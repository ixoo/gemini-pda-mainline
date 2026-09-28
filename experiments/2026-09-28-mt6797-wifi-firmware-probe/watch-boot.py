#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Pre-arm the reviewed USB-stage watcher for the passive WLAN probe."""

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-27-mt6797-conn-domain-link-passive/watch-boot.py'
SPEC = importlib.util.spec_from_file_location('conn_domain_watch', SOURCE)
WATCH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WATCH)
WATCH.HOST = HERE / 'passive-host.py'
WATCH.OUTPUT = HERE.parents[1] / 'artifacts/wifi-firmware-probe'


if __name__ == '__main__':
    raise SystemExit(WATCH.main())
