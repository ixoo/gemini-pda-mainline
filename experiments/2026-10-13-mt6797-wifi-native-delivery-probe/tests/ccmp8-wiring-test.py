#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply actual receipt/refusal/installer/namespace fixture to REAL CCMP8 bindings."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
fixture = (HERE / 'ccmp2-wiring-test.py').read_text()
fixture = fixture.replace('ccmp2', 'ccmp8').replace('CCMP2', 'CCMP8').replace(
    'ccmp-stable-monitor-candidate-2', 'ccmp-stable-monitor-candidate-8').replace(
    'mt6797-wifi-ccmp-stable-monitor-deployment-2',
    'mt6797-wifi-ccmp-stable-monitor-deployment-8').replace(
    'ba8078a0be1673a81a8159b5166769aeb226785eb0ee29ba682c3db3e50dc93d',
    '2f67ae1087fc3b967af527718f7edbc1cdd83e76e111679f3e4ea5a5fcaea98c').replace(
    '41881cb1345a9b1e3d39930c646a63d21499d5d7222039b8abfa7a9bf3b0be8e',
    '5b4405e0060111173da65445e3e4b1ffcd13347c9cf0ddb23d36d85140665ee6')
# Production resolves the runtime root; /tmp aliases /private/tmp on macOS.
fixture = fixture.replace('root = Path(temporary)', 'root = Path(temporary).resolve()').replace(
    'root = Path(tmp);', 'root = Path(tmp).resolve();')
exec(compile(fixture, str(HERE / 'ccmp2-wiring-test.py'), 'exec'),
     {'__file__': __file__, '__name__': '__main__'})
