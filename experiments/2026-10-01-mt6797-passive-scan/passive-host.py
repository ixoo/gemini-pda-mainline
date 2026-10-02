#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run one standard passive scan before sealing logs and reviewed recovery."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
ROOT = PRIVATE_REPO / 'artifacts/passive-scan/session-4'
CAPTURE = PRIVATE_REPO / 'artifacts/passive-scan/capture-4'
SOURCE = HERE.parent / '2026-10-01-mt6797-tc4-reconcile/passive-host.py'
SPEC = importlib.util.spec_from_file_location('tc4_scan_parent', SOURCE)
PARENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PARENT)
RELEASE = '7.1.3-gemini-a53-wifi-passive-scan'
PARENT.HERE = HERE
PARENT.ROOT = ROOT
PARENT.CAPTURE = CAPTURE
HOST = PARENT.HOST
HOST.HERE = HERE
HOST.ROOT = ROOT
HOST.CAPTURE = CAPTURE
HOST.DOMAIN.HERE = HERE
HOST.DOMAIN.ROOT = ROOT
HOST.DOMAIN.RELEASE = RELEASE
HOST.DOMAIN.HOST.HERE = HERE
HOST.DOMAIN.HOST.ROOT = ROOT
HOST.DOMAIN.HOST.REPO = PRIVATE_REPO
HOST.DOMAIN.HOST.__file__ = str(Path(__file__).resolve())
PARENT.WIPHY_PROBE = PARENT.WIPHY_PROBE.replace(
    b'7.1.3-gemini-a53-wifi-tc4-reconcile', RELEASE.encode())
PREPARE = HOST.DOMAIN.prepare
SCAN_SOURCE = HERE / 'passive-scan.sh'
SUMMARY = re.compile(rb'one-shot passive WLAN scan: status=(-?\d+) complete=([01]) frame=([01]) beacon=([01]) credit=([01]) retired=1$')
DONE = re.compile(rb'one-shot passive WLAN done header: len=(\d+) seq=(\d+) payload_seq=(\d+)$')


def scan_process(raw, err, process, boot):
    result = {'transport_complete': False, 'standard_scan_succeeded': False,
              'standard_bss_result': False, 'stdout_sha256': hashlib.sha256(raw).hexdigest(),
              'stderr_sha256': hashlib.sha256(err).hexdigest()}
    complete = (process['stdout_bytes'] == len(raw) and
                process['stderr_bytes'] == len(err) and process['stdin_complete'] is True and
                process['exit_status'] == 0 and process['reason'] is None)
    prefix = ('boot_before=' + boot + '\nkernel=' + RELEASE +
              '\ninterface_created=1\ninterface_up=1\n__IW_PASSIVE_BEGIN__\n').encode()
    suffix = re.search(rb'__IW_PASSIVE_END__\nscan_exit=(\d+)\nboot_after=([0-9a-f-]+)\n$', raw)
    if not complete or not raw.startswith(prefix) or suffix is None or suffix[2] != boot.encode():
        return result
    body = raw[len(prefix):suffix.start()]
    result['transport_complete'] = True
    result['interface_created'] = True
    result['interface_up'] = True
    result['scan_exit'] = int(suffix[1])
    result['standard_scan_succeeded'] = int(suffix[1]) == 0 and not err
    result['standard_bss_result'] = bool(re.search(
        rb'^BSS [0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\(', body, re.MULTILINE))
    return result


def prepare(candidate):
    prepared = PREPARE(candidate)
    source = SCAN_SOURCE.read_bytes()
    PARENT.HOST.require(not SCAN_SOURCE.is_symlink() and len(source) <= 16384,
                        'scan script source changed')
    globals_ = prepared['execute'].__globals__
    invoke = globals_['invoke']
    globals_['BUDGETS']['passive-scan'] = (30, 262144)
    prepared['claim']['phase_budgets']['passive-scan'] = {
        'connections': 1, 'seconds': 30, 'stdout_bytes': 262144, 'stderr_bytes': 16384}
    prepared['claim']['passive_scan_script_sha256'] = hashlib.sha256(source).hexdigest()
    consumed = False

    def invoke_with_scan(active, label, script, *, network_status=None):
        nonlocal consumed
        if label == 'log-export':
            if consumed:
                raise ValueError('passive scan phase already consumed')
            consumed = True
            # Observation and candidate-byte probe passed before this phase.
            observation = json.loads((ROOT / 'observation-result.json').read_bytes())
            boot = observation['boot_id']
            HOST.require(isinstance(boot, str) and re.fullmatch(
                r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', boot) is not None,
                'authenticated boot identity is malformed')
            # Print no identifiers or raw scan data outside ignored captures.
            bound = ('EXPECTED_BOOT=' + boot + '\nexport EXPECTED_BOOT\n').encode() + source
            try:
                raw, err, process = invoke(active, 'passive-scan', bound)
                result = scan_process(raw, err, process, boot)
            except (OSError, ValueError, KeyError, TypeError) as error:
                result = {'transport_complete': False, 'standard_scan_succeeded': False,
                          'standard_bss_result': False, 'reason': str(error)}
            active['collector'].write_new(ROOT / 'passive-scan-userspace.json',
                                           HOST.DOMAIN.HOST.encoded(result))
        return invoke(active, label, script, network_status=network_status)

    globals_['invoke'] = invoke_with_scan
    return prepared


HOST.DOMAIN.prepare = prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    os.umask(0o077)
    if not args.execute:
        prepare(args.candidate)
        print('offline-preparation=pass; device_action=none')
        return 0
    # The parent validates WMT/START identities and owns one log/recovery run.
    rc = HOST.main()
    log = ROOT / 'kmsg.log'
    if not log.is_file():
        return rc or 1
    initial = PARENT.classify(log)
    lines = log.read_bytes().splitlines()
    summaries = [match for line in lines if (match := SUMMARY.search(line))]
    dones = [match for line in lines if (match := DONE.search(line))]
    admitted = sum(b'one-shot passive WLAN scan: admitted=1' in line for line in lines)
    userspace_path = ROOT / 'passive-scan-userspace.json'
    userspace = json.loads(userspace_path.read_bytes()) if userspace_path.is_file() else {}
    session = json.loads((ROOT / 'session-result.json').read_bytes())
    result = {
        'initial_configuration_and_accounting_pass': initial['accepted'],
        'single_scan_admitted': admitted == 1,
        'matching_done_header': len(dones) == 1 and
            tuple(int(value) for value in dones[0].groups()) == (24, 0, 1),
        'scan_completed': len(summaries) == 1 and int(summaries[0][1]) == 0 and
            summaries[0][2] == b'1',
        'native_management_frame_seen': len(summaries) == 1 and summaries[0][3] == b'1',
        'validated_beacon_reported': len(summaries) == 1 and summaries[0][4] == b'1',
        'runtime_credit_returned': len(summaries) == 1 and summaries[0][5] == b'1',
        'wire_lifetime_retired': len(summaries) == 1,
        'standard_scan_succeeded': userspace.get('standard_scan_succeeded') is True,
        'standard_bss_result': userspace.get('standard_bss_result') is True,
        'a53_regression_pass': session.get('regression_pass') is True,
        'gemian_recovery_confirmed': session.get('recovery_confirmed') is True,
        'kernel_release': RELEASE,
        'complete_log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
        'wifi_operational': False,
    }
    result['passive_scan_demonstrated'] = all(result[key] for key in (
        'initial_configuration_and_accounting_pass', 'single_scan_admitted',
        'matching_done_header', 'scan_completed', 'validated_beacon_reported',
        'standard_scan_succeeded', 'standard_bss_result', 'a53_regression_pass',
        'gemian_recovery_confirmed'))
    with (ROOT / 'passive-scan-result.json').open('xb') as stream:
        stream.write(HOST.DOMAIN.HOST.encoded(result))
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(result, sort_keys=True))
    return rc or (0 if result['passive_scan_demonstrated'] else 1)


if __name__ == '__main__':
    raise SystemExit(main())
