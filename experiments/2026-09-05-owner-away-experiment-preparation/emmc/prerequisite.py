#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Explicit prerequisite selection for offline eMMC preparation only."""
import hashlib
import importlib.util
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / 'baseline/scripts'
SELECTORS = {
    'original-strict': ('verified_baseline.py',
        'ba70f6df476283c0113d433ae856940cc9c031f864019da95f014324e16c926e',
        'verified-first-authenticated-baseline-and-recovery'),
    'reviewed-supplemental': ('supplemental_recovery.py',
        'c0cc57dbc8c782bb7a995716c3b0dcdd74d7068dc84200d3954012a619b8b293',
        'supplemental-authenticated-baseline-recovery-verified'),
}


def verify_prerequisite(evidence_root, selector, bindings):
    if selector not in SELECTORS:
        raise ValueError('explicit reviewed prerequisite selector required')
    name, expected, classification = SELECTORS[selector]
    path = BASE / name
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('prerequisite source symlink')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('prerequisite source changed')
    spec = importlib.util.spec_from_file_location('emmc_selected_prerequisite', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.verify(evidence_root, bindings)
    if result['classification'] != classification or result['dependent_admission'] is not False:
        raise ValueError('prerequisite result outside reviewed scope')
    return {'prerequisite_selector': selector, 'verifier_sha256': expected,
            'evidence_result': result, 'preparation_only': True, 'execution_enabled': False}


def execute(*_args, **_kwargs):
    # Unconditional and before all argument, file, process or transport handling.
    raise ValueError('eMMC execution disabled pending coordinator review')


if __name__ == '__main__':
    execute()
