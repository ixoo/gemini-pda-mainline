#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic release-verdict failures; no firmware or device enforcement proof."""
import ast
import copy
from pathlib import Path
import runpy

here = Path(__file__).resolve().parent
# Reuse the frozen existing full-window grammar fixture, not another replica.
tree = ast.parse((here / 'gtk3-verdict-test.py').read_text())
values = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and isinstance(node.value, (ast.Constant, ast.Dict)):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in {'boot', 'receipt', 'protocol', 'log'}:
                # receipt/protocol refer to boot; preserve that single dependency.
                exec(compile(ast.Module(body=[node], type_ignores=[]), 'frozen-fixture', 'exec'), values)
C = runpy.run_path(str(here.parent / 'classify-ccmp-channel-release.py'))
probe = lambda n: (f'periodic_ping ordinal={n} scheduled_offset_ns={n * 10**10} attempted=1 '
                  f'start_offset_ns={n * 10**10 + 100000000} completion_offset_ns={n * 10**10 + 200000000} '
                  'exit=0 statistics_known=1 transmitted=1 replies=1 rtt_known=1 '
                  'rtt_ms=40.0 clock_resolution_ns=10000000\n').encode()
pings = b''.join(probe(n) for n in range(1, 6))
probes = C['periodic_probes'](pings)
assert len(probes) == 5
protocol = dict(values['protocol'], periodic_probes=probes)
extra = b'''one-shot WLAN join grant: channel=40 interval_ms=9000
one-shot WLAN PM credit clock: ns=1000000000
one-shot WLAN connected channel release: credited=0 sequence=30 status=0 observed_ns=7400000000 pm_offset_ns=6400000000 debt=1
one-shot WLAN connected channel release: credited=1 sequence=30 observed_ns=7420000000 pm_offset_ns=6420000000 debt=0
'''
extra += b''.join((f'one-shot WLAN TX completion timing: pid={n + 40} status=0 class=1 '
                   f'observed_ns={n * 10**10 + 1100000000} pm_offset_ns={n * 10**10 + 100000000}\n').encode()
                  for n in range(1, 6))
log = values['log'] + extra
call = lambda raw, p=protocol: C['classify'](raw, values['receipt'], values['boot'], p)
assert call(log)['connected_data_after_release_pass']
for raw in [values['log'], log + extra, log.replace(b'interval_ms=9000', b'interval_ms=65000'),
            log.replace(b'sequence=30 status=0', b'sequence=254 status=0'),
            log.replace(b'credited=1 sequence=30', b'credited=1 sequence=31'),
            log.replace(b'credited=0 sequence=30 status=0', b'credited=0 sequence=30 status=-110'),
            log.replace(b'pm_offset_ns=6420000000', b'pm_offset_ns=6420000001'),
            log.replace(b'credited=1 sequence=30 observed_ns=7420000000 pm_offset_ns=6420000000',
                        b'credited=1 sequence=30 observed_ns=7520000001 pm_offset_ns=6520000001'),
            log + b'one-shot WLAN TX completion timing: malformed\n',
            log + extra.splitlines()[-1] + b'\n',
            log.replace(b'class=1', b'class=3'), log.replace(b'elapsed_ms=60005', b'elapsed_ms=59999')]:
    assert not call(raw)['connected_data_after_release_pass'], raw
for raw in [pings + probe(1), pings.replace(b'replies=1', b'replies=0'), pings[:-1] + b'bad',
            pings.replace(b'ordinal=3', b'ordinal=2'), pings + b'periodic_refused reason=fixture\n']:
    assert not C['periodic_probes'](raw)
bad = copy.deepcopy(protocol); bad['periodic_probes'] = []
assert not call(log, bad)['connected_data_after_release_pass']
assert not C['classify'](b'', None, None)['connected_data_after_release_pass']
print('channel release host verdict: PASS release credit/clock/grant/traffic and malformed/missing refusal; synthetic only')
