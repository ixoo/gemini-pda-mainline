#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply actual receipt/refusal/installer/namespace fixture to REAL CCMP5 bindings."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
fixture = (HERE / 'ccmp2-wiring-test.py').read_text()
fixture = fixture.replace('ccmp2', 'ccmp5').replace('CCMP2', 'CCMP5').replace(
    'ccmp-stable-monitor-candidate-2', 'ccmp-stable-monitor-candidate-5').replace(
    'mt6797-wifi-ccmp-stable-monitor-deployment-2',
    'mt6797-wifi-ccmp-stable-monitor-deployment-5').replace(
    'ba8078a0be1673a81a8159b5166769aeb226785eb0ee29ba682c3db3e50dc93d',
    '1b1d668c15754b75e36fac6d24d4a31a3bc21eda042ead307a198c560e58597d').replace(
    '41881cb1345a9b1e3d39930c646a63d21499d5d7222039b8abfa7a9bf3b0be8e',
    'ee5dd8ad261496a387cf755b755982e0280f13a259e49619eb2de26e4a8dfc16')
exec(compile(fixture, str(HERE / 'ccmp2-wiring-test.py'), 'exec'),
     {'__file__': __file__, '__name__': '__main__'})
