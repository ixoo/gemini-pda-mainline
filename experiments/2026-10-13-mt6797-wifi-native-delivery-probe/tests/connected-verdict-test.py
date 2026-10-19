#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P1 ownership/duration/standard-disconnect grammar; synthetic, not firmware proof."""
import copy
from pathlib import Path
import runpy

here=Path(__file__).resolve().parent
c=runpy.run_path(str(here.parent/'classify-ccmp-connected.py'))
boot='c3c13385-7138-493e-b7df-6fe5673c6739'
receipt={'boot_id':boot,'all_pass':True,'cycles':[{'cycle':1,'ssh_exit':0,'boot_match':True,
    'ready_seen':True,'ack_written':True,'marker_after_active':True,
    'marker_mode':'ccmp-stable-monitor','marker_boot':boot}],
    'p1_stream':{'pass':True,'required_stream_ms':120000,'scheduled_stream_ms':121000,
      'receive_continuity_pass':True,'host_receive_span_ns':121000000000,
      'host_receive_max_gap_ns':500000000,'host_elapsed_ns':123000000000},
    'p1_core_disconnect':{'accepted':True,'kind':'after_completed_stream',
      'before_pm_offset_ns':134000000000,'after_pm_offset_ns':134500000000},
    'p1_remote_stream_quiescence':{'quiesced':True},
    'driver_window_after_client':{'driver_data_window':'open'}}
probe=lambda n:(f'periodic_ping ordinal={n} scheduled_offset_ns={n*10**10} attempted=1 '
                f'start_offset_ns={n*10**10+100000000} completion_offset_ns={n*10**10+200000000} '
                'exit=0 statistics_known=1 transmitted=1 replies=1 rtt_known=1 '
                'rtt_ms=40.0 clock_resolution_ns=10000000\n').encode()
pings=b''.join(probe(i) for i in range(1,12))
probes=c['periodic_probes'](pings);assert len(probes)==11
protocol={'protocol_pass':True,'verified_boot':boot,'periodic_probes':probes}
lines=[b'one-shot WLAN join grant: channel=40 interval_ms=9000']
for n in range(1,131):
    if n==3:lines.append(b'one-shot WLAN PM credit clock: ns=1000000000')
    if n==5:
        lines.extend([b'one-shot WLAN connected data phase: teardown_margin_ms=5000 no_reuse=1',
          b'one-shot WLAN native-diag: state=1 act=1 total=0 native=0 bytes=0',
          b'one-shot WLAN native-diag: state=2 act=0 total=2 native=0 bytes=500',
          b'one-shot WLAN ccmp-stable RX: first ethernet_bytes=100 flags=0x40200512',
          b'one-shot WLAN checked GTK RX: first_queued=1 ethernet_bytes=60'])
    if n==7:lines.extend([
        b'one-shot WLAN connected channel release: credited=0 sequence=29 status=0 observed_ns=7400000000 pm_offset_ns=6400000000 debt=1',
        b'one-shot WLAN connected channel release: credited=1 sequence=29 observed_ns=7420000000 pm_offset_ns=6420000000 debt=0'])
    pid=(n-1)%126+1;wrap=n//126
    lines.extend([f'one-shot WLAN TX slot allocation: pid={pid} ordinal={n} reserved=0 wraps={wrap}'.encode(),
                  f'one-shot WLAN TX slot completion: pid={pid} ordinal={n} wraps={wrap}'.encode()])
    if n>=3:
        lines.append(f'one-shot WLAN TX completion timing: pid={pid} status=0 class={int(n>=5)} observed_ns={n*10**9+10**9} pm_offset_ns={n*10**9}'.encode())
lines.extend([
 b'one-shot WLAN TX slot summary: phase=window allocations=130 completions=130 pending=0 wraps=1 unowned=0',
 b'one-shot WLAN data-end beacons: observed_ns=135100000000 count=21 known=1 age_ns=125000000000 since_pm_known=1 since_pm=20 interval_tu=100',
 b'one-shot WLAN join data phase end: reason=disconnect elapsed_ms=133900 rx_unicast=0 rx_group=0 rx_dropped=0 tx_queued=126 tx_done=126 tx_failed=0 tx_credits=252',
 b'one-shot WLAN native-diag: state=3 act=2 total=1000 native=0 bytes=200000',
 b'one-shot WLAN native-diag: state=4 act=0 total=1000 native=0 bytes=200000',
 b'one-shot WLAN ccmp-stable end: queued=700 no_reuse=1',
 b'one-shot WLAN TX slot allocation: pid=127 ordinal=0 reserved=1 wraps=1',
 b'one-shot WLAN TX completion timing: pid=127 status=0 class=2 observed_ns=135200000000 pm_offset_ns=134200000000',
 b'one-shot WLAN TX slot summary: phase=cleanup allocations=130 completions=130 pending=0 wraps=1 unowned=0',
 b'one-shot WLAN join cleanup: stage=3 credits=returned slots=retired deauth=1',
 b'one-shot WLAN checked GTK counters: withheld_arp=0 queued_ptk=400 queued_gtk=300 delivered_arp=1'])
log=b'\n'.join(lines)+b'\n'
call=lambda raw=log,r=receipt,p=protocol:c['classify'](raw,r,boot,p)
a=call();assert a['connected_lifetime_trial_pass'] and a['duration_pass'] and a['pid_ownership']['completed_reuses']==4
for raw in [log.replace(b'ordinal=127 reserved=0',b'ordinal=126 reserved=0'),
            log.replace(b'pid=1 ordinal=127',b'pid=2 ordinal=127'),
            log.replace(b'pid=127 ordinal=0 reserved=1',b'pid=1 ordinal=0 reserved=1'),
            log.replace(b'completions=130 pending=0',b'completions=129 pending=1'),
            log.replace(b'wraps=1 unowned=0',b'wraps=0 unowned=0'),
            log.replace(b'phase=cleanup',b'phase=window'),
            log.replace(b'pid=127 status=0 class=2',b'pid=127 status=5 class=2').replace(b'deauth=1',b'deauth=0'),
            log.replace(b'reason=disconnect',b'reason=connection-loss'),
            log.replace(b'credited=1 sequence=29',b'credited=1 sequence=30'),
            log.replace(b'ns=1000000000',b'ns=1000000001',1),
            log.replace(b'no_reuse=1\none-shot WLAN native-diag',b'no_reuse=0\none-shot WLAN native-diag',1),
            log.replace(next(l for l in lines if l.startswith(b'one-shot WLAN data-end beacons:')),b''),
            log+b'one-shot WLAN TX slot completion: malformed\n',
            log+b'one-shot WLAN join data phase end: malformed\n',
            log.replace(b'pid=5 status=0 class=1',b'pid=5 status=255 class=1'),
            log.replace(b'pid=127 status=0 class=2',b'pid=127 status=5 class=2')]:
    assert not call(raw)['connected_lifetime_trial_pass']
for key,value in [('host_receive_span_ns',119999999999),('host_receive_max_gap_ns',3000000001),
                  ('host_elapsed_ns',120999999999),('scheduled_stream_ms',120000),('pass',False)]:
    r=copy.deepcopy(receipt);r['p1_stream'][key]=value;assert not call(r=r)['connected_lifetime_trial_pass']
for field in ['p1_core_disconnect','p1_remote_stream_quiescence','driver_window_after_client']:
    r=copy.deepcopy(receipt);r.pop(field);assert not call(r=r)['connected_lifetime_trial_pass']
unowned=log.replace(b'one-shot WLAN PM credit clock: ns=1000000000',
    b'one-shot WLAN PM credit clock: ns=1000000000\none-shot WLAN unowned TX completion: pid=0 wlan=0 status=0 count=1')
unowned=unowned.replace(b'wraps=1 unowned=0',b'wraps=1 unowned=1')
assert call(unowned)['connected_lifetime_trial_pass']
assert len(call(unowned)['pid_ownership']['unowned_first_events'])==1
for raw in [unowned.replace(b'count=1',b'count=2'),unowned.replace(b'wraps=1 unowned=1',b'wraps=1 unowned=0'),
            log+b'one-shot WLAN unowned TX completion: malformed\n']:
    assert not call(raw)['connected_lifetime_trial_pass']
assert not call(p=dict(protocol,periodic_probes=[]))['connected_lifetime_trial_pass']
assert not c['classify'](b'',None,None)['connected_lifetime_trial_pass']
for bad in [pings+probe(12),pings+probe(1),pings.replace(b'replies=1',b'replies=0')]:
    assert not c['periodic_probes'](bad)
print('connected verdict: completed reuse/credit-clock/120s receive/ordinary disconnect, duplicate/missing/malformed/refusal cases PASS; synthetic only')
