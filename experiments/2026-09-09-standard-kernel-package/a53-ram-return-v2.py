#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Versioned return watcher for the observed pre-authentication host-down case."""
import hashlib
from pathlib import Path
import runpy

ORIGINAL = Path(__file__).resolve().with_name('a53-ram-return.py')
ORIGINAL_SHA256 = '0f6f20c324dc7bb4911c34a8e793b09a0af819ed46474ee996b723930bf5d081'
if ORIGINAL.is_symlink() or hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() != ORIGINAL_SHA256:
    raise ValueError('original Gemian return helper changed')

original = runpy.run_path(str(ORIGINAL))
original['CONNECT_FAILURES'].update(
    ('ssh: connect to host GEMIAN_HOST port 22: Host is down' + ending).encode()
    for ending in ('\n', '\r\n')
)

# The original watch and classify functions share this exact mutable set.
# Their identity, finite budget, host trust and other refusal rules are intact.
CONNECT_FAILURES = original['CONNECT_FAILURES']
PROBE = original['PROBE']
TRUST_SHA = original['TRUST_SHA']
classify = original['classify']
watch = original['watch']
