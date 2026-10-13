#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind real C34 and installed ND3 predecessor to unchanged guarded installation."""
import importlib.util
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ['GEMINI_PHASE_B_SESSION'] = '33'
SPEC = importlib.util.spec_from_file_location('runtime35_installer_base', HERE / 'install-passive.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
BASE = vars(MODULE)
GLOBALS = BASE['validate'].__globals__
MANIFEST_SHA = '8505a4867cdaaa20d2e9bd687f40958f8ec900ceb7467588e51a7e214cf5b3b3'
PREDECESSOR_SHA = '7b61241a89c9d8472885c93d654ecda6f63a188f154b2a7bfc69dd5caaf9dc06'
GLOBALS['_CANDIDATE'] = 'candidate-34'
GLOBALS['MANIFEST_SHA'] = MANIFEST_SHA
GLOBALS['PREDECESSOR_SHA'] = PREDECESSOR_SHA
ADAPTER = BASE['ADAPTER']
INSTALLER = ADAPTER.INSTALLER
ADAPTER.PREDECESSOR_SHA = PREDECESSOR_SHA
ADAPTER.MANIFEST_SHA = INSTALLER.MANIFEST_SHA = MANIFEST_SHA
INSTALLER.TOOL_NAME = 'install-passive-35.py'
INSTALLER.CANDIDATE_RECEIPT = 'results/candidate-34.json'
INSTALLER.RECEIPT_NAME = 'mt6797-wifi-phase-b-deployment-34'
validate, receipt = BASE['validate'], BASE['receipt']

if __name__ == '__main__':
    INSTALLER.main()
