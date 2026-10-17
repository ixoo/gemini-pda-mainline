#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reuse the C32 config/refusal oracle for the REAL CCMP6 package compositor."""
from pathlib import Path

HERE = Path(__file__).resolve().parent
body = (HERE / 'ccmp-composition-test.py').read_text().replace(
    "'build-ccmp-candidate.py'", "'build-ccmp-candidate-6.py'")
exec(compile(body, 'reused-ccmp-config-oracle', 'exec'),
     {'__file__': str(HERE / 'ccmp-composition-test.py')})
