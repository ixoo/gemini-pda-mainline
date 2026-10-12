#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Runtime 34 installer binding: the reviewed install-passive.py with the successor
identity (candidate 33 over the installed candidate 32 (deployment 33)). It only pins GEMINI_PHASE_B_SESSION=34 and runs the reviewed
tool unchanged; all logic, gates, pins and receipts live there and default to
runtime 33 when the variable is unset."""
import os
import runpy
import sys
from pathlib import Path

os.environ['GEMINI_PHASE_B_SESSION'] = '34'
_base = Path(__file__).resolve().parent / 'install-passive.py'
sys.argv[0] = str(_base)
runpy.run_path(str(_base), run_name='__main__')
