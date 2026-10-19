#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse exact retained-source/credential-separation tests for S1."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
body = (HERE / 'ccmp-gtk8-installer-sources-test.py').read_text().replace(
    'install-ccmp-gtk8.py', 'install-ccmp-core-disconnect.py').replace('GTK8', 'S1')
exec(compile(body, 's1-installer-source-fixture', 'exec'), {'__file__': __file__})
