#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run the actual P1D custody/client fixture against P2's fixed host envelope."""
from pathlib import Path
import hashlib
import runpy

HERE = Path(__file__).resolve().parent
source = (HERE / 'connected-client-test.py').read_text()
if hashlib.sha256(source.encode()).hexdigest() != '66a11817c9965b7acb3e84fcf9cc7f6ed109b78a2467e03f5f9cd612d81e6a25':
    raise ValueError('reviewed client fixture changed')
m = runpy.run_path(str(HERE.parent / 'ten-minute-envelope.py'))
source = m['literal'](source, "'laptop-wifi-ssh-connected.py'", "'laptop-wifi-ssh-connected-p2.py'", 1)
for old, new, count in [('P1','P2',13),('p1','p2',34),(' clock_resolution_ns=10000000','',2)]:
    source = m['literal'](source, old, new, count)
for old, new, count in [('243','602',2),('500000000','1000000000',2),
                        ('125','610',3),('135','625',2),('210','710',8),
                        ('121','601',1),('122.1','602.1',1),('127.1','607.1',1),
                        ('137000000000','610000000000',1),('124000000000','606000000000',2),
                        ('123200000000','607200000000',1),('123500000000','607500000000',1),
                        ('4500000000','5000000000',1)]:
    source = m['number'](source, old, new, count)
exec(compile(source, __file__, 'exec'), globals())
