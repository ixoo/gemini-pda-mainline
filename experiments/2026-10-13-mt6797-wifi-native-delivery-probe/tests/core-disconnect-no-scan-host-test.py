#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the completed no-scan host ownership/refusal fixture for S1."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
body = (HERE / 'ccmp2-no-scan-host-test.py').read_text().replace(
    'ccmp2', 'ccmp-core-disconnect').replace('CCMP2', 'S1')
for prefix in ['session-', 'capture-', 'runtime-']:
    body = body.replace(prefix + 'ccmp-core-disconnect', prefix + 'ccmp-gtk8-s1')
body = body.replace('root = Path(temporary)', 'root = Path(temporary).resolve()').replace(
    'root = Path(tmp);', 'root = Path(tmp).resolve();').replace('join-ccmp.sh', 'join-ccmp-gtk7.sh')
exec(compile(body, 's1-completed-host-fixture', 'exec'), {'__file__': __file__})
