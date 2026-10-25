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
    if data_depth not in (1, 4):
        raise ValueError('only reviewed data depths one and four are supported')
    value = base['classify'](kmsg,receipt,verified_boot,protocol)
    # The immutable cohort predates the delivery suffix. Adapt only its cleanup
    # grammar; all ledger, sequence, counter, fault and receipt gates stay live.
    healthy, delivery = cleanup_record(kmsg)
    value.update(healthy_cleanup=healthy, cleanup_delivery=delivery)
    ledger_ok = True
    if data_depth == 4:
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
    directions = measurement.get('directions',{})
    declared = measurement.get('chunks_each', 5)   # a predeclared shorter run is not a censored one
    timing = bool(len(directions)==2 and all(d.get('completed') and
                  len(d.get('chunks',[]))==declared and
                  all(c.get('elapsed_ns') is not None and 0<c['elapsed_ns']<=1.5e9 for c in d['chunks'])
                  for d in directions.values()))
    passed = bool(verified_boot and receipt and receipt.get('all_pass') and timing and
                  value.get('healthy_cleanup') and value.get('counts_ok') and
                  value.get('sequence_ok') and value.get('gtk_counters_consistent') and not value.get('fault') and ledger_ok)
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
