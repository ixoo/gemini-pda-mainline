#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""S1 planned stop is separate from a 60 s pass; synthetic host parsing only."""
import copy
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
F = runpy.run_path(str(HERE / 'channel-release-verdict-test.py'))
C = runpy.run_path(str(HERE.parent / 'classify-ccmp-core-disconnect.py'))['classify']
boot, receipt, protocol = F['values']['boot'], copy.deepcopy(F['values']['receipt']), F['protocol']
receipt.update(all_pass=True, s1_stream={'pass': True}, s1_remote_stream_quiescence={'quiesced': True}, s1_core_disconnect={
    'attempted': True, 'accepted': True, 'before_pm_offset_ns': 55100000000,
    'after_pm_offset_ns': 56200000000})
log = F['log'].replace(b'reason=budget elapsed_ms=60005', b'reason=disconnect elapsed_ms=55050')
beacon = b'one-shot WLAN data-end beacons: observed_ns=56200000000 count=21 known=1 age_ns=53000000000 since_pm_known=1 since_pm=20 interval_tu=100\n'
log += beacon
result = C(log, receipt, boot, protocol)
assert result['core_disconnect_trial_pass'] and result['finite_capability_pass']
assert not result['duration_pass'] and not result['low_traffic_60s_pass']
assert not result['full_60s_budget_pass_claimed']
for sample in [log.replace(b'reason=disconnect', b'reason=budget'),
               log.replace(b'observed_ns=56200000000 count', b'observed_ns=55200000000 count'),
               log + beacon, log.replace(beacon, b''),
               log + b'one-shot WLAN data-end beacons: malformed\n',
               log.replace(b'budget_ms=60000', b'budget_ms=55000'),
               log.replace(b'elapsed_ms=55050 rx_unicast=0', b'elapsed_ms=55050 malformed=0')]:
    assert not C(sample, receipt, boot, protocol)['core_disconnect_trial_pass']
for field in ['s1_stream', 's1_core_disconnect', 's1_remote_stream_quiescence']:
    bad = copy.deepcopy(receipt)
    bad[field] = {}
    assert not C(log, bad, boot, protocol)['core_disconnect_trial_pass']
bad = copy.deepcopy(receipt); bad['s1_core_disconnect']['before_pm_offset_ns'] = 55400000000
assert not C(log, bad, boot, protocol)['core_disconnect_trial_pass']
assert not C(b'', None, None)['core_disconnect_trial_pass']
print('S1 verdict: PASS controlled-stop attribution, strict records, stream/control refusals and no 60 s claim; synthetic only')
