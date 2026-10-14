#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply actual receipt/refusal/installer/namespace fixture to REAL CCMP3 bindings."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
fixture = (HERE / 'ccmp2-wiring-test.py').read_text()
fixture = fixture.replace('ccmp2', 'ccmp3').replace('CCMP2', 'CCMP3').replace(
    'ccmp-stable-monitor-candidate-2', 'ccmp-stable-monitor-candidate-3').replace(
    'mt6797-wifi-ccmp-stable-monitor-deployment-2',
    'mt6797-wifi-ccmp-stable-monitor-deployment-3').replace(
    'ba8078a0be1673a81a8159b5166769aeb226785eb0ee29ba682c3db3e50dc93d',
    '84722412ea250d86c0772b57e0d0fd39ccfd9335a555c42702037b6d6cae3919').replace(
    '41881cb1345a9b1e3d39930c646a63d21499d5d7222039b8abfa7a9bf3b0be8e',
    '7b2b881b74b958502cd9c148f10b23c58949ea221f75281c9d97721d8b3bd60e')
exec(compile(fixture, str(HERE / 'ccmp2-wiring-test.py'), 'exec'),
     {'__file__': __file__, '__name__': '__main__'})
