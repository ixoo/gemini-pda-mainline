#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""P2 fixed ten-minute derivation of the source-pinned P1D classifier."""
from pathlib import Path
import hashlib
import runpy

HERE = Path(__file__).resolve().parent
contract = HERE / 'ten-minute-envelope.py'
if hashlib.sha256(contract.read_bytes()).hexdigest() != 'dbafdb83b95edf261a99fe118cabe1cbdf799d9e4a949cdcd1f809691d27da62':
    raise ValueError('P2 host/log contract changed')
P2 = runpy.run_path(str(contract))
source = P2['classifier']((HERE / 'classify-ccmp-connected.py').read_text())
exec(compile(source, __file__, 'exec'), globals())

ORIGINAL_CLASSIFY = classify

def classify(kmsg, ssh_receipt, verified_boot, protocol=None):
    result = ORIGINAL_CLASSIFY(kmsg, ssh_receipt, verified_boot, protocol)
    result['reserved_submission_offsets'] = P2['reserved_submission_offsets'](kmsg)
    return result
