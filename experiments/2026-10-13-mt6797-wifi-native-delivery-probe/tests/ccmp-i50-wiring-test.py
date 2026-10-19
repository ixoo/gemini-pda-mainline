#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply actual receipt/refusal/installer/namespace fixture to REAL I50 bindings."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
fixture = (HERE / 'ccmp2-wiring-test.py').read_text()
fixture = fixture.replace('ccmp2', 'ccmp-i50').replace('CCMP2', 'I50').replace(
    'ccmp-stable-monitor-candidate-2', 'ccmp-stable-monitor-candidate-i50').replace(
    'mt6797-wifi-ccmp-stable-monitor-deployment-2',
    'mt6797-wifi-ccmp-stable-monitor-deployment-i50').replace(
    'ba8078a0be1673a81a8159b5166769aeb226785eb0ee29ba682c3db3e50dc93d',
    '544ba48aa0b2a773d8400ce1db68bf190ff90fc6529fcb4254daef4de232fb87').replace(
    '41881cb1345a9b1e3d39930c646a63d21499d5d7222039b8abfa7a9bf3b0be8e',
    'ffbb0d343aa7061e1c592488ee6ee92786cc70abe7a6f9008ca1f4a17cce2dff')
fixture = fixture.replace('laptop-wifi-ssh-ccmp.py', 'laptop-wifi-ssh-retain.py')
# Production resolves the runtime root; /tmp aliases /private/tmp on macOS.
fixture = fixture.replace('root = Path(temporary)', 'root = Path(temporary).resolve()').replace(
    'root = Path(tmp);', 'root = Path(tmp).resolve();')
fixture = fixture.replace(
    "    assert standalone.ROOT == runtime",
    "    assert standalone.CCMP_CLASSIFIER == PROBE / 'classify-ccmp-i50.py'\n    assert standalone.ROOT == runtime").replace(
    "    ph = host.PH",
    "    assert host.CCMP_CLASSIFIER == PROBE / 'classify-ccmp-i50.py'\n    ph = host.PH")
fixture = fixture.replace('join-ccmp.sh', 'join-ccmp-i50.sh')
exec(compile(fixture, str(HERE / 'ccmp2-wiring-test.py'), 'exec'),
     {'__file__': __file__, '__name__': '__main__'})
