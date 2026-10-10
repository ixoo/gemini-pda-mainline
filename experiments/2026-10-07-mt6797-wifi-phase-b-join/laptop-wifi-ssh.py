#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Laptop side of the Phase C3 data checks: one bounded authenticated SSH exchange over Wi-Fi.

The custodian runs this on the laptop while the device session's join phase runs. It
polls the device over the authenticated USB SSH path for the private lease file the
join script's udhcpc hook writes (the station's own address), on a monotonic budget with
each call clamped to what remains; when the lease exists it opens exactly one SSH session
to that address over Wi-Fi with the same approved identity (IdentitiesOnly, no agent,
strict host-key checking against the device's known host key through HostKeyAlias, no key
updates), runs one read-only command that prints the boot identity, and compares it with
the verified boot. The receipt carries statuses, byte counts and seconds only; the address
is never printed, logged or kept. One attempt; no retry.
"""
import argparse
import re
import subprocess
import sys
import time

LEASE = '/tmp/mt6797-wifi-phase-b-1/lease'
BOOT_ID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
ADDRESS = re.compile(r'^(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$')
COMMAND = 'cat /proc/sys/kernel/random/boot_id'


def ssh_base(identity, timeout_s, host_key_alias=None):
    options = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=%d' % max(1, int(timeout_s)),
               '-o', 'IdentitiesOnly=yes', '-o', 'IdentityAgent=none', '-o', 'StrictHostKeyChecking=yes',
               '-o', 'UpdateHostKeys=no', '-o', 'LogLevel=ERROR', '-i', identity]
    if host_key_alias:
        options += ['-o', 'HostKeyAlias=' + host_key_alias]
    return options


def read_lease(usb_alias, identity, runner, timeout_s):
    """The station's address from the private lease file, or None while absent or malformed."""
    result = runner(ssh_base(identity, min(10, timeout_s)) + [usb_alias, 'cat', LEASE],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout_s)
    if result.returncode != 0:
        return None
    text = result.stdout.decode('ascii', 'replace').strip()
    return text if ADDRESS.match(text) else None


def run(usb_alias, identity, boot_id, user, host_key_alias, poll_seconds, runner=subprocess.run,
        monotonic=time.monotonic, sleep=time.sleep):
    deadline = monotonic() + poll_seconds
    started = monotonic()
    receipt = {'lease_seen': False, 'lease_wait_s': None, 'ssh_attempted': False, 'ssh_exit': None,
               'boot_match': False, 'stdout_bytes': 0, 'elapsed_s': None, 'reason': None}
    address = None
    while True:
        remaining = deadline - monotonic()
        if remaining <= 1:
            receipt['reason'] = 'no lease within the poll budget'
            receipt['elapsed_s'] = round(monotonic() - started, 1)
            return receipt
        try:
            address = read_lease(usb_alias, identity, runner, min(10.0, remaining))
        except subprocess.TimeoutExpired:
            address = None
        if address:
            break
        sleep(2)
    receipt['lease_seen'] = True
    receipt['lease_wait_s'] = round(monotonic() - started, 1)
    remaining = deadline - monotonic()
    if remaining <= 2:
        receipt['reason'] = 'no budget left for the exchange'
        receipt['elapsed_s'] = round(monotonic() - started, 1)
        return receipt
    receipt['ssh_attempted'] = True
    try:
        result = runner(ssh_base(identity, min(5, remaining), host_key_alias) + [user + '@' + address, COMMAND],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=min(25.0, remaining))
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
    parser.add_argument('usb_alias', help='the custodian\'s SSH alias for the device over USB')
    parser.add_argument('identity', help='the approved private key file for the device')
    parser.add_argument('boot_id', help='the verified boot ID the device session was launched with')
    parser.add_argument('--user', default='root', help='the login for the Wi-Fi hop (default root)')
    parser.add_argument('--host-key-alias', default=None,
                        help='known_hosts name of the device\'s host key (the USB alias), so the Wi-Fi hop checks the same key')
    parser.add_argument('--poll-seconds', type=int, default=90, help='monotonic budget, 10 to 120')
    args = parser.parse_args()
    if not BOOT_ID.match(args.boot_id):
        parser.error('boot id is not a UUID')
    if not 10 <= args.poll_seconds <= 120:
        parser.error('poll budget must be between 10 and 120 seconds')
    receipt = run(args.usb_alias, args.identity, args.boot_id, args.user, args.host_key_alias, args.poll_seconds)
    print(' '.join('%s=%s' % (k, v) for k, v in sorted(receipt.items())))
    return 0 if receipt['boot_match'] else 1


if __name__ == '__main__':
    sys.exit(main())
