#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Use the reviewed A53 collector with the VCN28 observer candidate."""

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / '2026-09-27-mt6797-conn-domain-link-passive/passive-session.py'
SPEC = importlib.util.spec_from_file_location('conn_domain_session', SOURCE)
DOMAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOMAIN)
DOMAIN.SESSION.HERE = HERE
SOURCE_PINS = DOMAIN.SOURCE_PINS
load = DOMAIN.load
boot_uuid = DOMAIN.boot_uuid
prepare = DOMAIN.prepare
classify = DOMAIN.classify
