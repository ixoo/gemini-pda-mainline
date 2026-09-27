#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Bind the reviewed boot2 installer to the passive CONMCU reset image."""

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-27-mt6797-consys-rails-passive/install-passive.py'
SPEC = importlib.util.spec_from_file_location('consys_rails_installer', SOURCE)
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)
INSTALLER.HERE = HERE
INSTALLER.EXPERIMENT = 'mt6797-consys-reset-passive'
INSTALLER.RECEIPT_NAME = 'mt6797-consys-reset-passive-deployment-1'
INSTALLER.MANIFEST_SHA = 'f75ef78fd3f5adaec6dd2b2c74b5216e59800b43cdd3ed319453cd79d699c10e'
MANIFEST_SHA = INSTALLER.MANIFEST_SHA
validate = INSTALLER.validate
receipt = INSTALLER.receipt


if __name__ == '__main__':
    INSTALLER.main()
