# SPDX-License-Identifier: MIT
"""Reuse the reviewed strict block-identity receipt for this candidate only."""
import hashlib
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
PARSER = REPO / 'experiments/2026-09-04-mt6797-thermal-snapshot/scripts/v4_deployment_receipt.py'


def receipt(raw, candidate):
    if PARSER.is_symlink() or hashlib.sha256(PARSER.read_bytes()).hexdigest() != '2ef4fc09a11207e2f43cce9c1d328905b636d618c72f3ab76325ef766201c5b7':
        raise ValueError('reviewed receipt parser changed')
    # Identity substitution is confined to a complete, single experiment field.
    # No V4 observation budget or candidate identity is reused.
    original = 'experiment=a53-authenticated-baseline'
    lines = raw.splitlines()
    if lines.count(original) != 1 or any(line.startswith('experiment=') and line != original for line in lines):
        raise ValueError('wrong or duplicate baseline experiment receipt')
    translated = '\n'.join('experiment=2026-09-04-mt6797-thermal-snapshot' if line == original else line for line in lines)
    return runpy.run_path(str(PARSER))['receipt'](translated, candidate)
