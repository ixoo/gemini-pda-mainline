#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply actual receipt/refusal/installer/namespace fixture to REAL CCMP4 bindings."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
fixture = (HERE / 'ccmp2-wiring-test.py').read_text()
fixture = fixture.replace('ccmp2', 'ccmp4').replace('CCMP2', 'CCMP4').replace(
    'ccmp-stable-monitor-candidate-2', 'ccmp-stable-monitor-candidate-4').replace(
    'mt6797-wifi-ccmp-stable-monitor-deployment-2',
    'mt6797-wifi-ccmp-stable-monitor-deployment-4').replace(
    'ba8078a0be1673a81a8159b5166769aeb226785eb0ee29ba682c3db3e50dc93d',
    '1e8efbeaf49ac08f6fea3d76d3e4949d8473b2d1586c964a67a0b4677449598c').replace(
    '41881cb1345a9b1e3d39930c646a63d21499d5d7222039b8abfa7a9bf3b0be8e',
    '4e3c8ef7cc3f6470ef76f3337e038160ba29ba996b32d4d0534f597c30f175e5')
exec(compile(fixture, str(HERE / 'ccmp2-wiring-test.py'), 'exec'),
     {'__file__': __file__, '__name__': '__main__'})
