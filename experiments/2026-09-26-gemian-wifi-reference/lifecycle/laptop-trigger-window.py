#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Laptop side of the traffic step: wait for the device's traffic window, then send the group trigger once.

The custodian runs this on the laptop after launching the device cycle. It polls the
device over the known-good LAN SSH path for the `traffic-window` marker the cycle
writes (`<start> <end> <boot-id>` in epoch seconds), on a monotonic deadline, each SSH
call clamped to the remaining budget; it requires the marker's boot ID to equal the
verified v10 boot ID, and sends the three datagrams only when the window still has
room for the whole schedule (two one-second gaps plus a margin). The marker lives in the
root-owned capture directory and is read with `sudo -n cat`; nothing is written on the
device. The SSH identity is the custodian's approved private key, used with
IdentitiesOnly, no agent and strict host-key checking; no other key is offered.
"""
import argparse
import pathlib
import re
import runpy
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
TRIGGER = runpy.run_path(str(HERE / 'lan-group-trigger.py'), run_name='lan_group_trigger')
MARKER = '/var/tmp/gemini-wifi-reference-lifecycle-v10/traffic-window'
SCHEDULE_SECONDS = 2.0   # three datagrams one second apart
MARGIN_SECONDS = 2.0
BOOT_ID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


def ssh_command(alias, identity, timeout_s):
    return ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=%d' % max(1, int(timeout_s)),
            '-o', 'IdentitiesOnly=yes', '-o', 'IdentityAgent=none', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UpdateHostKeys=no', '-i', identity, alias]


def read_marker(ssh, runner, timeout_s):
    """(start, end, boot_id) from the marker, or None while it does not exist or is malformed."""
    # The capture directory is root-owned mode 0700; the device user reads the fixed marker through sudo -n.
    result = runner(ssh + ['sudo', '-n', 'cat', MARKER], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout_s)
    if result.returncode != 0:
        return None
    parts = result.stdout.decode('ascii', 'replace').split()
    if len(parts) != 3 or not parts[0].isdigit() or not parts[1].isdigit() or not BOOT_ID.match(parts[2]):
        return None
    return int(parts[0]), int(parts[1]), parts[2]


def run(alias, identity, boot_id, local, prefix, poll_seconds, runner=subprocess.run, clock=time.time,
        monotonic=time.monotonic, sleep=time.sleep, send=None):
    send = send or TRIGGER['send']
    deadline = monotonic() + poll_seconds
    while True:
        remaining = deadline - monotonic()
        if remaining <= 0:
            return {'window_seen': False, 'sent': False, 'reason': 'no window within the poll budget'}
        ssh = ssh_command(alias, identity, min(10, remaining))
        try:
            marker = read_marker(ssh, runner, min(10.0, remaining))
        except subprocess.TimeoutExpired:
            marker = None
        if marker:
            start, end, marker_boot = marker
            if marker_boot != boot_id:
                return {'window_seen': True, 'sent': False, 'reason': 'marker boot id differs from the verified boot'}
            now = clock()
            if now < start:
                return {'window_seen': True, 'sent': False, 'reason': 'window start is in the future'}
            if end - now < SCHEDULE_SECONDS + MARGIN_SECONDS:
                return {'window_seen': True, 'sent': False, 'reason': 'not enough window left for the three datagrams'}
            send(local, prefix)
            return {'window_seen': True, 'sent': True, 'sent_at': int(clock()), 'window': [start, end]}
        if deadline - monotonic() <= 1:
            return {'window_seen': False, 'sent': False, 'reason': 'no window within the poll budget'}
        sleep(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('ssh_alias', help='the custodian\'s SSH alias for the device on the LAN')
    parser.add_argument('identity', help='the approved private key file for the device')
    parser.add_argument('boot_id', help='the verified v10 boot ID the device cycle was launched with')
    parser.add_argument('local', help='this laptop\'s IPv4 address on the owner LAN')
    parser.add_argument('prefix', type=int)
    parser.add_argument('--poll-seconds', type=int, default=120)
    args = parser.parse_args()
    if not BOOT_ID.match(args.boot_id):
        parser.error('boot id is not a UUID')
    outcome = run(args.ssh_alias, args.identity, args.boot_id, args.local, args.prefix, args.poll_seconds)
    print(' '.join('%s=%s' % (k, v) for k, v in sorted(outcome.items())))
    return 0 if outcome['sent'] else 1


if __name__ == '__main__':
    sys.exit(main())
