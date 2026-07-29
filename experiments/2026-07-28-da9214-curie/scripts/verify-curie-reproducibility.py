#!/usr/bin/env python3
"""Verify two Curie builds and their 2x2 LK assembly matrix offline."""

from __future__ import annotations

import hashlib
import pathlib
import stat
import sys

sys.dont_write_bytecode = True


FERMI_VERIFIER = (
    "experiments/2026-07-28-da9214-fermi/"
    "scripts/verify-fermi-reproducibility.py"
)
FERMI_VERIFIER_SHA256 = (
    "11bbabe6f913dc93943e525f3587e1f1b2979ff5846f924c6edf19f5eb8ee4af"
)
FERMI_CANDIDATE_MODULE_SHA256 = (
    "3422bb29490f21f0410d4d45f521fc3ac89eff3679d117535c7b5dcf0cffe5e6"
)
FERMI_PACKAGE_VALIDATOR_SHA256 = (
    "20c15b859a1fb04f562ff4955fff034bec65edbdceea17c1a9062f4be3585fc2"
)
CURIE_CANDIDATE_MODULE_SHA256 = (
    "47494b3280f0e098a61469f03f6c91dfe887260719c0f144cccde4101dcea683"
)
CURIE_PACKAGE_VALIDATOR_SHA256 = (
    "1984c5bd7e63ce6cf88d9fb59d015567fb4051028bea53a473b6c14edcc5b04c"
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
    text = source
    for old, new, count in (
        (
            FERMI_CANDIDATE_MODULE_SHA256,
            CURIE_CANDIDATE_MODULE_SHA256,
            1,
        ),
        (
            FERMI_PACKAGE_VALIDATOR_SHA256,
            CURIE_PACKAGE_VALIDATOR_SHA256,
            1,
        ),
        ("FERMI", "CURIE", 7),
        ("Fermi", "Curie", 6),
        ("fermi", "curie", 6),
    ):
        text = replace_exact(text, old, new, count)
    required = {
        'SCRIPT_DIR / "candidate_curie.py"': 1,
        'SCRIPT_DIR / "validate-package-curie.py"': 1,
        'LK_EXPECTED_NAME = "gemini-curie"': 1,
        r'"candidate=Curie\\n"': 1,
        '"validation=curie-two-build-2x2-reproducibility"': 1,
        CURIE_CANDIDATE_MODULE_SHA256: 1,
        CURIE_PACKAGE_VALIDATOR_SHA256: 1,
        "device_access=none": 1,
        "runtime_result=not-tested": 1,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise ValueError(f"derived Curie verifier changed for {token!r}")
    for stale in (
        "candidate_fermi.py",
        "validate-package-fermi.py",
        "gemini-fermi",
        "candidate=Fermi",
        "validation=fermi-two-build-2x2-reproducibility",
        FERMI_CANDIDATE_MODULE_SHA256,
        FERMI_PACKAGE_VALIDATOR_SHA256,
    ):
        if stale in text:
            raise ValueError(f"derived Curie verifier retained {stale!r}")
    return text


def load_source() -> str:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    path = repository / FERMI_VERIFIER
    data = regular(path, "source-pinned Fermi reproducibility verifier")
    if hashlib.sha256(data).hexdigest() != FERMI_VERIFIER_SHA256:
        raise ValueError("source-pinned Fermi reproducibility verifier changed")
    return derive_source(data.decode("utf-8", "strict"))


exec(compile(load_source(), __file__, "exec"), globals(), globals())
