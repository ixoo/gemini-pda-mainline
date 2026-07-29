#!/usr/bin/env python3
"""Verify two Quasar builds and their 2x2 LK assembly matrix offline."""

from __future__ import annotations

import hashlib
import os
import pathlib
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True


VEGA_VERIFIER = (
    "experiments/2026-07-27-mt6797-i2c6-vega/"
    "scripts/verify-vega-reproducibility.py"
)
VEGA_VERIFIER_SHA256 = (
    "bed4403f37b74b69e688b0960a1e155cf208cebb9d09ed180c7a58ae2ab7242a"
)
VEGA_CANDIDATE_MODULE_SHA256 = (
    "225d134cf36cd025162bf99ef3a3ea0ad83c462b43577b95f933a3b297f0d379"
)
VEGA_PACKAGE_VALIDATOR_SHA256 = (
    "ef07f12d82c4db233f30a535500e0a688bcb13228b94fea7f8618fa4a6344eee"
)
QUASAR_CANDIDATE_MODULE_SHA256 = (
    "8ecca91a9ae34d2a77017341d20dbd5787aa5c105110e64fdb78fd06c0acce88"
)
QUASAR_PACKAGE_VALIDATOR_SHA256 = (
    "bdf18fcf4b8dd1668ff80d50645ea57488e98eee05bb6eb65520faaad40602d5"
)


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"verifier token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def derive_source(source: str) -> str:
    replacements = (
        ("Vega", "Quasar", 25),
        ("vega", "quasar", 7),
        (
            VEGA_CANDIDATE_MODULE_SHA256,
            QUASAR_CANDIDATE_MODULE_SHA256,
            1,
        ),
        (
            VEGA_PACKAGE_VALIDATOR_SHA256,
            QUASAR_PACKAGE_VALIDATOR_SHA256,
            1,
        ),
    )
    text = source
    for old, new, count in replacements:
        text = replace_exact(text, old, new, count)
    restored = text
    for old, new, count in reversed(replacements):
        restored = replace_exact(restored, new, old, count)
    if restored != source:
        raise ValueError("Quasar verifier cannot restore exact Vega foundation")
    required = {
        'SCRIPT_DIR / "candidate_quasar.py"': 1,
        'SCRIPT_DIR / "validate-package-quasar.py"': 1,
        'LK_EXPECTED_NAME = "gemini-quasar"': 1,
        '"candidate=Quasar\\n"': 1,
        '"validation=quasar-two-build-2x2-reproducibility"': 1,
        f'CANDIDATE_MODULE_SHA256 = (\n    "{QUASAR_CANDIDATE_MODULE_SHA256}"': 1,
        f'PACKAGE_VALIDATOR_SHA256 = (\n    "{QUASAR_PACKAGE_VALIDATOR_SHA256}"': 1,
        "device_access=none": 1,
        "runtime_result=not-tested": 2,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise ValueError(
                f"derived Quasar verifier contract changed for {token!r}"
            )
    for stale in (
        "candidate_vega.py",
        "validate-package-vega.py",
        "gemini-vega",
        "candidate=Vega",
        "validation=vega-two-build-2x2-reproducibility",
    ):
        if stale in text:
            raise ValueError(
                f"derived Quasar verifier retained stale token: {stale}"
            )
    return text


def load_implementation() -> ModuleType:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    source_path = repository / VEGA_VERIFIER
    source_data = regular(source_path, "source-pinned Vega verifier")
    if hashlib.sha256(source_data).hexdigest() != VEGA_VERIFIER_SHA256:
        raise ValueError("source-pinned Vega reproducibility verifier changed")
    source = derive_source(source_data.decode("utf-8", "strict"))
    name = "quasar_reproducibility_derived"
    module = ModuleType(name)
    module.__file__ = os.fspath(script)
    module.__package__ = ""
    sys.modules[name] = module
    try:
        exec(compile(source, os.fspath(script), "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


_IMPL = load_implementation()

ContractError = _IMPL.ContractError
InventoryMember = _IMPL.InventoryMember
PackageResult = _IMPL.PackageResult
CandidateResult = _IMPL.CandidateResult
LK_EXPECTED_NAME = _IMPL.LK_EXPECTED_NAME
LK_EXPECTED_CMDLINE = _IMPL.LK_EXPECTED_CMDLINE
LK_ANALYZER_RELATIVE = _IMPL.LK_ANALYZER_RELATIVE
LK_ANALYZER_SHA256 = _IMPL.LK_ANALYZER_SHA256
CANDIDATE_MODULE_SHA256 = _IMPL.CANDIDATE_MODULE_SHA256
PACKAGE_VALIDATOR_SHA256 = _IMPL.PACKAGE_VALIDATOR_SHA256
require_distinct_lanes = _IMPL.require_distinct_lanes
require_identical = _IMPL.require_identical
inventory_digest = _IMPL.inventory_digest
load_package_validator = _IMPL.load_package_validator
load_lk_analyzer = _IMPL.load_lk_analyzer
verify_lk_artifact = _IMPL.verify_lk_artifact
verify_padded_construction = _IMPL.verify_padded_construction
render_record = _IMPL.render_record
verify = _IMPL.verify


def main() -> int:
    return _IMPL.main()


if __name__ == "__main__":
    raise SystemExit(main())
