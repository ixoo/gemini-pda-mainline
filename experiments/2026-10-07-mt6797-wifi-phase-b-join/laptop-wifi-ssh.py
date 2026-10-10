#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Laptop side of the Phase C3 data checks: one bounded authenticated SSH exchange over Wi-Fi.

The custodian runs this on the laptop while the device session's join phase runs. It
polls the device over the authenticated USB SSH path for the private readiness marker the
join script writes last, after its second Dropbear listener on wlan0's leased address has
its pid file (the station's own address), on a monotonic budget with each call clamped to
what remains; when the marker exists it opens exactly one SSH session to that address over
Wi-Fi, runs one read-only command that prints the boot identity, and compares it with the
verified boot. Both hops use the baseline's exact direct SSH options (no configuration
file, no agent, no proxy, no multiplexing, Ed25519 only, key only, strict host-key checking
against the retained known_hosts, which pins the fixed USB endpoint's host key); the Wi-Fi
hop names that endpoint as its HostKeyAlias so the same retained host key is required. The
receipt carries statuses, byte counts and seconds only; the address is never printed, logged
or kept. One attempt; no retry.
"""
import argparse
import json
import os
import pathlib
import re
import runpy
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
BASELINE = runpy.run_path(str(HERE.parents[0] / '2026-09-05-owner-away-experiment-preparation/baseline/scripts/collect-baseline.py'),
                          run_name='a53_baseline')
READY = '/tmp/mt6797-wifi-phase-b-1/wifi-ssh'
BOOT_ID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
ADDRESS = re.compile(r'^(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$')
COMMAND = 'cat /proc/sys/kernel/random/boot_id'


def base_command(keys):
    """The baseline's exact SSH options and admin identity, without its target and shell."""
    command = BASELINE['ssh_command'](keys)
    assert command[-1] == '/bin/busybox sh -s' and command[-2].startswith('root@')
    return command[:-2], command[-2]


def usb_command(keys, argument):
    base, target = base_command(keys)
    return base + [target, argument]


def wifi_command(keys, address):
    base, target = base_command(keys)
    alias = target.split('@', 1)[1]
    return base + ['-o', 'HostKeyAlias=' + alias, 'root@' + address, COMMAND]


def admissible(address, usb_target):
    """A leased station address the Wi-Fi hop may use: a well-formed unicast address that is
    not the fixed USB endpoint (an accidental USB lease must not reach the USB listener and pass),
    not loopback, multicast, unspecified or broadcast."""
    if not ADDRESS.match(address) or address == usb_target.split('@', 1)[1]:
        return False
    first = int(address.split('.')[0])
    return not (first == 0 or first == 127 or first >= 224 or address == '255.255.255.255')


def read_ready(keys, runner, timeout_s):
    """The station's address from the private readiness marker, or None while absent, malformed or inadmissible."""
    result = runner(usb_command(keys, 'cat ' + READY), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout_s)
    if result.returncode != 0:
        return None
    text = result.stdout.decode('ascii', 'replace').strip()
    return text if admissible(text, base_command(keys)[1]) else None


def run(keys, boot_id, poll_seconds, runner=subprocess.run, monotonic=time.monotonic, sleep=time.sleep):
    deadline = monotonic() + poll_seconds
    started = monotonic()
    receipt = {'ready_seen': False, 'ready_wait_s': None, 'ssh_attempted': False, 'ssh_exit': None,
               'boot_match': False, 'stdout_bytes': 0, 'elapsed_s': None, 'reason': None}
    address = None
    while True:
        remaining = deadline - monotonic()
        if remaining <= 1:
            receipt['reason'] = 'no readiness marker within the poll budget'
            receipt['elapsed_s'] = round(monotonic() - started, 1)
            return receipt
        try:
            address = read_ready(keys, runner, min(15.0, remaining))
        except subprocess.TimeoutExpired:
            address = None
        if address:
            break
        sleep(2)
    receipt['ready_seen'] = True
    receipt['ready_wait_s'] = round(monotonic() - started, 1)
    remaining = deadline - monotonic()
    if remaining <= 2:
        receipt['reason'] = 'no budget left for the exchange'
        receipt['elapsed_s'] = round(monotonic() - started, 1)
        return receipt
    receipt['ssh_attempted'] = True
    try:
        result = runner(wifi_command(keys, address), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                        timeout=min(25.0, remaining))
    except subprocess.TimeoutExpired:
        receipt['reason'] = 'exchange timed out'
        receipt['elapsed_s'] = round(monotonic() - started, 1)
        return receipt
    receipt['ssh_exit'] = result.returncode
    receipt['stdout_bytes'] = len(result.stdout)
    text = result.stdout.decode('ascii', 'replace').strip()
    receipt['boot_match'] = result.returncode == 0 and BOOT_ID.match(text) is not None and text == boot_id
    if not receipt['boot_match']:
        receipt['reason'] = 'exchange failed' if result.returncode else 'boot identity differs'
    receipt['elapsed_s'] = round(monotonic() - started, 1)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('keys', type=pathlib.Path,
                        help='the retained credential directory holding admin and known_hosts (private, never copied)')
    parser.add_argument('boot_id', help='the verified boot ID the device session was launched with')
    parser.add_argument('--poll-seconds', type=int, default=90, help='monotonic budget, 10 to 120')
    parser.add_argument('--receipt', type=pathlib.Path, default=None,
                        help='write the receipt as JSON to this new mode-0600 file for the host session')
    args = parser.parse_args()
    if not BOOT_ID.match(args.boot_id):
        parser.error('boot id is not a UUID')
    if not 10 <= args.poll_seconds <= 120:
        parser.error('poll budget must be between 10 and 120 seconds')
    keys = args.keys.resolve(strict=True)
    if not (keys / 'admin').is_file() or not (keys / 'known_hosts').is_file():
        parser.error('keys directory lacks admin or known_hosts')
    receipt = run(keys, args.boot_id, args.poll_seconds)
    receipt['boot_id'] = args.boot_id
    if args.receipt is not None:
        fd = os.open(str(args.receipt), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(' '.join('%s=%s' % (k, v) for k, v in sorted(receipt.items())))
    return 0 if receipt['boot_match'] else 1


if __name__ == '__main__':
    sys.exit(main())
