#!/usr/bin/env python3
"""Mutation tests for the module-policy control profile validator."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parents[2]
VALIDATOR = SCRIPT_DIR / "validate.py"
spec = importlib.util.spec_from_file_location("module_control_validator", VALIDATOR)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def rejected(manifest: dict, fragment: str) -> bool:
    try:
        validator.validate_profile(manifest, fragment)
    except AssertionError:
        return True
    return False


def main() -> None:
    manifest = json.loads((REPO / "kernel/manifest.json").read_text(encoding="utf-8"))
    fragment = (REPO / validator.FRAGMENT).read_text(encoding="utf-8")
    validator.validate_profile(manifest, fragment)
    mutations: list[tuple[dict, str]] = []

    changed = copy.deepcopy(manifest)
    changed["config"]["profiles"][validator.PROFILE]["fragments"].pop()
    mutations.append((changed, fragment))

    changed = copy.deepcopy(manifest)
    changed["config"]["profiles"][validator.PROFILE]["base"] = "wrong"
    mutations.append((changed, fragment))

    changed = copy.deepcopy(manifest)
    changed["config"]["profiles"][validator.PROFILE]["patch_series"] = "patches/series"
    mutations.append((changed, fragment))

    changed = copy.deepcopy(manifest)
    changed["config"]["profiles"][validator.PROFILE]["fragments"].insert(
        -1, "configs/gemini-da921x-readonly-observer.fragment"
    )
    mutations.append((changed, fragment))

    changed = copy.deepcopy(manifest)
    final = changed["config"]["profiles"][validator.PROFILE]["fragments"]
    final[-1], final[-2] = final[-2], final[-1]
    mutations.append((changed, fragment))

    mutations.append((copy.deepcopy(manifest), fragment + "CONFIG_MODULE_UNLOAD=y\n"))
    assert all(rejected(*mutation) for mutation in mutations), "mutation escaped validation"
    print("validation=mainline-module-policy-control-mutations")
    print(f"negative_mutations_rejected={len(mutations)}")
    print("result=pass")


if __name__ == "__main__":
    main()
