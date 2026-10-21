#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P2E: host-only evidence successor; unchanged P2 kernel and device envelope."""
from pathlib import Path
import hashlib
import runpy

HERE = Path(__file__).resolve().parent
ADAPTER = HERE / 'p2-evidence-successor.py'
if hashlib.sha256(ADAPTER.read_bytes()).hexdigest() != 'ef37f9b90b9d2e8f7db2ab6cbd34ac9663bc120b2b472fd71eb5322cc8a29265':
    raise ValueError('P2E evidence adapter changed')
P2E = runpy.run_path(str(ADAPTER))
source = P2E['host']((HERE / 'passive-host-ccmp-p2.py').read_text(), 'ebd787c573c9434fc1848487bee30d24df1b5702b4847aae26a9a9e44e4f7a8e')
exec(compile(source, __file__, 'exec'), globals())
