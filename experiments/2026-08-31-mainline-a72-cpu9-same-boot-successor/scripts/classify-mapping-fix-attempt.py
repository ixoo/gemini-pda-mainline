#!/usr/bin/env python3
"""Classify one CPU9 retained-reader mapping-fix runtime attempt."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys


SOURCE_SHA256 = "90e58cb4b7223cc038023cbf3f89ca351fbd805bbacd465d00ac1b95bcf21943"
VALIDATOR_SHA256 = "26fac1ea17aec094ba09c466956c4ccacab61f5e6ecc6aac2d1d385ab1597a7f"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("classify-progress-attempt.py")
VALIDATOR = SCRIPT.with_name("validate-mapping-fix-pretrigger.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU9 progress attempt classifier changed")
if hashlib.sha256(VALIDATOR.read_bytes()).hexdigest() != VALIDATOR_SHA256:
    raise SystemExit("CPU9 mapping-fix pre-trigger validator changed")


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


source = load("cpu9_progress_attempt", SOURCE)
mapping_pretrigger = load("cpu9_mapping_fix_pretrigger", VALIDATOR)
source.progress_pretrigger = mapping_pretrigger
source.source.PRE = mapping_pretrigger


if __name__ == "__main__":
    raise SystemExit(source.main())
