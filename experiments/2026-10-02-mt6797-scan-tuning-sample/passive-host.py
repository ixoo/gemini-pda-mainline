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
ROOT = PRIVATE_REPO / 'artifacts/scan-tuning-sample/session-1'
CAPTURE = PRIVATE_REPO / 'artifacts/scan-tuning-sample/capture-1'
SOURCE = HERE.parent / '2026-10-01-mt6797-tc4-reconcile/passive-host.py'
SPEC = importlib.util.spec_from_file_location('tc4_scan_parent', SOURCE)
PARENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PARENT)
RELEASE = '7.1.3-gemini-a53-wifi-scan-tuning-sample'
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

TIMING = re.compile(rb'one-shot passive WLAN timing: requested_ms=(\d+) elapsed_us=(\d+) channels=(\d+)$')


def timing_result(lines):
    matches = [match for line in lines if (match := TIMING.search(line))]
    result = {'timing_observation_complete': False,
              'nominal_dwell_timing_consistent': False,
              'effective_rf_dwell_verified': False}
    if len(matches) != 1:
        return result
    requested, elapsed, channels = (int(value) for value in matches[0].groups())
    result.update(requested_channel_dwell_ms=requested,
                  host_elapsed_us=elapsed, scan_channel_count=channels)
    result['timing_observation_complete'] = requested == 500 and channels == 1
    result['nominal_dwell_timing_consistent'] = (
        result['timing_observation_complete'] and 500000 <= elapsed <= 6000000)
    return result


COUNT = re.compile(rb'one-shot passive WLAN firmware scan count: version=(\d+) management=(\d+) pno=(\d+)$')


def count_result(lines):
    matches = [match for line in lines if (match := COUNT.search(line))]
    result = {'firmware_count_observation_complete': False,
              'firmware_management_processing_seen': False}
    if len(matches) != 1:
        return result
    version, count, pno = (int(value) for value in matches[0].groups())
    result.update(firmware_scan_done_version=version,
                  firmware_management_processing_count=count,
                  firmware_scan_pno=pno)
    complete = 3 <= version <= 255 and count <= 0xffffffff and pno in (0, 1)
    result['firmware_count_observation_complete'] = complete
    result['firmware_management_processing_seen'] = complete and count > 0
    return result



TUNING = re.compile(rb'one-shot passive WLAN tuning sample: sample=(\d+) role=(\d+) value=(\d+) sent_us=(\d+) received_us=(\d+) post_done=([01])$')
TUNING_SUMMARY = re.compile(rb'one-shot passive WLAN tuning summary: submitted=(\d+) received=(\d+) pending=([01]) atomic=0 rf_proven=0$')


def tuning_result(lines):
    result = {'tuning_samples_complete': False,
              'tuning_samples_before_done': False,
              'sampled_band_channel_matches_request': False,
              'tuning_samples_atomic': False, 'rf_tuning_verified': False}
    matches = [m for line in lines if (m := TUNING.search(line))]
    summaries = [m for line in lines if (m := TUNING_SUMMARY.search(line))]
    if (len(matches) != 4 or len(summaries) != 1 or
            sum(b'one-shot passive WLAN tuning sample:' in line for line in lines) != 4 or
            sum(b'one-shot passive WLAN tuning summary:' in line for line in lines) != 1 or
            tuple(int(v) for v in summaries[0].groups()) != (4, 4, 0)):
        return result
    samples = []
    prior_received = 0
    for index, match in enumerate(matches):
        sample, role, value, sent, received, post_done = (int(v) for v in match.groups())
        if (sample != index // 2 or role != index % 2 or value > 0xffffffff or
                sent < (100000 if sample == 0 else 300000) or
                sent < prior_received or not sent <= received < sent + 100000 or
                received > 6000000):
            return result
        samples.append({'sample': sample, 'role': role, 'value': value,
                        'sent_us': sent, 'received_us': received,
                        'post_done': bool(post_done)})
        prior_received = received
    pairs = []
    for index in (0, 2):
        band, channel = samples[index]['value'], samples[index + 1]['value']
        pairs.append({'band_base': band, 'fixed_override': channel & 255,
                      'requested_channel': (channel >> 8) & 255,
                      'center_channel': (channel >> 16) & 255,
                      'bandwidth': (channel >> 24) & 255})
    result.update(tuning_samples_complete=True, tuning_samples=samples,
                  tuning_channel_pairs=pairs,
                  tuning_samples_before_done=not any(s['post_done'] for s in samples),
                  sampled_band_channel_matches_request=all(
                      p['band_base'] == 5000000 and p['fixed_override'] == 0 and
                      p['requested_channel'] == 40 for p in pairs))
    return result


def scan_process(raw, err, process, boot):
    result = {'transport_complete': False, 'standard_scan_succeeded': False,
              'standard_bss_result': False, 'channel40_permitted': False,
              'standard_5g_bss_result': False, 'stdout_sha256': hashlib.sha256(raw).hexdigest(),
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
    phy = re.search(rb'__PHY_INFO_BEGIN__\n(.*?)__PHY_INFO_END__\n', body, re.DOTALL)
    if phy is not None:
        lines = [line for line in phy[1].splitlines() if b'* 5200 MHz [40]' in line]
        result['channel40_permitted'] = len(lines) == 1 and b'(disabled)' not in lines[0]
        body = body[phy.end():]
    result['transport_complete'] = True
    result['interface_created'] = True
    result['interface_up'] = True
    result['scan_exit'] = int(suffix[1])
    result['standard_scan_succeeded'] = int(suffix[1]) == 0 and not err
    result['standard_bss_result'] = bool(re.search(
        rb'^BSS [0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\(', body, re.MULTILINE))
    # Only a frequency within a standard BSS block establishes this band.
    in_bss = False
    for line in body.splitlines():
        if line.startswith(b'BSS '):
            in_bss = bool(re.match(rb'BSS [0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}\(', line))
        if in_bss and re.fullmatch(rb'\s*freq: (5180|5200|5220|5240)\s*', line):
            result['standard_5g_bss_result'] = True
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
        # Exact candidate code admits the scan only after filter submission.
        'supported_broadcast_filter_submitted': admitted == 1,
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
        'channel40_permitted': userspace.get('channel40_permitted') is True,
        'standard_5g_bss_result': userspace.get('standard_5g_bss_result') is True,
        'a53_regression_pass': session.get('regression_pass') is True,
        'gemian_recovery_confirmed': session.get('recovery_confirmed') is True,
        'kernel_release': RELEASE,
        'complete_log_sha256': hashlib.sha256(log.read_bytes()).hexdigest(),
        'wifi_operational': False,
    }
    result.update(timing_result(lines))
    result.update(count_result(lines))
    result['counter_diagnostic_complete'] = all(result[key] for key in (
        'initial_configuration_and_accounting_pass', 'single_scan_admitted',
        'timing_observation_complete', 'matching_done_header', 'scan_completed',
        'runtime_credit_returned', 'standard_scan_succeeded', 'channel40_permitted',
        'a53_regression_pass', 'gemian_recovery_confirmed',
        'firmware_count_observation_complete'))
    result['counter_diagnosis'] = 'inconclusive'
    if result['counter_diagnostic_complete'] and not result['native_management_frame_seen']:
        result['counter_diagnosis'] = ('firmware-processing-without-host-frame'
                                       if result['firmware_management_processing_seen']
                                       else 'no-firmware-management-count')
    result.update(tuning_result(lines))
    result['tuning_diagnostic_complete'] = (result['counter_diagnostic_complete'] and
                                            result['tuning_samples_complete'] and
                                            result['tuning_samples_before_done'])
    result['tuning_diagnosis'] = 'inconclusive'
    if result['tuning_diagnostic_complete'] and not result['native_management_frame_seen']:
        if result['firmware_management_processing_seen']:
            result['tuning_diagnosis'] = 'firmware-processing-without-host-frame'
        elif result['sampled_band_channel_matches_request']:
            result['tuning_diagnosis'] = 'requested-software-state-without-management-count'
        else:
            result['tuning_diagnosis'] = 'different-channel-software-state'
    result['passive_scan_demonstrated'] = all(result[key] for key in (
        'initial_configuration_and_accounting_pass', 'single_scan_admitted',
        'timing_observation_complete', 'matching_done_header', 'scan_completed', 'validated_beacon_reported',
        'standard_scan_succeeded', 'standard_bss_result', 'channel40_permitted',
        'standard_5g_bss_result', 'a53_regression_pass',
        'gemian_recovery_confirmed'))
    with (ROOT / 'passive-scan-result.json').open('xb') as stream:
        stream.write(HOST.DOMAIN.HOST.encoded(result))
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps(result, sort_keys=True))
    return rc or (0 if result['passive_scan_demonstrated'] else 1)


if __name__ == '__main__':
    raise SystemExit(main())
