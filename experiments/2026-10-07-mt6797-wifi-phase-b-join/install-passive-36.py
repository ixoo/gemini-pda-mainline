#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Real C35/R36 installer binding; unchanged guards, actual ND3 predecessor."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('runtime36_installer_base', HERE / 'install-passive-35.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
MANIFEST_SHA = 'dcb3db4be44f8fbd6df9ea231de62ec8e6a6c9709dd8e12cb26a6c3c903638a2'
PREDECESSOR_SHA = '7b61241a89c9d8472885c93d654ecda6f63a188f154b2a7bfc69dd5caaf9dc06'
MODULE.GLOBALS['_CANDIDATE'] = 'candidate-35'
MODULE.GLOBALS['MANIFEST_SHA'] = MANIFEST_SHA
MODULE.GLOBALS['PREDECESSOR_SHA'] = PREDECESSOR_SHA
ADAPTER, INSTALLER = MODULE.ADAPTER, MODULE.INSTALLER
ADAPTER.PREDECESSOR_SHA = PREDECESSOR_SHA
ADAPTER.MANIFEST_SHA = INSTALLER.MANIFEST_SHA = MANIFEST_SHA
INSTALLER.TOOL_NAME = 'install-passive-36.py'
INSTALLER.CANDIDATE_RECEIPT = 'results/candidate-35.json'
INSTALLER.RECEIPT_NAME = 'mt6797-wifi-phase-b-deployment-35'
validate, receipt = MODULE.validate, MODULE.receipt

if __name__ == '__main__':
    INSTALLER.main()
