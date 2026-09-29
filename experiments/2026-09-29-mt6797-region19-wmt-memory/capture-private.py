#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Capture and verify one WMT memory setup over authenticated USB SSH."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = PRIVATE_REPO / 'artifacts/region19-wmt-memory'
CAPTURE = ROOT / 'capture-1'
DEPLOYMENT = ROOT / 'session-1/deployment-summary.txt'
RECEIPT = HERE / 'results/candidate.json'
MANIFEST_SHA = '5b0f97bc8b45d6c8287dd52e6d0b5a978f061c359ea0a025457aec6f9d2f69a9'
RELEASE = '7.1.3-gemini-a53-wifi-region19-wmtmem'
WINDOW = '/sys/bus/platform/devices/10001340.consys/region19_snapshot'
TRIGGER = '/sys/bus/platform/devices/10001340.consys/region19_prepare'
BYTES = 524288
CLEAR_BYTES = 343 * 1024
BASELINE = REPO / 'experiments/2026-09-05-owner-away-experiment-preparation'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def prepare(candidate):
    published = RECEIPT.read_bytes()
    require(sha(published) == MANIFEST_SHA, 'published candidate receipt changed')
    expected = json.loads(published)
    require(not candidate.is_symlink(), 'candidate path is a symlink')
    candidate = candidate.resolve(strict=True)
    require(candidate.is_dir() and
            candidate.name == 'candidate-' + expected['files']['boot.img']['sha256'] and
            json.loads((candidate / 'candidate.json').read_bytes()) == expected and
            {p.name for p in candidate.iterdir()} == set(expected['files']) | {'candidate.json'},
            'private candidate identity changed')
    for name, identity in expected['files'].items():
        path = candidate / name
        require(path.is_file() and not path.is_symlink() and
                path.stat().st_size == identity['bytes'] and
                sha(path.read_bytes()) == identity['sha256'],
                'candidate member changed: ' + name)
    rows = [line.split('=', 1) for line in DEPLOYMENT.read_text().splitlines()]
    require(all(len(row) == 2 for row in rows) and
            len({row[0] for row in rows}) == len(rows),
            'deployment fields malformed or repeated')
    fields = dict(rows)
    require(fields.get('experiment') == 'mt6797-region19-wmt-memory' and
            fields.get('candidate_manifest_sha256') == MANIFEST_SHA and
            fields.get('target_logical_name') == 'boot2' and
            fields.get('result') == 'write-synced-flushed-full-readback-verified' and
            fields.get('candidate_sha256') == expected['files']['boot2-padded.img']['sha256'] and
            fields.get('readback_sha256') == fields['candidate_sha256'] and
            fields.get('reboot') == 'no', 'deployment not admitted')
    return expected


def attempt(collector, network, command, name, script, limit):
    require(network['require_ready']()['ready'], 'direct mainline USB route absent')
    folder = CAPTURE / name
    folder.mkdir(mode=0o700)
    collector['write_new'](folder / 'command.sh', script)
    process = collector['run_once'](command, script, folder, 30,
                                    stdout_limit=limit, stderr_limit=16384)
    collector['write_new'](folder / 'process.json',
                           (json.dumps(process, sort_keys=True) + '\n').encode())
    raw = (folder / 'stdout.txt').read_bytes()
    err = (folder / 'stderr.txt').read_bytes()
    require(process['reason'] is None and process['exit_status'] == 0 and
            process['stdin_complete'] is True and not err and
            process['stdout_bytes'] == len(raw), name + ' transport incomplete')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        expected = prepare(args.candidate)
        require(not CAPTURE.exists(), 'capture already claimed')
        if not args.execute:
            print('offline-preparation=pass; device_action=none')
            return 0
        collector = runpy.run_path(str(BASELINE / 'baseline/scripts/collect-baseline.py'))
        network = runpy.run_path(str(BASELINE / 'emmc/mainline_host.py'))
        keys = PRIVATE_REPO / 'artifacts/credentials/a53-auth'
        command = collector['ssh_command'](keys)
        CAPTURE.mkdir(mode=0o700)
        identify = ("set -eu\nBB=/bin/busybox\n"
                    f"[ -r {WINDOW} ] || exit 1\n"
                    f"[ -w {TRIGGER} ] || exit 1\n"
                    "boot=$($BB cat /proc/sys/kernel/random/boot_id)\n"
                    "release=$($BB uname -r)\n"
                    f"[ \"$release\" = {RELEASE} ] || exit 1\n"
                    "$BB printf 'boot_id=%s\\nrelease=%s\\n' \"$boot\" \"$release\"\n").encode()
        identity = attempt(collector, network, command, 'identify', identify, 1024)
        match = re.fullmatch(rb'boot_id=([0-9a-f-]{36})\nrelease=' +
                             re.escape(RELEASE.encode()) + rb'\n', identity)
        require(match is not None, 'mainline boot identity malformed')
        boot = match[1].decode()
        read = ("set -eu\nBB=/bin/busybox\n"
                f"[ \"$($BB cat /proc/sys/kernel/random/boot_id)\" = {boot} ] || exit 1\n"
                f"[ \"$($BB uname -r)\" = {RELEASE} ] || exit 1\n"
                f"$BB cat {WINDOW}\n"
                f"[ \"$($BB cat /proc/sys/kernel/random/boot_id)\" = {boot} ] || exit 1\n").encode()
        first = attempt(collector, network, command, 'read-1', read, BYTES)
        second = attempt(collector, network, command, 'read-2', read, BYTES)
        require(len(first) == len(second) == BYTES, 'region-19 export size changed')
        require(first == second, 'same-boot pre-write samples differ')
        preflight = {'status': 'private-wmt-prewrite-preserved',
                     'candidate_boot2_sha256': expected['files']['boot2-padded.img']['sha256'],
                     'mainline_boot_id': boot, 'kernel_release': RELEASE,
                     'bytes_per_read': BYTES, 'read_1_sha256': sha(first),
                     'read_2_sha256': sha(second), 'equal': True}
        collector['write_new'](CAPTURE / 'preflight.json',
                               (json.dumps(preflight, indent=2) + '\n').encode())
        write = ("set -eu\nBB=/bin/busybox\n"
                 f"[ \"$($BB cat /proc/sys/kernel/random/boot_id)\" = {boot} ] || exit 1\n"
                 f"[ \"$($BB uname -r)\" = {RELEASE} ] || exit 1\n"
                 f"$BB printf '1\\n' > {TRIGGER}\n"
                 f"[ \"$($BB cat /proc/sys/kernel/random/boot_id)\" = {boot} ] || exit 1\n").encode()
        trigger_error = None
        try:
            require(not attempt(collector, network, command,
                                'trigger-once', write, 1024),
                    'trigger returned unexpected output')
        except (OSError, ValueError) as error:
            trigger_error = str(error)
        # Preserve the post-attempt window even when the sysfs write refused.
        after = attempt(collector, network, command, 'read-after', read, BYTES)
        require(len(after) == BYTES, 'post-write export size changed')
        prefix_zero = not any(after[:CLEAR_BYTES])
        suffix_unchanged = after[CLEAR_BYTES:] == first[CLEAR_BYTES:]
        result = {'status': 'private-one-shot-wmt-memory-captured',
                  'candidate_boot2_sha256': expected['files']['boot2-padded.img']['sha256'],
                  'mainline_boot_id': boot, 'kernel_release': RELEASE,
                  'bytes_per_read': BYTES, 'read_1_sha256': sha(first),
                  'read_2_sha256': sha(second), 'pre_equal': True,
                  'read_after_sha256': sha(after), 'clear_bytes': CLEAR_BYTES,
                  'cleared_prefix_zero': prefix_zero,
                  'untouched_suffix_equal': suffix_unchanged,
                  'one_sysfs_trigger_attempt': True,
                  'trigger_transport_complete': trigger_error is None,
                  'firmware_start': False,
                  'radio_action': False, 'raw_published': False}
        collector['write_new'](CAPTURE / 'receipt.json',
                               (json.dumps(result, indent=2) + '\n').encode())
        require(trigger_error is None, 'trigger refused: ' + str(trigger_error))
        require(prefix_zero and suffix_unchanged,
                'WMT clear or preserved suffix did not read back')
        print(json.dumps(result, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'WMT memory capture refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
