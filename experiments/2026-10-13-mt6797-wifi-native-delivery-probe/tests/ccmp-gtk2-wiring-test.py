#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply actual receipt/refusal/installer/namespace fixture to REAL GTK2 bindings."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
fixture = (HERE / 'ccmp2-wiring-test.py').read_text()
fixture = fixture.replace('ccmp2', 'ccmp-gtk2').replace('CCMP2', 'GTK2').replace(
    'ccmp-stable-monitor-candidate-2', 'ccmp-stable-monitor-candidate-gtk2').replace(
    'mt6797-wifi-ccmp-stable-monitor-deployment-2',
    'mt6797-wifi-ccmp-stable-monitor-deployment-gtk2').replace(
    'ba8078a0be1673a81a8159b5166769aeb226785eb0ee29ba682c3db3e50dc93d',
    'a557a7b7c5c53ddbff10948e9e79119d656016c65e4cf5ca7f3cea29de08ecac').replace(
    '41881cb1345a9b1e3d39930c646a63d21499d5d7222039b8abfa7a9bf3b0be8e',
    'c1af69befe43ac1e24cda8006952953af08246bfa40318728e3b298754f427ea')
fixture = fixture.replace('laptop-wifi-ssh-ccmp.py', 'laptop-wifi-ssh-retain.py')
# Production resolves the runtime root; /tmp aliases /private/tmp on macOS.
fixture = fixture.replace('root = Path(temporary)', 'root = Path(temporary).resolve()').replace(
    'root = Path(tmp);', 'root = Path(tmp).resolve();')
exec(compile(fixture, str(HERE / 'ccmp2-wiring-test.py'), 'exec'),
     {'__file__': __file__, '__name__': '__main__'})
