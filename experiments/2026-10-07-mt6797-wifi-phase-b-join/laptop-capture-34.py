#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Runtime 34 Phase-A capture binding: the reviewed laptop-capture.py (which
remaps the baseline collector to the private checkout) with the successor
identity (candidate 33, capture-34). It only pins GEMINI_PHASE_B_SESSION=34 and
runs the reviewed laptop capture unchanged; all logic, gates, pins and the
private-source remap live there and default to runtime 33 when unset."""
import os
import runpy
import sys
from pathlib import Path

os.environ['GEMINI_PHASE_B_SESSION'] = '34'
_base = Path(__file__).resolve().parent / 'laptop-capture.py'
sys.argv[0] = str(_base)
runpy.run_path(str(_base), run_name='__main__')
