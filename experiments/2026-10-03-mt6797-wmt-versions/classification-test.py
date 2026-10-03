#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
import runpy
from pathlib import Path
classify = runpy.run_path(str(Path(__file__).with_name('classify-versions.py')))['classify']


def log_for(failure=None):
    status = 0 if failure is None else -71
    completed = 3 if failure is None else failure
    lines = [f'one-shot WMT versions: result={status} completed={completed} clocks-held=1']
    for ordinal in range(3 if failure is None else failure+1):
        command = bytearray.fromhex('8040140001081000020100010800008000000000ffff00000000')
        command[12] = (8,0,4)[ordinal]
        reply = bytearray.fromhex('8040100002080c000000000108000080790200000000')
        reply[12] = (8,0,4)[ordinal]
        reply[16:18] = (b'\x79\x02',b'\x00\x8a',b'\x00\x8a')[ordinal]
        ret = -71 if ordinal == failure else 0
        if ret: reply[16] ^= 1
        lines.append(f'WMT version {ordinal}: result={ret} tx=26 rx=22 services=6 terminal=1')
        for name,wire in [('TX',command),('RX',reply)]:
            for i in range(0,len(wire),16):
                lines.append(f'WMT version {ordinal} {name}: {i:08x}: '+wire[i:i+16].hex(' '))
    return '\n'.join(lines).encode()+b'\n'

valid = log_for()
assert classify(valid)['identity_accepted']
for ordinal in range(3):
    result = classify(log_for(ordinal))
    assert result['evidence_consistent'] and not result['identity_accepted']
lines=valid.splitlines()
for i in range(len(lines)):
    assert not classify(b'\n'.join(lines[:i]+lines[i+1:]))['identity_accepted']
    assert not classify(b'\n'.join(lines+[lines[i]]))['identity_accepted']
for old,new in [(b'completed=3',b'completed=2'),(b'clocks-held=1',b'clocks-held=0'),
                (b'terminal=1',b'terminal=0'),(b'services=6',b'services=65'),
                (b'rx=22',b'rx=21'),(b'result=0 completed',b'result=-71 completed')]:
    assert not classify(valid.replace(old,new,1))['identity_accepted']
for marker in [b'one-shot WLAN START',b'one-shot EMI copy',b'one-shot HIF probe',b'WMT negotiation TX:']:
    assert not classify(valid+marker+b'\n')['identity_accepted']
for i,line in enumerate(lines):
    if b' RX: ' not in line and b' TX: ' not in line: continue
    prefix,hexbytes=line.rsplit(b': ',1)
    wire=bytearray.fromhex(hexbytes.decode())
    for byte in range(len(wire)):
        mutation=bytearray(wire);mutation[byte]^=1
        changed=lines.copy();changed[i]=prefix+b': '+mutation.hex(' ').encode()
        assert not classify(b'\n'.join(changed))['identity_accepted']
print('version log classifier: exact tuple, first-error preservation, missing/duplicate/count/wire/continuation refusals pass')
