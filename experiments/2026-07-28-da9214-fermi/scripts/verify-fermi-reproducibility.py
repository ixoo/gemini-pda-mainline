#!/usr/bin/env python3
"""Verify two Fermi builds and their 2x2 LK assembly matrix offline."""

from __future__ import annotations

import hashlib
import os
import pathlib
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True


QUASAR_VERIFIER = (
    "experiments/2026-07-27-mt6797-i2c6-quasar/"
    "scripts/verify-quasar-reproducibility.py"
)
QUASAR_VERIFIER_SHA256 = (
    "88b9257cd21ee81a92b72d1beb99819bd8773e2c49e128cea3645d7a46011b14"
)
QUASAR_CANDIDATE_MODULE_SHA256 = (
    "8ecca91a9ae34d2a77017341d20dbd5787aa5c105110e64fdb78fd06c0acce88"
)
QUASAR_PACKAGE_VALIDATOR_SHA256 = (
    "bdf18fcf4b8dd1668ff80d50645ea57488e98eee05bb6eb65520faaad40602d5"
)
FERMI_CANDIDATE_MODULE_SHA256 = (
    "3422bb29490f21f0410d4d45f521fc3ac89eff3679d117535c7b5dcf0cffe5e6"
)
FERMI_PACKAGE_VALIDATOR_SHA256 = (
    "20c15b859a1fb04f562ff4955fff034bec65edbdceea17c1a9062f4be3585fc2"
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
        ("QUASAR", "FERMI", 6),
        ("Quasar", "Fermi", 6),
        ("quasar", "fermi", 6),
        (
            QUASAR_CANDIDATE_MODULE_SHA256,
            FERMI_CANDIDATE_MODULE_SHA256,
            1,
        ),
        (
            QUASAR_PACKAGE_VALIDATOR_SHA256,
            FERMI_PACKAGE_VALIDATOR_SHA256,
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
        raise ValueError("Fermi verifier cannot restore exact Quasar foundation")
    required = {
        'SCRIPT_DIR / "candidate_fermi.py"': 1,
        'SCRIPT_DIR / "validate-package-fermi.py"': 1,
        'LK_EXPECTED_NAME = "gemini-fermi"': 1,
        r'"candidate=Fermi\\n"': 1,
        '"validation=fermi-two-build-2x2-reproducibility"': 1,
        f'CANDIDATE_MODULE_SHA256 = (\n    "{FERMI_CANDIDATE_MODULE_SHA256}"': 1,
        f'PACKAGE_VALIDATOR_SHA256 = (\n    "{FERMI_PACKAGE_VALIDATOR_SHA256}"': 1,
        "device_access=none": 1,
        "runtime_result=not-tested": 1,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise ValueError(f"derived Fermi verifier changed for {token!r}")
    for stale in (
        "candidate_quasar.py",
        "validate-package-quasar.py",
        "gemini-quasar",
        "candidate=Quasar",
        "validation=quasar-two-build-2x2-reproducibility",
    ):
        if stale in text:
            raise ValueError(f"derived Fermi verifier retained {stale!r}")
    return text


def load_implementation() -> ModuleType:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    source_path = repository / QUASAR_VERIFIER
    source_data = regular(source_path, "source-pinned Quasar verifier")
    if hashlib.sha256(source_data).hexdigest() != QUASAR_VERIFIER_SHA256:
        raise ValueError("source-pinned Quasar reproducibility verifier changed")
    source = derive_source(source_data.decode("utf-8", "strict"))
    name = "fermi_reproducibility_derived"
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
