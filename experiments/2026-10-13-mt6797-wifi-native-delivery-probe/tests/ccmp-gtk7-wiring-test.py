#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply actual receipt/refusal/installer/namespace fixture to REAL GTK7 bindings."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
fixture = (HERE / 'ccmp2-wiring-test.py').read_text()
fixture = fixture.replace('ccmp2', 'ccmp-gtk7').replace('CCMP2', 'GTK7').replace(
    'ccmp-stable-monitor-candidate-2', 'ccmp-stable-monitor-candidate-gtk7').replace(
    'mt6797-wifi-ccmp-stable-monitor-deployment-2',
    'mt6797-wifi-ccmp-stable-monitor-deployment-gtk7').replace(
    'ba8078a0be1673a81a8159b5166769aeb226785eb0ee29ba682c3db3e50dc93d',
    'e7e4821e7d1f68529806d0dae872d2f1eba07a3690fd4eabb9c6b9ac5f5d68c7').replace(
    '41881cb1345a9b1e3d39930c646a63d21499d5d7222039b8abfa7a9bf3b0be8e',
    '75316795e8a9a732db5f02e5df32393b7f955c402422b72832fb9d5855f5ee09')
fixture = fixture.replace('laptop-wifi-ssh-ccmp.py', 'laptop-wifi-ssh-retain.py')
# Production resolves the runtime root; /tmp aliases /private/tmp on macOS.
fixture = fixture.replace('root = Path(temporary)', 'root = Path(temporary).resolve()').replace(
    'root = Path(tmp);', 'root = Path(tmp).resolve();')
fixture = fixture.replace(
    "    assert standalone.ROOT == runtime",
    "    assert standalone.CCMP_CLASSIFIER == PROBE / 'classify-ccmp-gtk-budget.py'\n    assert standalone.ROOT == runtime").replace(
    "    ph = host.PH",
    "    assert host.CCMP_CLASSIFIER == PROBE / 'classify-ccmp-gtk-budget.py'\n    ph = host.PH")
fixture = fixture.replace('join-ccmp.sh', 'join-ccmp-gtk7.sh')
exec(compile(fixture, str(HERE / 'ccmp2-wiring-test.py'), 'exec'),
     {'__file__': __file__, '__name__': '__main__'})
