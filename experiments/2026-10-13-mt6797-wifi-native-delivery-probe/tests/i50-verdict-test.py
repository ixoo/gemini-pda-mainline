#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""I50 parser refusals and independent idle/cleanup verdicts; synthetic only."""
import ast
from pathlib import Path
import runpy

here = Path(__file__).resolve().parent
tree = ast.parse((here / 'gtk3-verdict-test.py').read_text())
v = {}
for n in tree.body:
    if isinstance(n, ast.Assign) and isinstance(n.value, (ast.Constant, ast.Dict)):
        if any(isinstance(t, ast.Name) and t.id in {'boot', 'receipt', 'protocol', 'log'} for t in n.targets):
            exec(compile(ast.Module(body=[n], type_ignores=[]), 'retained-fixture', 'exec'), v)
c = runpy.run_path(str(here.parent / 'classify-ccmp-i50.py'))
ping = lambda n: (f'periodic_ping ordinal={n} scheduled_offset_ns={n * 10**10} attempted=1 '
                  f'start_offset_ns={n * 10**10 + 100000000} completion_offset_ns={n * 10**10 + 200000000} '
                  'exit=0 statistics_known=1 transmitted=1 replies=1 rtt_known=1 '
                  'rtt_ms=40.0 clock_resolution_ns=10000000\n').encode()
pings = b''.join(ping(i) for i in range(1, 5))
probes = c['periodic_probes'](pings)
assert len(probes) == 4 and not c['periodic_probes'](pings + ping(5))
protocol = dict(v['protocol'], periodic_probes=probes)
log = v['log'].replace(b'budget_ms=60000', b'budget_ms=50000').replace(b'elapsed_ms=60005', b'elapsed_ms=50005')
extra = b'''one-shot WLAN join grant: channel=40 interval_ms=9000
one-shot WLAN PM credit clock: ns=1000000000
one-shot WLAN connected channel release: credited=0 sequence=30 status=0 observed_ns=7400000000 pm_offset_ns=6400000000 debt=1
one-shot WLAN connected channel release: credited=1 sequence=30 observed_ns=7420000000 pm_offset_ns=6420000000 debt=0
'''
extra += b''.join((f'one-shot WLAN TX completion timing: pid={n+40} status=0 class=1 '
                   f'observed_ns={n*10**10+1100000000} pm_offset_ns={n*10**10+100000000}\n').encode() for n in range(1, 5))
# Wrap the inherited semantic fixture in the real kmsg record grammar.
raw = b''.join(f'6,{i},{i*1000},-;'.encode() + line + b'\n' for i, line in enumerate((log+extra).splitlines()))
# Replace only the final data record's log clock, independent of its observed_ns.
lines = raw.splitlines();lines[-1] = lines[-1].replace(str((len(lines)-1)*1000).encode()+b',-;', b'41100000,-;', 1)
raw = b'\n'.join(lines) + b'\n' + f'6,{len(lines)},51100000,-;one-shot WLAN join TX: subtype=12 pid=45 pages=1\n'.encode()
call = lambda x, p=protocol: c['classify'](x, v['receipt'], v['boot'], p)
a = call(raw);assert a['duration_pass'] and a['idle_tail_comparison_measured'] and a['deauth_acked']
assert a['provisional_ccmp_compatibility_pass'] and not a['full_60s_budget_pass_claimed']
assert a['idle_tail']['completion_log_to_deauth_submission_us'] == 10000000
no_cleanup = raw.replace(b'one-shot WLAN join cleanup: stage=3 credits=returned slots=retired deauth=1', b'one-shot WLAN cleanup complete: bounded_page_debt=1 healthy_stage3=0 no_reuse=1')
a = call(no_cleanup);assert a['idle_tail_comparison_measured'] and not a['healthy_cleanup'] and not a['provisional_ccmp_compatibility_pass']
for sample in [raw.replace(b'elapsed_ms=50005', b'elapsed_ms=49999'),
               raw.replace(b'reason=budget', b'reason=disconnect'),
               raw.replace(b'pm_offset_ns=40100000000', b'pm_offset_ns=45100000000'),
               raw.replace(b',51100000,-;', b',49100000,-;'),
               raw + raw.splitlines()[-1] + b'\n',
               raw + b'6,99,52000000,-;one-shot WLAN TX completion timing: malformed\n',
               raw.replace(b'credited=1 sequence=30', b'credited=1 sequence=31'),
               raw.replace(b'budget_ms=50000', b'budget_ms=60000')]:
    assert not call(sample)['idle_tail_comparison_measured'], sample
assert not call(raw, dict(protocol, periodic_probes=[]))['idle_tail_comparison_measured']
for sample in [pings + ping(1), pings.replace(b'replies=1', b'replies=0'), pings + b'periodic_refused reason=fixture\n']:
    assert not c['periodic_probes'](sample)
assert not c['classify'](b'', None, None)['idle_tail_comparison_measured']
leaf = (here.parent / 'join-ccmp-i50.sh').read_text()
parent = (here.parent / 'join-ccmp-gtk7.sh').read_text()
assert leaf.replace('I50 retains four guarded periodic pings', 'GTK7 adds five guarded periodic pings').replace('four periodic pings <=3 s each', 'five periodic pings <=3 s each').replace('for pc_sec in 10 20 30 40; do', 'for pc_sec in 10 20 30 40 50; do') == parent
print('I50 verdict/leaf cases PASS: four probes, 50 s, actual idle, malformed/extra TX and cleanup independence; synthetic only')
