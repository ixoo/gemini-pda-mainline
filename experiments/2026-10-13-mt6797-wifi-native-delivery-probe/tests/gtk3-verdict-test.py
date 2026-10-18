#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic host parser cases reuse the existing exact CCMP log grammar."""
import copy
from pathlib import Path
import runpy

root = Path(__file__).resolve().parent.parent
new = runpy.run_path(str(root / 'classify-ccmp-gtk-budget.py'))
old = runpy.run_path(str(root / 'classify-ccmp.py'))
assert old['RX_MAX'] == 512 and old['NATIVE_MAX'] == 64 and old['BYTES_MAX'] == 1024 * 1024
C = new['classify']
boot = 'c3c13385-7138-493e-b7df-6fe5673c6739'
receipt = {'boot_id': boot, 'cycles': [{'cycle': 1, 'ssh_exit': 0, 'boot_match': True,
    'ready_seen': True, 'ack_written': True, 'marker_after_active': True,
    'marker_mode': 'ccmp-stable-monitor', 'marker_boot': boot}]}
protocol = {'protocol_pass': True, 'verified_boot': boot}
log = b'''one-shot WLAN native-diag: state=1 act=1 total=0 native=0 bytes=0
one-shot WLAN native-diag: state=2 act=0 total=2 native=0 bytes=500
one-shot WLAN ccmp-stable RX: first ethernet_bytes=100 flags=0x40200512
one-shot WLAN checked GTK RX: first_queued=1 ethernet_bytes=60
one-shot WLAN join data phase: budget_ms=60000 teardown_margin_ms=5000 inside_grant=1
one-shot WLAN native-diag: state=3 act=2 total=1000 native=0 bytes=200000
one-shot WLAN join data phase end: reason=budget elapsed_ms=60005 rx_unicast=0 rx_group=0 rx_dropped=0 tx_queued=28 tx_done=28 tx_failed=0 tx_credits=59
one-shot WLAN native-diag: state=4 act=0 total=1000 native=0 bytes=200000
one-shot WLAN ccmp-stable end: queued=700 no_reuse=1
one-shot WLAN join cleanup: stage=3 credits=returned slots=retired deauth=1
one-shot WLAN checked GTK counters: withheld_arp=0 queued_ptk=400 queued_gtk=300 delivered_arp=1
'''
good = C(log, receipt, boot, protocol)
assert good['finite_capability_pass'] and good['duration_pass'] and good['low_traffic_60s_pass']
assert good['gtk_arp_handoff_observed'] and not good['sustained_ssh_proven']
assert not good['hardware_replay_proven'] and not good['key_deletion_proven']
assert C(log.replace(b'elapsed_ms=60005', b'elapsed_ms=60000'), receipt, boot, protocol)['duration_pass']
cases = [
    log.replace(b'elapsed_ms=60005', b'elapsed_ms=59999'),
    log.replace(b'elapsed_ms=60005', b'elapsed_ms=5925'),
    log.replace(b'budget_ms=60000', b'budget_ms=5925'),
    log.replace(b'inside_grant=1', b'outside_grant=1'),
    log.replace(b'queued_gtk=300', b'queued_gtk=301'),
    log.replace(b'delivered_arp=1', b'delivered_arp=301'),
    log.replace(b'withheld_arp=0', b'withheld_arp=4097'),
    log.replace(b'queued_gtk=300', b'queued_gtk=0'),
    log.replace(b'queued=700', b'queued=1025'),
    log.replace(b'total=1000', b'total=4097'),
    log.replace(b'bytes=200000', b'bytes=2097153'),
    log.replace(b'flags=0x40200512', b'flags=0x0'),
    log.replace(b'native=0', b'native=1'),
    log + b'one-shot WLAN join stopped: status=-71\n',
    log + log.splitlines()[-1] + b'\n',
    log.replace(log.splitlines()[-1], b''),
    log.replace(b'queued_ptk=400', b'queued_ptk=bad'),
    log.replace(log.splitlines()[3], b''),
    log + log.splitlines()[3] + b'\n',
    log + log.splitlines()[4] + b'\n',
    log + b'one-shot WLAN checked GTK RX: malformed\n',
    log + b'one-shot WLAN join data phase: malformed\n',
    log + b'one-shot WLAN join data phase end: malformed\n',
]
for reason in [b'native-diag', b'pidbudget', b'native-window', b'disconnect', b'key-disable', b'txfail']:
    cases.append(log.replace(b'reason=budget', b'reason=' + reason))
for sample in cases:
    assert not C(sample, receipt, boot, protocol)['low_traffic_60s_pass'], sample
at_cap = log.replace(b'queued=700', b'queued=1024').replace(b'queued_ptk=400', b'queued_ptk=724').replace(b'total=1000', b'total=2000')
assert C(at_cap, receipt, boot, protocol)['finite_capability_pass']
assert not C(at_cap, receipt, boot, protocol)['duration_pass']
assert not C(log.replace(b'total=1000', b'total=4096'), receipt, boot, protocol)['duration_pass']
assert not C(log.replace(b'bytes=200000', b'bytes=2094801'), receipt, boot, protocol)['duration_pass']
bad = copy.deepcopy(receipt); bad['cycles'][0]['ssh_exit'] = 255
r = C(log, bad, boot, protocol); assert r['duration_pass'] and not r['finite_capability_pass']
assert not C(log, receipt, boot, {'protocol_pass': False})['low_traffic_60s_pass']
r = C(log.replace(b'delivered_arp=1', b'delivered_arp=0'), receipt, boot, protocol)
assert r['low_traffic_60s_pass'] and not r['gtk_arp_handoff_observed']
assert not C(b'', None, None)['low_traffic_60s_pass']
print('GTK3 host verdict: PASS separate capability/duration, 60s boundary, counters, quota/drain, SSH/protocol and historical-scope refusals; synthetic only')
