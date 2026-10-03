#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Preserve WMT evidence and execute one guarded default query over USB SSH."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import runpy


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = PRIVATE_REPO / 'artifacts/wmt-default-query'
CAPTURE_DIR = ROOT / 'capture-2'
SOURCE = HERE.parent / '2026-09-29-mt6797-region19-wmt-memory/capture-private.py'
SPEC = importlib.util.spec_from_file_location('wmt_memory_capture', SOURCE)
CAPTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAPTURE)
CAPTURE.ROOT = ROOT
CAPTURE.CAPTURE = CAPTURE_DIR
CAPTURE.DEPLOYMENT = ROOT / 'session-2/deployment-summary.txt'
CAPTURE.RECEIPT = HERE / 'results/candidate.json'
CAPTURE.MANIFEST_SHA = 'fc6f457d353ef7cadae83d8842e82383333f81d27a85ff5df1dd1d9fbc59b309'
CAPTURE.RELEASE = '7.1.3-gemini-a53-wmt-query'
RELEASE = CAPTURE.RELEASE
WINDOW = CAPTURE.WINDOW
WMT_TRIGGER = CAPTURE.TRIGGER
START_TRIGGER = '/sys/bus/platform/devices/10001340.consys/wmt_default_query'
BYTES = CAPTURE.BYTES
CLEAR_BYTES = CAPTURE.CLEAR_BYTES
WMT_RECORDS = (
    b'one-shot WMT before: remap=0x180e0000 region1=0x44604460 '
    b'region18=0x00000000/0x00000000',
    b'one-shot WMT before: region19=0x00000000/0x00000000 '
    b'region23=0x00000000/0x00000000 CONN=off',
    b'one-shot WMT region19: status=0 range=0xbfa8bfaf policy=0x00b6da28',
    b'one-shot WMT remap: before=0x180e0000 after=0x180e1bfa '
    b'expected=0x180e1bfa',
    b'one-shot WMT setup complete: clear=351232 verified, CONN held off',
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, why):
    if not ok:
        raise ValueError(why)


def prepare(candidate):
    published = CAPTURE.RECEIPT.read_bytes()
    require(sha(published) == CAPTURE.MANIFEST_SHA, 'published candidate changed')
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
    rows = [line.split('=', 1) for line in CAPTURE.DEPLOYMENT.read_text().splitlines()]
    require(all(len(row) == 2 for row in rows) and
            len({row[0] for row in rows}) == len(rows), 'deployment malformed')
    fields = dict(rows)
    require(fields.get('experiment') == 'mt6797-wmt-default-query' and
            fields.get('candidate_manifest_sha256') == CAPTURE.MANIFEST_SHA and
            fields.get('target_logical_name') == 'boot2' and
            fields.get('result') in ('write-synced-flushed-full-readback-verified',
                                     'skipped-already-matching') and
            (fields['result'] != 'skipped-already-matching' or
             fields.get('predecessor_sha256') == expected['files']['boot2-padded.img']['sha256']) and
            fields.get('candidate_sha256') == expected['files']['boot2-padded.img']['sha256'] and
            fields.get('readback_sha256') == fields['candidate_sha256'] and
            fields.get('reboot') == 'no', 'deployment not admitted')
    installer = runpy.run_path(str(HERE / 'install-passive.py'))
    installer['receipt'](CAPTURE.DEPLOYMENT.read_text(),
                         expected['files']['boot2-padded.img']['sha256'],
                         CAPTURE.MANIFEST_SHA, fields.get('boot_id', ''))
    return expected


def read_script(boot):
    return ("set -eu\nBB=/bin/busybox\n"
            f"[ \"$($BB cat /proc/sys/kernel/random/boot_id)\" = {boot} ]\n"
            f"[ \"$($BB uname -r)\" = {RELEASE} ]\n"
            f"$BB cat {WINDOW}\n"
            f"[ \"$($BB cat /proc/sys/kernel/random/boot_id)\" = {boot} ]\n").encode()


GUARD = HERE / 'runtime-guard.sh'
GUARD_SHA256 = '8254c16f9de45becff7b88abb2d5a672a28622b4143dd7177f66157510f4eb29'


def admission_script(allow_mount=False):
    raw = GUARD.read_bytes()
    require(not GUARD.is_symlink() and sha(raw) == GUARD_SHA256,
            'runtime guard changed')
    return (b'ALLOW_DEBUGFS_MOUNT=' + (b'1' if allow_mount else b'0') + b'\n' + raw).decode()


def trigger_script(boot, path):
    require(path in {WMT_TRIGGER, START_TRIGGER}, 'unselected trigger')
    require(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot),
            'invalid boot identity')
    # Install restoration before remount; a failed restoration keeps EXIT active.
    return ("set -u\nBB=/bin/busybox\n"
            f"[ \"$($BB cat /proc/sys/kernel/random/boot_id)\" = {boot} ] || exit 10\n"
            f"[ \"$($BB uname -r)\" = {RELEASE} ] || exit 11\n"
            + admission_script() +
            "[ \"$($BB grep -c '^sysfs /sys sysfs ro,' /proc/mounts)\" = 1 ] || exit 12\n"
            f"[ -e {path} ] || exit 13\n"
            "restore() { $BB mount -o remount,ro /sys; }\n"
            "trap restore EXIT\n"
            "trap 'exit 30' HUP INT TERM\n"
            "$BB mount -o remount,rw /sys || exit 14\n"
            "[ \"$($BB grep -c '^sysfs /sys sysfs rw,' /proc/mounts)\" = 1 ] || exit 15\n"
            "echo sysfs_rw_verified\n"
            f"$BB printf '1\\n' > {path}\n"
            "trigger_rc=$?\n"
            "restore || exit 19\n"
            "[ \"$($BB grep -c '^sysfs /sys sysfs ro,' /proc/mounts)\" = 1 ] || exit 16\n"
            "trap - EXIT HUP INT TERM\n"
            "echo sysfs_ro_restored\n"
            f"[ \"$($BB cat /proc/sys/kernel/random/boot_id)\" = {boot} ] || exit 17\n"
            "[ \"$trigger_rc\" = 0 ] || exit 18\n").encode()


def query_result(log):
    pattern = rb'one-shot WMT default query: result=(-?\d+) rx=(\d+) irqs=(\d+) clocks-held=([01])$'
    matches = [m for line in log.splitlines() if (m := re.search(pattern, line))]
    if len(matches) != 1:
        return {'matched_response': False, 'query_record_count': len(matches)}
    status, rx, irqs, held = map(int, matches[0].groups())
    return {'matched_response': status == 0 and rx == 16 and 1 <= irqs < 32 and held == 1,
            'query_record_count': 1, 'query_status': status, 'rx_bytes': rx,
            'irq_entries': irqs, 'clocks_held': bool(held)}


def record_attempt(collector, command, name, script, timeout=30):
    folder = CAPTURE_DIR / name
    folder.mkdir(mode=0o700)
    collector['write_new'](folder / 'command.sh', script)
    result = collector['run_once'](command, script, folder, timeout,
                                   stdout_limit=2048, stderr_limit=16384)
    collector['write_new'](folder / 'process.json',
                           (json.dumps(result, sort_keys=True) + '\n').encode())
    return result, (folder / 'stdout.txt').read_bytes(), (folder / 'stderr.txt').read_bytes()


def read_log(capture, collector, network, command, boot, name):
    require(network['require_ready']()['ready'], 'direct mainline USB route absent')
    script = ("set -eu\nBB=/bin/busybox\n"
              f"[ \"$($BB cat /proc/sys/kernel/random/boot_id)\" = {boot} ]\n"
              f"[ \"$($BB uname -r)\" = {RELEASE} ]\n"
              "$BB dmesg\n").encode()
    return capture.attempt(collector, network, command, name, script, 1048576)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    try:
        expected = prepare(args.candidate)
        require(not CAPTURE_DIR.exists(), 'capture already claimed')
        if not args.execute:
            print('offline-preparation=pass; device_action=none')
            return 0
        collector = runpy.run_path(str(CAPTURE.BASELINE / 'baseline/scripts/collect-baseline.py'))
        network = runpy.run_path(str(CAPTURE.BASELINE / 'emmc/mainline_host.py'))
        command = collector['ssh_command'](PRIVATE_REPO / 'artifacts/credentials/a53-auth')
        CAPTURE_DIR.mkdir(mode=0o700)
        identify = ("set -eu\nBB=/bin/busybox\n"
                    f"[ -r {WINDOW} ] && [ -e {WMT_TRIGGER} ] && "
                    f"[ -e {START_TRIGGER} ]\n"
                    "boot=$($BB cat /proc/sys/kernel/random/boot_id)\n"
                    "release=$($BB uname -r)\n"
                    f"[ \"$release\" = {RELEASE} ]\n"
                    + admission_script(allow_mount=True) +
                    "$BB printf 'boot_id=%s\\nrelease=%s\\n' \"$boot\" \"$release\"\n").encode()
        identity = CAPTURE.attempt(collector, network, command, 'identify', identify, 1024)
        match = re.fullmatch(rb'boot_id=([0-9a-f-]{36})\nrelease=' +
                             re.escape(RELEASE.encode()) + rb'\n', identity)
        require(match is not None, 'mainline boot identity malformed')
        boot = match[1].decode()
        deployment = dict(line.split('=', 1) for line in
                          CAPTURE.DEPLOYMENT.read_text().splitlines())
        require(boot != deployment['boot_id'], 'mainline boot did not change from Gemian')
        read = read_script(boot)
        first = CAPTURE.attempt(collector, network, command, 'read-1', read, BYTES)
        second = CAPTURE.attempt(collector, network, command, 'read-2', read, BYTES)
        require(len(first) == len(second) == BYTES and first == second,
                'private pre-WMT samples differ')
        collector['write_new'](CAPTURE_DIR / 'preflight.json',
                               (json.dumps({'boot_id': boot, 'release': RELEASE,
                                            'candidate_boot2_sha256':
                                            expected['files']['boot2-padded.img']['sha256'],
                                            'window_sha256': sha(first), 'bytes': BYTES,
                                            'samples_equal': True}, indent=2) + '\n').encode())
        require(network['require_ready']()['ready'], 'direct mainline USB route absent')
        wmt_process, wmt_out, wmt_err = record_attempt(
            collector, command, 'wmt-trigger', trigger_script(boot, WMT_TRIGGER))
        # Preserve the post-attempt window before making any START decision.
        after = CAPTURE.attempt(collector, network, command, 'read-after-wmt', read, BYTES)
        log = read_log(CAPTURE, collector, network, command, boot, 'log-after-wmt')
        counts = [sum(record in line for line in log.splitlines())
                  for record in WMT_RECORDS]
        no_active = not any(re.search(rb'one-shot (?:WLAN|EMI|HIF|CONN) ', line)
                            for line in log.splitlines())
        wmt_ok = (wmt_process['reason'] is None and wmt_process['exit_status'] == 0 and
                  wmt_process['stdin_complete'] is True and
                  wmt_out == b'sysfs_rw_verified\nsysfs_ro_restored\n' and not wmt_err and
                  len(after) == BYTES and not any(after[:CLEAR_BYTES]) and
                  after[CLEAR_BYTES:] == first[CLEAR_BYTES:] and
                  counts == [1] * len(WMT_RECORDS) and
                  b'one-shot WMT setup stopped' not in log and no_active)
        collector['write_new'](CAPTURE_DIR / 'wmt-result.json',
                               (json.dumps({'boot_id': boot, 'release': RELEASE,
                                            'candidate_boot2_sha256':
                                            expected['files']['boot2-padded.img']['sha256'],
                                            'wmt_trigger_process': wmt_process,
                                            'wmt_stdout_sha256': sha(wmt_out),
                                            'wmt_stderr_sha256': sha(wmt_err),
                                            'pre_sha256': sha(first), 'post_sha256': sha(after),
                                            'post_bytes': len(after),
                                            'clear_prefix_zero': not any(after[:CLEAR_BYTES]),
                                            'suffix_equal': after[CLEAR_BYTES:] == first[CLEAR_BYTES:],
                                            'wmt_record_counts': counts,
                                            'no_other_active_records': no_active,
                                            'log_sha256': sha(log), 'accepted': wmt_ok,
                                            'query_attempted': False},
                                           indent=2) + '\n').encode())
        require(wmt_ok, 'WMT preparation or full readback refused query')
        require(network['require_ready']()['ready'], 'direct mainline USB route absent')
        query_process, query_out, query_err = record_attempt(
            collector, command, 'wmt-query-once', trigger_script(boot, START_TRIGGER))
        result = {'boot_id': boot, 'release': RELEASE,
                  'candidate_boot2_sha256': expected['files']['boot2-padded.img']['sha256'],
                  'query_request_sent': query_process['stdin_complete'],
                  'one_host_query_attempt': True, 'query_process': query_process,
                  'query_stdout_sha256': sha(query_out),
                  'query_stderr_sha256': sha(query_err), 'radio_action': False, 'matched_response': False}
        collector['write_new'](CAPTURE_DIR / 'query-result.json',
                               (json.dumps(result, indent=2) + '\n').encode())
        if network['require_ready']()['ready']:
            after_query = read_log(CAPTURE, collector, network, command, boot,
                                   'log-after-query')
            result.update(query_result(after_query))
            result['trigger_accepted'] = (query_process['reason'] is None and
                query_process['exit_status'] == 0 and query_process['stdin_complete'] is True and
                query_out == b'sysfs_rw_verified\nsysfs_ro_restored\n' and not query_err)
            result['transport_liveness'] = result['trigger_accepted'] and result['matched_response']
            collector['write_new'](CAPTURE_DIR / 'query-log-sha256.txt',
                                   (sha(after_query) + '\n').encode())
        collector['write_new'](CAPTURE_DIR / 'query-classification.json',
                               (json.dumps(result, indent=2) + '\n').encode())
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get('transport_liveness') else 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, 'WMT query capture refused: ' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
