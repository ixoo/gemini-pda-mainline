#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Apply the P1D ownership/refusal fixture to P2's stated time envelope."""
from pathlib import Path
import hashlib
import runpy

HERE = Path(__file__).resolve().parent
source = (HERE/'connected-verdict-test.py').read_text()
if hashlib.sha256(source.encode()).hexdigest() != '382caf95503d52c45c5cc8c1bca27f2b17457b238744656a369a43e1bace8f42':
    raise ValueError('reviewed verdict fixture changed')
m=runpy.run_path(str(HERE.parent/'ten-minute-envelope.py'))
source=m['literal'](source,"'classify-ccmp-connected.py'","'classify-ccmp-connected-p2.py'",1)
source=m['literal'](source,'P1','P2',1)
source=m['literal'](source,'p1','p2',6)
for old,new,count in [('12','60',2),('11','59',1),('120000','600000',2),
                      ('121000','601000',1),('121000000000','601000000000',1),
                      ('123000000000','603000000000',1),('134000000000','606000000000',1),
                      ('134500000000','606500000000',1),('135100000000','607100000000',1),
                      ('125000000000','597000000000',1),('135200000000','607200000000',1),
                      ('134200000000','606200000000',1),('133900','605900',1),
                      ('119999999999','599999999999',1),('120999999999','600999999999',1)]:
    source=m['number'](source,old,new,count)
source=m['literal'](source,'    if n>=3:\n','    if n>=3:\n        moment=n if n<5 else n*4+80\n',1)
source=m['literal'](source,'{n*10**9+10**9}','{moment*10**9+10**9}',1)
source=m['literal'](source,'{n*10**9}','{moment*10**9}',1)
source=source.replace('120s receive','600s receive')
exec(compile(source,__file__,'exec'),globals())
assert a['ten_minute_ssh_proven'] and not a['maintained_wifi_support'] and not a['same_boot_reconnect_proven']
print('P2 single-lifetime duration claim remains separate from maintained support/reconnect; synthetic only PASS')
