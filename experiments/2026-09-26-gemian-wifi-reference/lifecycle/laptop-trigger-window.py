#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Laptop side of the traffic step: wait for the device's traffic window, then send the group trigger.

The custodian runs this on the laptop after launching the device cycle. It polls
the device over the known-good LAN SSH path for the `traffic-window` marker the
cycle writes (two epoch seconds: start and end), bounded by --poll-seconds, then
calls lan-group-trigger.send() once while the window is open, and reports only
booleans and timestamps. The SSH command is the custodian's own alias; nothing
is written on the device.
"""
import argparse
import pathlib
import runpy
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
TRIGGER = runpy.run_path(str(HERE / 'lan-group-trigger.py'), run_name='lan_group_trigger')
MARKER = '/var/tmp/gemini-wifi-reference-lifecycle-v10/traffic-window'


def read_marker(ssh, runner=subprocess.run):
    """(start, end) epochs from the marker, or None while it does not exist."""
    result = runner(ssh + ['cat', MARKER], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
    if result.returncode != 0:
        return None
    parts = result.stdout.decode('ascii', 'replace').split()
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        return None
    return int(parts[0]), int(parts[1])


def run(ssh, local, prefix, poll_seconds, runner=subprocess.run, clock=time.time, sleep=time.sleep, send=None):
    send = send or TRIGGER['send']
    deadline = clock() + poll_seconds
    while clock() < deadline:
        try:
            window = read_marker(ssh, runner)
        except subprocess.TimeoutExpired:
            window = None
        if window:
            start, end = window
            if clock() >= end:
                return {'window_seen': True, 'sent': False, 'reason': 'window already closed'}
            send(local, prefix)
            return {'window_seen': True, 'sent': True, 'sent_at': int(clock()), 'window': [start, end]}
        sleep(1)
    return {'window_seen': False, 'sent': False, 'reason': 'no window within the poll budget'}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('ssh_alias', help='the custodian\'s SSH alias for the device on the LAN')
    parser.add_argument('local', help='this laptop\'s IPv4 address on the owner LAN')
    parser.add_argument('prefix', type=int)
    parser.add_argument('--poll-seconds', type=int, default=120)
    args = parser.parse_args()
    outcome = run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', args.ssh_alias], args.local, args.prefix, args.poll_seconds)
    print(' '.join('%s=%s' % (k, v) for k, v in sorted(outcome.items())))
    return 0 if outcome['sent'] else 1


if __name__ == '__main__':
    sys.exit(main())
