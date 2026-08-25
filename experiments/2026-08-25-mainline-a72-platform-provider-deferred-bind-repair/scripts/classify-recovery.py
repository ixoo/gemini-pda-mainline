#!/usr/bin/env python3
"""Classify exact changed-ID Gemian recovery for the provider-ready image."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE = REPO_ROOT / "experiments/2026-08-25-mainline-a72-platform-provider-snapshot-second-read/scripts/classify-recovery.py"
SOURCE_SHA256 = "489e848182924c91f6249717fbb4f05d8aa99f0a8c4a5b5e47d9c6eaa1d079b3"
CANDIDATE = "f55bb272de24a62a0e4055624e8eb0ef35bc53432fa130463c867c43c059732e"


if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source recovery classifier changed")
SPEC = importlib.util.spec_from_file_location("provider_ready_recovery_source", SOURCE)
assert SPEC is not None and SPEC.loader is not None
SOURCE_MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE_MODULE)
SOURCE_MODULE.CANDIDATE = CANDIDATE

PREFIX = SOURCE_MODULE.PREFIX
MARKER_1 = SOURCE_MODULE.MARKER_1
MARKER_2 = SOURCE_MODULE.MARKER_2
VALID_HEADER_1 = SOURCE_MODULE.VALID_HEADER_1
VALID_HEADER_2 = SOURCE_MODULE.VALID_HEADER_2
EMPTY_HEADER = SOURCE_MODULE.EMPTY_HEADER
classify = SOURCE_MODULE.classify
classify_text = SOURCE_MODULE.classify_text


if __name__ == "__main__":
    raise SystemExit(SOURCE_MODULE.main())
