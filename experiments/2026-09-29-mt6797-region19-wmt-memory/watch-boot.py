#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pre-arm one USB-stage watch for the private WMT-memory capture."""

import importlib.util
import os
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-27-mt6797-conn-domain-link-passive/watch-boot.py'
SPEC = importlib.util.spec_from_file_location('conn_domain_watch', SOURCE)
WATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WATCH)
WATCH.HOST = HERE / 'capture-private.py'
WATCH.OUTPUT = Path(os.environ['GEMINI_PRIVATE_REPO']).resolve(strict=True) / 'artifacts/region19-wmt-memory'


if __name__ == '__main__':
    raise SystemExit(WATCH.main())
