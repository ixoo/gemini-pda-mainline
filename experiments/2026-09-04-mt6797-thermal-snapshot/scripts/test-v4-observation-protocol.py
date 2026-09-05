#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Prove corrected-image refusals stop before the next consuming request."""
from pathlib import Path
import runpy
from v4_observation_protocol import Protocol, RELEASE, CLOSED_BOOTS, OLD_IDENTITIES

fixture = runpy.run_path(str(Path(__file__).with_name('test-observation-protocol.py')))
candidate, record = '3' * 64, '4' * 64
protocol = Protocol(candidate, record)
pre = fixture['pre'].replace('7.1.3-gemini-thermal-snapshot', RELEASE).replace(fixture['RECORD'], record)
deployment = fixture['deployment'].replace(fixture['CANDIDATE'], candidate)
deployment = deployment.rstrip('\n') + '\nboot2_device_guard=passed\nboot2_device_guard_sha256=0f0fc88ce4650590c6cb86f0ef5ce22b95b2a0f41c9b39b397e24e39cf9f0ebf\ntarget_major_minor=179:30\nroot_major_minor=179:29\n'
boot = fixture['boot']
post = pre.replace('abi=1 attempts=0 limit=3', 'abi=1 attempts=3 limit=3')

cases = {
    'pass': (None, 3),
    'old-release': (('pre', RELEASE, '7.1.3-gemini-thermal-snapshot'), 0),
    'old-record': (('pre', record, fixture['RECORD']), 0),
    'initial-precision': (('pre', 'millicelsius=35000', 'millicelsius=35001'), 0),
    'initial-hot': (('pre', 'millicelsius=35000', 'millicelsius=58600'), 0),
    'used-lifecycle': (('pre', 'cpu_requests=0', 'cpu_requests=1'), 0),
    'used-frequency': (('pre', 'frequency_log_count=0', 'frequency_log_count=1'), 0),
    'used-snapshot': (('pre', 'attempts=0', 'attempts=1'), 0),
    'missing-state': (('pre', 'cpu_online=0-7\n', ''), 0),
    'writeable-sysfs': (('pre', 'sysfs_options=ro,', 'sysfs_options=rw,'), 0),
    'first-precision': (('read1', 'temperature=35000', 'temperature=35001'), 1),
    'first-accounting': (('read1', 'observer_status=abi=1 attempts=1', 'observer_status=abi=1 attempts=2'), 1),
    'second-order': (('read2', 'start_ns=20 end_ns=21', 'start_ns=10 end_ns=11'), 2),
    'second-invalid': (('read2', 'valid_mask=127', 'valid_mask=126'), 2),
    'third-winner': (('read3', 'winner=6', 'winner=0'), 3),
    'post-boot': (('post', boot, fixture['deploy']), 3),
    'post-precision': (('post', 'millicelsius=35000', 'millicelsius=35001'), 3),
    'post-count': (('post', 'attempts=3', 'attempts=2'), 3),
    'post-late-change': (('post', '[ 1.0]', '[ 2.0]'), 3),
}
for old in CLOSED_BOOTS:
    cases['consumed-' + old] = (('pre', boot, old), 0)
for boundary in ('first-timeout', 'request-interrupted', 'pause-interrupted', 'second-hot', 'third-spread'):
    cases[boundary] = (None, {'first-timeout':1, 'request-interrupted':1, 'pause-interrupted':1,
                             'second-hot':2, 'third-spread':3}[boundary])

for name, (mutation, expected_requests) in cases.items():
    calls, requests, pauses, saved = [], [], [], {}
    def request(attempt):
        requests.append(attempt)
        if name == 'request-interrupted':
            raise KeyboardInterrupt('injected after durable request')
    def pause(seconds):
        pauses.append(seconds)
        if name == 'pause-interrupted':
            raise KeyboardInterrupt('injected during spacing')
    def transport(kind, current_boot, attempt):
        calls.append(kind)
        if kind == 'state':
            label = 'pre' if len(calls) == 1 else 'post'
            raw = pre if label == 'pre' else post
        else:
            assert requests == list(range(1, attempt + 1))
            assert current_boot == boot
            if name == 'first-timeout':
                raise TimeoutError('injected read timeout')
            label = 'read' + str(attempt)
            base = 59000 if name == 'second-hot' and attempt == 2 else 42000 if name == 'third-spread' and attempt == 3 else 35000
            raw = fixture['read_frame'](attempt, base)
        if mutation and label == mutation[0]:
            assert mutation[1] in raw
            raw = raw.replace(mutation[1], mutation[2])
        return raw
    try:
        result = protocol.run(transport, lambda n,r: saved.setdefault(n,r), request, pause, deployment)
    except (ValueError, TimeoutError, KeyboardInterrupt):
        assert name != 'pass', name
    else:
        assert name == 'pass' and result['snapshot_requests'] == 3
        assert result['integrated_thermal_repeatability'] == 'not-established'
        assert calls == ['state', 'read', 'read', 'read', 'state']
    assert requests == list(range(1, expected_requests + 1)), name
    assert len(calls) <= 5 and all(n == 1 for n in pauses), name
    if name == 'request-interrupted': assert calls == ['state']

for bad in OLD_IDENTITIES | {'0'*64, 'x'*64, '1'*63}:
    for pair in ((bad, record), (candidate, bad)):
        try: Protocol(*pair)
        except ValueError: pass
        else: raise AssertionError('identity accepted')
try: Protocol(candidate, candidate)
except ValueError: pass
else: raise AssertionError('image/record alias')
# Adapting the new release must not mutate the frozen predecessor module.
import observation_state
assert observation_state.FIXED['kernel_release'] == '7.1.3-gemini-thermal-snapshot'
print(f'v4_protocol_scenarios={len(cases)} identity_refusals=13 predecessor_unchanged=pass device_access=none')
