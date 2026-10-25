#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Measurement verdict separate from the consumed ten-minute stream verdict."""
import os
import hashlib
from pathlib import Path
import re
import runpy

base = runpy.run_path(str(Path(os.environ['TP_SOURCE_ROOT'])/'experiments/2026-10-13-mt6797-wifi-native-delivery-probe/classify-ccmp-connected-p2.py'))
read_protocol = base['read_protocol']


def depth_decoder(source, namespace):
    """Derive only depth-four ownership from the exact retained decoder."""
    source = source[source.index('def pid_trace('):source.index('\n\ndef classify(')]
    if hashlib.sha256(source.encode()).hexdigest() != '1ebc187625d94832bf6125168da1fa9e3ff00d342d46f7ab9bef00c95736ff58':
        raise ValueError('retained PID decoder changed')
    for old, new in (
        ('pending=timing=None', 'pending={}\n    timing=None'),
        ("if pending or timing:fail('allocation overlaps outstanding completion')",
         "if timing:fail('allocation overlaps completion timing')"),
        ('if pid!=127 or ordinal!=0 or reserved or not data_ended or wraps!=allocated//126:',
         'if pending or pid!=127 or ordinal!=0 or reserved or not data_ended or wraps!=allocated//126:'),
        ('if reserved or ordinal!=allocated+1 or pid!=(ordinal-1)%126+1 or wraps!=ordinal//126:',
         'if reserved or len(pending)>=4 or pid in pending or ordinal!=allocated+1 or pid!=(ordinal-1)%126+1 or wraps!=ordinal//126:'),
        ('pending=(pid,ordinal)', 'pending[pid]=ordinal'),
        ('if pending!=(pid,ordinal) or ordinal!=completed+1 or wraps!=allocated//126:',
         'if pid not in pending or ordinal!=completed+1 or wraps!=allocated//126:'),
        ("fail('completion does not retire its single owner')",
         "fail('completion does not retire its exact PID owner')"),
        ('pending=None', 'owner_ordinal=pending.pop(pid,None)'),
        ('reused+=ordinal>126', 'reused+=bool(owner_ordinal and owner_ordinal>126)'),
        ('timing=(pid,ordinal)', 'timing=(pid,owner_ordinal)'),
        ('pending[0] if pending else 0', 'len(pending)'),
    ):
        if source.count(old) != 1:
            raise ValueError('depth-four decoder anchor changed')
        source = source.replace(old, new)
    derived = dict(namespace)
    exec(compile(source, '<depth-four PID ownership>', 'exec'), derived)
    return derived['pid_trace']


def credit_retire_record(kmsg):
    """The credit-retire end record and the data end's failed count, or None."""
    ends = re.findall(rb'one-shot WLAN join data credit retire end: retired=(\d+) expired=(\d+) '
                      rb'pid_faults=(\d+) wait_avg_us=\d+ wait_max_us=\d+ left_pages=(\d+) ', kmsg)
    data = re.findall(rb'one-shot WLAN join data phase end: reason=\S+ elapsed_ms=\d+ .*?tx_failed=(\d+) ', kmsg)
    if not ends:
        return None
    retired, expired, faults, left = map(int, ends[0])
    failed = int(data[0]) if len(data) == 1 else None
    return {'records': len(ends), 'retired': retired, 'expired': expired, 'pid_faults': faults,
            'left_pages': left, 'tx_failed': failed,
            'whole': len(ends) == 1 and retired > 0 and expired == faults == left == 0 and failed == 0}


def native_record(kmsg):
    """No native ciphertext reached the core and the diagnostic counters only grew."""
    counts = [tuple(map(int, m)) for m in re.findall(
        rb'one-shot WLAN native-diag: state=\d+ act=\d+ total=(\d+) native=(\d+) bytes=(\d+)\r?$', kmsg, re.M)]
    monotone = all(counts[i][j] >= counts[i - 1][j] for i in range(1, len(counts)) for j in range(3))
    return {'records': len(counts), 'native_last': counts[-1][1] if counts else None,
            'ok': bool(counts) and all(c[1] == 0 for c in counts) and monotone}


def cleanup_record(kmsg):
    """Accept the retained terminal grammar and its explicit delivery suffix.

    Cleanup proves resource retirement. The suffix reports delivery separately;
    neither a flushed nor a missing completion becomes transmitted here.
    """
    records = [line for line in kmsg.splitlines()
               if b'one-shot WLAN join cleanup:' in line]
    if len(records) != 1:
        return False, None
    match = re.search(rb'one-shot WLAN join cleanup: stage=3 credits=returned '
                      rb'slots=retired deauth=[01](?: delivery='
                      rb'(transmitted|flushed|missing|unclassified))?$', records[0])
    return bool(match), (match[1].decode() if match and match[1] else None)


def classify(kmsg, receipt, verified_boot, protocol=None, data_depth=1):
    if data_depth not in (1, 4, 8, 12, 16):
        raise ValueError('only reviewed data depths one, four, eight, twelve and sixteen are supported')
    value = base['classify'](kmsg,receipt,verified_boot,protocol)
    # The immutable cohort predates the delivery suffix. Adapt only its cleanup
    # grammar; all ledger, sequence, counter, fault and receipt gates stay live.
    healthy, delivery = cleanup_record(kmsg)
    value.update(healthy_cleanup=healthy, cleanup_delivery=delivery)
    ledger_ok = True
    retire = credit_retire_record(kmsg)
    if retire is not None:
        # ordinary data carries no PID under credit retire (0278): its end record is the ownership proof
        value['credit_retire_ownership'] = retire
        ledger_ok = retire['whole']
    elif data_depth == 4:
        origin = Path(os.environ['TP_SOURCE_ROOT'])/'experiments/2026-10-13-mt6797-wifi-native-delivery-probe/classify-ccmp-connected.py'
        trace = depth_decoder(origin.read_text(), base['classify'].__globals__)(kmsg)
        value['pid_ownership'] = trace
        ledger_ok = bool(trace['trace_valid'] and trace['whole_after_cleanup'])
    measurement = (receipt or {}).get('throughput_measurement',{})
    for label, direction in measurement.get('directions',{}).items():
        start, end = direction.get('device_start_ns'), direction.get('device_end_ns')
        if start is None or end is None:
            continue
        records = []
        for line in kmsg.splitlines():
            m = re.match(rb'^\d+,\d+,(\d+),[^;]*;(.*)',line)
            if m and start <= int(m[1])*1000 < end:
                records.append(m[2])
        done = [m for line in records if (m:=re.search(rb'one-shot WLAN join TX done: pid=\d+ status=(\d+)',line))]
        direction['device_clock_resolution_ns'] = 10000000
        direction['completion_interval'] = 'start-inclusive, end-exclusive; boundary uncertainty one device clock tick'
        direction['device_tx_status_completions'] = len(done)
        direction['device_tx_status_nonzero'] = sum(int(m[1]) != 0 for m in done)
        # receive gaps (0283) kept only inside this direction's markers: idle outside them is expected
        gaps = [g for g in re.findall(rb'one-shot WLAN data rx gap: ([^\r\n]+)', kmsg)]
        inside = [g.decode() for g in gaps if start <= int(re.search(rb'start_ns=(\d+)', g)[1]) < end]
        direction['rx_gaps_in_window'] = inside
        direction['rx_gaps_outside_window'] = len(gaps) - len(inside)
    directions = measurement.get('directions',{})
    declared = measurement.get('chunks_each', 5)   # a predeclared shorter run is not a censored one
    # each chunk inside the device's declared bound; the 1 s protocol's 1.5 s otherwise
    chunk_limit = (measurement['device_bound_seconds'] + 0.5) * 1e9 if measurement.get('device_bound_seconds') else 1.5e9
    native = native_record(kmsg)
    timing = bool(len(directions)==2 and all(d.get('completed') and
                  len(d.get('chunks',[]))==declared and
                  all(c.get('elapsed_ns') is not None and 0<c['elapsed_ns']<=chunk_limit for c in d['chunks'])
                  for d in directions.values()))
    passed = bool(verified_boot and receipt and receipt.get('all_pass') and timing and
                  value.get('healthy_cleanup') and native['ok'] and
                  value.get('sequence_ok') and not value.get('fault') and ledger_ok)
    value.update(native_ciphertext=native, chunk_limit_ns=int(chunk_limit),
                 verdict_gates={'receipt_all_pass': bool(receipt and receipt.get('all_pass')), 'verified_boot': bool(verified_boot),
                                'timing': timing, 'healthy_cleanup': bool(value.get('healthy_cleanup')),
                                'native_ciphertext_ok': native['ok'], 'sequence_ok': bool(value.get('sequence_ok')),
                                'no_fault': not value.get('fault'), 'ownership': ledger_ok},
                 retained_not_gated=['counts_ok', 'gtk_counters_consistent', 'queued_count_ok'])
    value['verdict_failed'] = ['receipt:' + name for name in (receipt or {}).get('all_pass_failed', [])] + \
        ['classifier:' + gate for gate, ok in value['verdict_gates'].items() if not ok]
    value.update(throughput_measurement=measurement,throughput_baseline_pass=passed,
                 provisional_ccmp_compatibility_pass=passed,ten_minute_ssh_proven=False,
                 same_boot_reconnect_proven=False,maintained_wifi_support=False,
                 measurement_censored=not timing,
                 measurement_short_by=None if timing and declared == 5 else ('declaration' if timing else 'fault'),
                 chunks_declared=declared)
    return value


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kmsg', type=Path)
    parser.add_argument('receipt', type=Path)
    parser.add_argument('verified_boot')
    parser.add_argument('protocol_root', nargs='?')
    parser.add_argument('--data-depth', type=int, choices=(1, 4), default=1)
    args = parser.parse_args()
    protocol = read_protocol(args.protocol_root, args.verified_boot) if args.protocol_root else None
    print(json.dumps(classify(args.kmsg.read_bytes(), json.loads(args.receipt.read_text()),
                              args.verified_boot, protocol, args.data_depth), indent=2))
