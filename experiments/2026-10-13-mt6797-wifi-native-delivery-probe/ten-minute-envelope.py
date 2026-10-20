#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixed P2 source derivations from the proven P1D host, not a runtime control API.

Keep the immutable two-minute client and decoder as the reviewed origin. Every
replacement is counted and source-pinned; unrelated text or predicates refuse.
"""
import hashlib
import re

HELPER_SHA = '31b65043570988dc3f9d06cd3269cd98e9c8015d48f45bc6fa838c7b20d4b3bf'
CLASSIFIER_SHA = '5d8355ebbe2a385502f98d5a1016054aea419cd8f6e991d6a8388c394c1822ae'
STEPS_SHA = '762616bb386647e0a25addd36ad9dba2f6384ebde4858f89a806a32678fc60fc'


def checked(source, digest):
    if hashlib.sha256(source.encode()).hexdigest() != digest:
        raise ValueError('reviewed P1D source changed')
    return source


def literal(source, old, new, count):
    if source.count(old) != count:
        raise ValueError('fixed P2 source anchor changed: ' + old)
    return source.replace(old, new)


def number(source, old, new, count):
    pattern = r'(?<![A-Za-z0-9_])' + re.escape(old) + r'(?![A-Za-z0-9_])'
    result, actual = re.subn(pattern, new, source)
    if actual != count:
        raise ValueError('fixed P2 scalar anchor changed: ' + old)
    return result


def helper(source):
    source = checked(source, HELPER_SHA)
    source = literal(source, 'P1', 'P2', 35)
    source = literal(source, 'p1', 'p2', 24)
    # Clock resolution is invariant receipt metadata; avoid repeating the same
    # constant in each of 602 chunks so all raw output fits the existing 64 KiB.
    source = literal(source, ' clock_resolution_ns=10000000', '', 2)
    source = literal(source, 'span >= 120_000_000_000', 'span >= 600_000_000_000', 1)
    for old, new, count in [
        ('242', '601', 1), ('243', '602', 6),
        ('500000000', '1000000000', 1), ('500_000_000', '1_000_000_000', 1),
        ('120000', '600000', 1), ('121000', '601000', 1),
        ('121_000_000_000', '601_000_000_000', 2),
        ('120_000_000_000', '604_000_000_000', 2),
        ('120000000000', '604000000000', 1),
        ('135000000000', '608000000000', 1),
        ('135_000_000_000', '608_000_000_000', 3),
        ('140_000_000_000', '613_000_000_000', 1),
        ('125', '610', 2), ('135', '625', 4),
        ('210', '710', 7), ('270', '770', 1),
    ]:
        source = number(source, old, new, count)
    compile(source, '<P2 fixed host envelope>', 'exec')
    return source


def classifier(source):
    source = checked(source, CLASSIFIER_SHA)
    source = literal(source, 'P1', 'P2', 1)
    source = literal(source, 'p1', 'p2', 3)
    source = literal(source, '120000000000<=before', '604000000000<=before', 1)
    for old, new, count in [
        ('11', '59', 3), ('120', '600', 1),
        ('120000', '600000', 2), ('121000', '601000', 2),
        ('120000000000', '600000000000', 2),
        ('121000000000', '601000000000', 1),
        ('135000000000', '608000000000', 1),
        ('140000000000', '613000000000', 1),
    ]:
        source = number(source, old, new, count)
    # Duration is an authenticated received-stream claim; maintained support,
    # key erasure and same-boot reconnect retain their separate false verdicts.
    source = literal(source, 'ten_minute_ssh_proven=False',
                     'ten_minute_ssh_proven=bool(duration and result[\'authenticated\'])', 1)
    compile(source, '<P2 fixed verdict envelope>', 'exec')
    return source


def log_contract(namespace, path):
    """Scope only the actual complete-log classifier to the P2 logger's bound.

    The retained origin file and all framing/seal/syscall checks stay pinned.
    Both module loaders and runpy callers must bind this same contract before
    P2 preparation; the finished preparation checks that binding explicitly.
    """
    import inspect
    if hashlib.sha256(path.read_bytes()).hexdigest() != STEPS_SHA:
        raise ValueError('reviewed log decoder origin changed')
    values = namespace if isinstance(namespace, dict) else vars(namespace)
    original = values['classify_log']
    if getattr(original, 'p2_logger_deadline_ms', None) == 900000:
        return namespace
    source = inspect.getsource(original)
    source = literal(source, '600000', '900000', 2)
    state = original.__globals__
    exec(compile(source, '<P2 900-second log contract>', 'exec'), state)
    adapted = state['classify_log']
    adapted.p2_logger_deadline_ms = 900000
    values['classify_log'] = adapted
    return namespace


def reserved_submission_offsets(kmsg):
    """Derive free diagnostics from existing same-kmsg-clock observations.

    The reference is the PM-credit announcement's log timestamp. This is not a
    wire TX timestamp or proof of any firmware timer's phase or mechanism.
    """
    records = []
    for line in kmsg.splitlines():
        match = re.fullmatch(rb'\d+,\d+,(\d+),[^;]*;(.*)', line)
        if match:
            records.append((int(match[1]), match[2]))
    clocks = [(stamp, int(m[1])) for stamp, text in records if
              (m := re.search(rb'one-shot WLAN PM credit clock: ns=(\d+)$', text))]
    frames = [(stamp, int(m[1])) for stamp, text in records if
              (m := re.search(rb'one-shot WLAN join TX: subtype=12 pid=(\d+) pages=1$', text))]
    output = []
    for stamp, pid in frames:
        frame = {'submission_log_time_us': stamp, 'pid': pid, 'offset_known': False}
        if len(clocks) == 1 and stamp >= clocks[0][0]:
            offset = stamp - clocks[0][0]
            index = (offset + 15000000) // 30000000
            frame.update(offset_known=True, pm_relative_log_offset_ns=offset*1000,
                         nearest_nominal_pm_30s_index=index,
                         signed_offset_from_nearest_nominal_boundary_ns=(offset-index*30000000)*1000)
        output.append(frame)
    return {'reference': 'same kmsg timestamp domain, PM-credit announcement',
            'resolution_ns': 1000, 'wire_timestamp': False,
            'firmware_timer_phase_proven': False,
            'pm_credit_monotonic_ns': clocks[0][1] if len(clocks) == 1 else None,
            'submissions': output}
