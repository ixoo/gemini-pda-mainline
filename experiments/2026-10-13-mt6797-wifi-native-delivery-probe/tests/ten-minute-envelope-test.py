#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixed host derivations and actual logger decoder boundaries; no device I/O."""
from pathlib import Path
import hashlib
import runpy
import tempfile

HERE = Path(__file__).resolve().parent.parent
m = runpy.run_path(str(HERE / 'ten-minute-envelope.py'))
source = (HERE / 'laptop-wifi-ssh-connected.py').read_text()
new = m['helper'](source)
assert "SESSION = 'session-ccmp-p2'" in new
assert 'target=$((start+i*1000000000))' in new and 'while [ "$i" -le 601 ]' in new
assert 'clock_resolution_ns=10000000' not in new
assert "'clock_resolution_ns': 10000000" in new
assert 'span >= 600_000_000_000' in new
assert "'604000000000'" in new and '608000000000' in new
assert 'timeout 610' in new and "'min(625.0, remaining)'" in new
assert "'timeout': 15" in new and 'timeout 3 /bin/wpa_cli' in new
assert '65536' in new and '400000000' in new
# Conservative maximum line lengths, plus room for the existing served/header.
ticks = ''.join('P2_STREAM ordinal=%d boot=%s pm_offset_ns=%d\r\n' %
                (i, '0'*36, 5*10**9+i*10**9) for i in range(602)).encode()
assert len(ticks)+2048 < 65536
verdict = m['classifier']((HERE / 'classify-ccmp-connected.py').read_text())
assert '604000000000<=before' in verdict and '<=608000000000' in verdict
assert 'len(probes)==59' in verdict and 'ten_minute_ssh_proven=bool(duration' in verdict
for name, text in [('helper', source), ('classifier', (HERE/'classify-ccmp-connected.py').read_text())]:
    try:
        m[name](text+'\n')
    except ValueError:
        pass
    else:
        raise AssertionError('changed origin accepted')
steps_path = HERE.parents[1] / 'experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/session_steps.py'
steps = runpy.run_path(str(steps_path))
log = b'6,0,1,-;fixture\n'
def status(deadline, elapsed):
    return (f'logger_exit=0\nschema=gemini-kmsg-v1\nsealed=yes\nresult=pass\n'
            f'reason=sealed-on-sigterm\nfirst_seq=0\nlast_seq=0\nrecords=1\n'
            f'bytes={len(log)}\nelapsed_ms={elapsed}\nbyte_limit=2097152\n'
            f'deadline_ms={deadline}\n').encode()
steps['classify_log'](log,status(600000,1))
try:
    steps['classify_log'](log,status(900000,1))
except ValueError:
    pass
else:
    raise AssertionError('old contract accepted new deadline')
m['log_contract'](steps, steps_path)
assert steps['classify_log'].p2_logger_deadline_ms == 900000
m['log_contract'](steps, steps_path)  # explicit same binding is idempotent
steps['classify_log'](log,status(900000,899999))
for raw in [status(900000,900000),status(900000,900001),status(600000,1),
            status(900000,1).replace(b'sealed=yes',b'sealed=no')]:
    try:
        steps['classify_log'](log,raw)
    except ValueError:
        pass
    else:
        raise AssertionError('changed deadline/boundary/seal accepted')
with tempfile.TemporaryDirectory() as td:
    path=Path(td)/'session_steps.py';path.write_bytes(steps_path.read_bytes()+b'\n')
    try:
        m['log_contract'](steps,path)
    except ValueError:
        pass
    else:
        raise AssertionError('modified decoder origin accepted')
print('P2 fixed 601-second/602-chunk host envelope, 64 KiB fit and exact 900-second log contract boundaries PASS')

for stamp, expected in [(0,0),(14999999,14999999000),(15000000,-15000000000),
                        (29800000,-200000000),(30000000,0),(60200000,200000000)]:
    raw=(b'6,0,1000000,-;one-shot WLAN PM credit clock: ns=900000000\n'+
         ('6,1,%d,-;one-shot WLAN join TX: subtype=12 pid=127 pages=1\n' % (1000000+stamp)).encode())
    d=m['reserved_submission_offsets'](raw)
    assert d['submissions'][0]['signed_offset_from_nearest_nominal_boundary_ns']==expected
unknown=m['reserved_submission_offsets'](b'6,0,10,-;one-shot WLAN join TX: subtype=12 pid=127 pages=1\n')
assert not unknown['submissions'][0]['offset_known']
print('Existing reserved-submission records: nearest nominal 30-second boundary, signed/tie/missing-clock cases PASS')
