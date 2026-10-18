#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply actual receipt/refusal/installer/namespace fixture to REAL GTK4 bindings."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
fixture = (HERE / 'ccmp2-wiring-test.py').read_text()
fixture = fixture.replace('ccmp2', 'ccmp-gtk4').replace('CCMP2', 'GTK4').replace(
    'ccmp-stable-monitor-candidate-2', 'ccmp-stable-monitor-candidate-gtk4').replace(
    'mt6797-wifi-ccmp-stable-monitor-deployment-2',
    'mt6797-wifi-ccmp-stable-monitor-deployment-gtk4').replace(
    'ba8078a0be1673a81a8159b5166769aeb226785eb0ee29ba682c3db3e50dc93d',
    '74fb9d94e4202e2030e3659ca717487af0de17fb659493f595567ff4fe7aad89').replace(
    '41881cb1345a9b1e3d39930c646a63d21499d5d7222039b8abfa7a9bf3b0be8e',
    'e2571776fe674cf1288f8a12f4362c7fba1d083cf93846edfb1a3850ed27eb09')
fixture = fixture.replace('laptop-wifi-ssh-ccmp.py', 'laptop-wifi-ssh-retain.py')
# Production resolves the runtime root; /tmp aliases /private/tmp on macOS.
fixture = fixture.replace('root = Path(temporary)', 'root = Path(temporary).resolve()').replace(
    'root = Path(tmp);', 'root = Path(tmp).resolve();')
fixture = fixture.replace(
    "    assert standalone.ROOT == runtime",
    "    assert standalone.CCMP_CLASSIFIER == PROBE / 'classify-ccmp-gtk-budget.py'\n    assert standalone.ROOT == runtime").replace(
    "    ph = host.PH",
    "    assert host.CCMP_CLASSIFIER == PROBE / 'classify-ccmp-gtk-budget.py'\n    ph = host.PH")
exec(compile(fixture, str(HERE / 'ccmp2-wiring-test.py'), 'exec'),
     {'__file__': __file__, '__name__': '__main__'})
