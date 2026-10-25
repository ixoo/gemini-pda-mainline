#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Throughput verdict gates that apply to a credit-retire, steady-state run.

usage: throughput_verdict.py <work-dir>   (after bind rendered hosts/; also
applied to this experiment's classify-throughput.py with --source)

Every steady-state run since boot H failed the verdict on gates written for
earlier protocols, while its data was whole: the low-traffic sample ceilings
(`counts_ok`: 512 frames and 1 MiB; `gtk_counters_consistent`: the 60 s GTK
budget), the 1 s protocol's 1.5 s chunk bound, and the depth-four PID trace,
which cannot hold once ordinary data is retired on credit arrival without a
PID (0278). The verdict keeps every gate that still means something (the
receipt, the verified boot, healthy cleanup, the key sequence, no fault, the
declared chunk count) and replaces the stale ones: no native ciphertext
reached the core and the counters are monotone; each chunk inside the
device's declared bound; and, where the credit-retire record is present, it
is the ownership proof (nothing expired, no PID fault, no pages left, no
failed transmit). The retained fields stay in the record unchanged.

It also records 0283's receive gaps per direction, only those inside the
direction's start and end markers (on the kernel clock, like the gaps); the
driver does not know the leaf's phases, so the windowing is applied here, and
a gap kept in the record is a stall by construction. Not a verdict gate.

A failed verdict names itself: the receipt lists the checks that cleared
`all_pass` (`all_pass_failed`), and the verdict lists the gates that failed
with their phase (`verdict_failed`, `receipt:` or `classifier:`), so a
`session_exit=1` is read from the record, not reconstructed by hand.
"""
import sys
from pathlib import Path


def apply(path):
    s = path.read_text()

    def literal(old, new):
        nonlocal s
        assert s.count(old) == 1, (path.name, old[:60], s.count(old))
        s = s.replace(old, new)

    literal("    if data_depth not in (1, 4):\n        raise ValueError('only reviewed data depths one and four are supported')\n",
            "    if data_depth not in (1, 4, 8, 12, 16):\n        raise ValueError('only reviewed data depths one, four, eight, twelve and sixteen are supported')\n")
    literal("    ledger_ok = True\n    if data_depth == 4:\n",
            "    ledger_ok = True\n    retire = credit_retire_record(kmsg)\n    if retire is not None:\n"
            "        # ordinary data carries no PID under credit retire (0278): its end record is the ownership proof\n"
            "        value['credit_retire_ownership'] = retire\n"
            "        ledger_ok = retire['whole']\n    elif data_depth == 4:\n")
    literal("                  all(c.get('elapsed_ns') is not None and 0<c['elapsed_ns']<=1.5e9 for c in d['chunks'])\n",
            "                  all(c.get('elapsed_ns') is not None and 0<c['elapsed_ns']<=chunk_limit for c in d['chunks'])\n")
    literal("    declared = measurement.get('chunks_each', 5)   # a predeclared shorter run is not a censored one\n",
            "    declared = measurement.get('chunks_each', 5)   # a predeclared shorter run is not a censored one\n"
            "    # each chunk inside the device's declared bound; the 1 s protocol's 1.5 s otherwise\n"
            "    chunk_limit = (measurement['device_bound_seconds'] + 0.5) * 1e9 if measurement.get('device_bound_seconds') else 1.5e9\n"
            "    native = native_record(kmsg)\n")
    literal("                  value.get('healthy_cleanup') and value.get('counts_ok') and\n"
            "                  value.get('sequence_ok') and value.get('gtk_counters_consistent') and not value.get('fault') and ledger_ok)\n",
            "                  value.get('healthy_cleanup') and native['ok'] and\n"
            "                  value.get('sequence_ok') and not value.get('fault') and ledger_ok)\n")
    literal("        direction['device_tx_status_nonzero'] = sum(int(m[1]) != 0 for m in done)\n",
            "        direction['device_tx_status_nonzero'] = sum(int(m[1]) != 0 for m in done)\n"
            "        # receive gaps (0283) kept only inside this direction's markers: idle outside them is expected\n"
            "        gaps = [g for g in re.findall(rb'one-shot WLAN data rx gap: ([^\\r\\n]+)', kmsg)]\n"
            "        inside = [g.decode() for g in gaps if start <= int(re.search(rb'start_ns=(\\d+)', g)[1]) < end]\n"
            "        direction['rx_gaps_in_window'] = inside\n"
            "        direction['rx_gaps_outside_window'] = len(gaps) - len(inside)\n")
    literal("    value.update(throughput_measurement=measurement,throughput_baseline_pass=passed,\n",
            "    value.update(native_ciphertext=native, chunk_limit_ns=int(chunk_limit),\n"
            "                 verdict_gates={'receipt_all_pass': bool(receipt and receipt.get('all_pass')), 'verified_boot': bool(verified_boot),\n"
            "                                'timing': timing, 'healthy_cleanup': bool(value.get('healthy_cleanup')),\n"
            "                                'native_ciphertext_ok': native['ok'], 'sequence_ok': bool(value.get('sequence_ok')),\n"
            "                                'no_fault': not value.get('fault'), 'ownership': ledger_ok},\n"
            "                 retained_not_gated=['counts_ok', 'gtk_counters_consistent', 'queued_count_ok'])\n"
            "    value['verdict_failed'] = ['receipt:' + name for name in (receipt or {}).get('all_pass_failed', [])] + \\\n"
            "        ['classifier:' + gate for gate, ok in value['verdict_gates'].items() if not ok]\n"
            "    value.update(throughput_measurement=measurement,throughput_baseline_pass=passed,\n")
    literal("\ndef cleanup_record(kmsg):\n", '''
def credit_retire_record(kmsg):
    """The credit-retire end record and the data end's failed count, or None."""
    ends = re.findall(rb'one-shot WLAN join data credit retire end: retired=(\\d+) expired=(\\d+) '
                      rb'pid_faults=(\\d+) wait_avg_us=\\d+ wait_max_us=\\d+ left_pages=(\\d+) ', kmsg)
    data = re.findall(rb'one-shot WLAN join data phase end: reason=\\S+ elapsed_ms=\\d+ .*?tx_failed=(\\d+) ', kmsg)
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
        rb'one-shot WLAN native-diag: state=\\d+ act=\\d+ total=(\\d+) native=(\\d+) bytes=(\\d+)\\r?$', kmsg, re.M)]
    monotone = all(counts[i][j] >= counts[i - 1][j] for i in range(1, len(counts)) for j in range(3))
    return {'records': len(counts), 'native_last': counts[-1][1] if counts else None,
            'ok': bool(counts) and all(c[1] == 0 for c in counts) and monotone}


def cleanup_record(kmsg):
''')
    compile(s, str(path), 'exec')
    path.write_text(s)


def apply_receipt(path):
    """The receipt names the checks that cleared all_pass."""
    s = path.read_text()
    old = """    for direction in measured.values():
        directions_ok = bool(directions_ok and direction.get('completed') and"""
    new = """    failed = [] if result['all_pass'] else ['retained receipt checks']
    if not directions_ok: failed.append('directions present with received bytes')
    for label, direction in measured.items():
        for name, ok in (('completed', direction.get('completed')), ('errors', not direction['errors']),
                         ('expected_termination', direction['expected_termination']),
                         ('device_cpu', direction['device_cpu']['valid']), ('bytes', direction['bytes']>0),
                         ('chunk_count', len(direction.get('chunks',[]))==CHUNKS),
                         ('chunk_progress', direction['chunk_progress_valid']),
                         ('chunk_exits', all(c.get('device_exit') in (0,124,143,1,141) for c in direction['chunks'])),
                         ('netdev_counters', set(direction.get('netdev_delta',{}))==counter_names and
                          min(direction['netdev_delta'].values())>=0)):
            if not ok: failed.append(label + '.' + name)
    if not remote['quiesced']: failed.append('remote quiescence')
    if not control['accepted']: failed.append('core disconnect')
    for direction in measured.values():
        directions_ok = bool(directions_ok and direction.get('completed') and"""
    assert s.count(old) == 1, 'receipt anchor (directions)'
    s = s.replace(old, new)
    old = """    result['all_pass'] = bool(result['all_pass'] and remote['quiesced'] and
                              control['accepted'] and directions_ok)
"""
    assert s.count(old) == 1, 'receipt anchor (all_pass)'
    s = s.replace(old, old + "    result['all_pass_failed'] = failed\n")
    compile(s, str(path), 'exec')
    path.write_text(s)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--source']:
        apply(Path(sys.argv[2]))
    else:
        apply(Path(sys.argv[1]) / 'hosts/classify-throughput.py')
        apply_receipt(Path(sys.argv[1]) / 'hosts/throughput-helper.py')
    print('throughput verdict: stale gates replaced (native ciphertext, declared chunk bound, credit-retire ownership); retained fields recorded')
