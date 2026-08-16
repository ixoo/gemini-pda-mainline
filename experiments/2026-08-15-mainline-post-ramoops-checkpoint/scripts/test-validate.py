#!/usr/bin/env python3
"""Reject unsafe or non-attributable post-ramoops checkpoint mutations."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("checkpoint_validate", SCRIPT_DIR / "validate.py")
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def rejected(manifest: dict[str, object], series: str, patch: str, fragment: str) -> bool:
    try:
        validator.validate_inputs(manifest, series, patch, fragment)
    except (AssertionError, ValueError):
        return True
    return False


def main() -> None:
    manifest = json.loads(validator.MANIFEST_PATH.read_text(encoding="utf-8"))
    series = validator.SERIES_PATH.read_text(encoding="utf-8")
    patch = validator.PATCH_PATH.read_text(encoding="utf-8")
    fragment = validator.FRAGMENT_PATH.read_text(encoding="utf-8")
    validator.validate_inputs(manifest, series, patch, fragment)

    cases: list[tuple[dict[str, object], str, str, str]] = []
    cases.append((manifest, series.replace(validator.PATCH_NAME + "\n", ""), patch, fragment))

    drift = copy.deepcopy(manifest)
    drift["config"]["profiles"][validator.PROFILE]["fragments"].insert(-1, "configs/gemini-da921x-readonly-observer.fragment")
    cases.append((drift, series, patch, fragment))

    cases.append((manifest, series, patch, fragment + "CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER=y\n"))
    cases.append((manifest, series, patch.replace("default n", "default y", 1), fragment))
    cases.append((manifest, series, patch.replace(validator.MARKER, validator.MARKER * 2, 1), fragment))
    cases.append((manifest, series, patch.replace("cpu8_cpu9_admission=closed", "cpu8_cpu9_admission=open", 1), fragment))
    cases.append((manifest, series, patch.replace("#endif", "\ti2c_transfer(adapter, msgs, 1);\n+#endif", 1), fragment))
    cases.append((manifest, series, patch.replace("err = pstore_register(&cxt->pstore);", "err = pstore_register_later(&cxt->pstore);", 1), fragment))

    count = sum(rejected(*case) for case in cases)
    if count != len(cases):
        raise AssertionError(f"only {count} of {len(cases)} mutations were rejected")
    print("validation=mainline-post-ramoops-checkpoint-mutations")
    print(f"negative_mutations_rejected={count}")
    print("result=pass")


if __name__ == "__main__":
    main()
