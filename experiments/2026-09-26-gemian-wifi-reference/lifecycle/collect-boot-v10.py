#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Finite read-only LAN collector for the v10 reference boot and for the return to Gemian.

Run on the laptop by the custodian, armed before the owner's physical boot2 handoff and
again before the ordinary return reboot. It polls the device over the LAN SSH path with
the approved identity until a boot other than the given predecessor appears with the
expected release on aarch64, or the deadline passes. On a changed boot it captures
read-only snapshots (dmesg and /proc/cmdline through sudo -n, the wlan0 carrier and IPv4
address) into a new private directory (mode 0700, files 0600), re-reads the identity
after the captures, hashes every file and writes a receipt with sanitized identity only
(boot IDs, release, architecture, sizes, digests, timings, booleans). It never writes on
the device and performs no boot control, pstore, radio or reboot action.
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

BOOT_ID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
RELEASE = re.compile(r'^[A-Za-z0-9._+-]{1,64}$')
IDENTITY_COMMAND = 'cat /proc/sys/kernel/random/boot_id; uname -m; uname -r'
SNAPSHOTS = (
    ('dmesg.log', 'sudo -n dmesg'),
    ('cmdline.txt', 'sudo -n cat /proc/cmdline'),   # mode 0440 root:radio on Gemian
    ('carrier.txt', 'cat /sys/class/net/wlan0/carrier'),
    ('addr.txt', 'ip -4 addr show dev wlan0'),
)


def ssh_command(alias, identity, timeout_s):
    return ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=%d' % max(1, int(timeout_s)),
            '-o', 'IdentitiesOnly=yes', '-o', 'IdentityAgent=none', '-o', 'StrictHostKeyChecking=yes',
            '-o', 'UpdateHostKeys=no', '-i', identity, alias]


def query(runner, ssh, command, timeout_s):
    """stdout bytes of one bounded remote read-only command, or None on failure or timeout."""
    try:
        result = runner(ssh + [command], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return None
    return result.stdout if result.returncode == 0 else None


def parse_identity(raw):
    """(boot_id, machine, release) or None when the three lines are not well formed."""
    if raw is None:
        return None
    lines = raw.decode('ascii', 'replace').splitlines()
    if len(lines) != 3 or not all(lines) or not BOOT_ID.match(lines[0]) or not RELEASE.match(lines[2]) \
            or not re.match(r'^[A-Za-z0-9_]{1,16}$', lines[1]):
        return None
    return lines[0], lines[1], lines[2]


def collect(alias, key, predecessor, expected_release, output, deadline_s, runner=subprocess.run,
            monotonic=time.monotonic, sleep=time.sleep, wall=time.time):
    output = pathlib.Path(output)
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    start = monotonic()
    deadline = start + deadline_s
    polls = 0
    seen = []
    receipt = {'predecessor_boot_id': predecessor, 'expected_release': expected_release, 'deadline_s': deadline_s,
               'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(wall())), 'polls': 0,
               'changed_boot': False, 'identity_before': None, 'identity_after': None, 'identity_stable': False,
               'files': {}, 'result': 'no changed boot within the deadline'}
    while monotonic() < deadline:
        remaining = deadline - monotonic()
        if remaining < 1:
            break
        per_call = min(10.0, remaining)
        polls += 1
        ident = parse_identity(query(runner, ssh_command(alias, str(key), per_call), IDENTITY_COMMAND, per_call))
        if ident and ident[0] not in seen:
            seen.append(ident[0])
        if ident and ident[0] != predecessor:
            boot_id, machine, release = ident
            receipt['identity_before'] = {'boot_id': boot_id, 'machine': machine, 'release': release}
            if machine != 'aarch64' or release != expected_release:
                receipt['result'] = 'changed boot refused: machine or release differ from the expected v10 boot'
                receipt['changed_boot'] = True
                break
            receipt['changed_boot'] = True
            for name, command in SNAPSHOTS:
                remaining = deadline - monotonic()
                if remaining <= 1:
                    receipt['result'] = 'deadline during the captures'
                    break
                data = query(runner, ssh_command(alias, str(key), min(10.0, remaining)), command, min(30.0, remaining))
                path = output / name
                if data is None:
                    receipt['files'][name] = {'captured': False}
                    continue
                path.write_bytes(data)
                path.chmod(0o600)
                receipt['files'][name] = {'captured': True, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            remaining = deadline - monotonic()
            after = None
            if remaining >= 1:
                final = min(10.0, remaining)
                after = parse_identity(query(runner, ssh_command(alias, str(key), final), IDENTITY_COMMAND, final))
            else:
                receipt['result'] = 'deadline before the final identity read'
            if after:
                receipt['identity_after'] = {'boot_id': after[0], 'machine': after[1], 'release': after[2]}
                receipt['identity_stable'] = after == ident
            captured = all(v.get('captured') for v in receipt['files'].values()) and len(receipt['files']) == len(SNAPSHOTS)
            if receipt['result'] == 'no changed boot within the deadline':
                receipt['result'] = 'changed boot captured' if captured and receipt['identity_stable'] else 'changed boot captured partially'
            break
        if deadline - monotonic() <= 1:
            break
        sleep(1)
    receipt['polls'] = polls
    receipt['boot_ids_seen'] = seen
    receipt['elapsed_s'] = round(monotonic() - start, 1)
    text = json.dumps(receipt, indent=1, sort_keys=True) + '\n'
    (output / 'receipt.json').write_text(text)
    (output / 'receipt.json').chmod(0o600)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('ssh_alias')
    parser.add_argument('identity', help='the approved private key for the device')
    parser.add_argument('predecessor_boot_id', help='the boot ID the device had before the handoff or the return')
    parser.add_argument('expected_release', help='3.18.41-gemini-wifi-ref10+ for the handoff, 3.18.41+ for the return')
    parser.add_argument('output', help='new private output directory (created 0700)')
    parser.add_argument('--deadline', type=int, choices=(180, 900), default=180)
    args = parser.parse_args()
    if not BOOT_ID.match(args.predecessor_boot_id):
        parser.error('predecessor boot id is not a UUID')
    if not RELEASE.match(args.expected_release):
        parser.error('expected release is malformed')
    receipt = collect(args.ssh_alias, args.identity, args.predecessor_boot_id, args.expected_release, args.output, args.deadline)
    print('result=%s changed_boot=%d identity_stable=%d polls=%d elapsed_s=%s' % (
        receipt['result'].replace(' ', '_'), receipt['changed_boot'], receipt['identity_stable'], receipt['polls'], receipt['elapsed_s']))
    return 0 if receipt['result'] == 'changed boot captured' else 1


if __name__ == '__main__':
    sys.exit(main())
