#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse pinned recovery routing tests for the S1 session namespace."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
body = (HERE / 'ccmp-gtk8-session-sources-test.py').read_text().replace(
    'laptop-session-ccmp-gtk8.py', 'laptop-session-ccmp-core-disconnect.py').replace(
    'session-ccmp-gtk8', 'session-ccmp-gtk8-s1').replace('GTK8', 'S1')
exec(compile(body, 's1-session-source-fixture', 'exec'), {'__file__': __file__})
