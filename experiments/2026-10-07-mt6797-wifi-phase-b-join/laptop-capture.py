#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run capture-private.py from a checkout without private artifacts.

Environment: GEMINI_PRIVATE_REPO (the checkout holding artifacts/credentials),
GEMINI_RUNTIME_ROOT (fresh evidence root) and GEMINI_JOIN_SCRIPT. The only
change to the public capture is where the baseline collector is loaded from:
the private checkout's copy, so that its own repository root resolves to the
credentials. Everything else, including the one-attempt capture claim, is the
public adapter's. No device action beyond the public capture itself.
"""

import importlib.util
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PRIVATE_REPO = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True)
SPEC = importlib.util.spec_from_file_location('wifi_phase_b_capture', HERE / 'capture-private.py')
CAPTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAPTURE)


def remap(path):
    """Move a public-checkout path to the same relative path in the private checkout."""
    path = Path(path)
    if not path.is_relative_to(REPO):
        raise ValueError('path outside this checkout: ' + str(path))
    return PRIVATE_REPO / path.relative_to(REPO)


CAPTURE.WMT.CAPTURE.BASELINE = remap(CAPTURE.WMT.CAPTURE.BASELINE)

if __name__ == '__main__':
    raise SystemExit(CAPTURE.main())
