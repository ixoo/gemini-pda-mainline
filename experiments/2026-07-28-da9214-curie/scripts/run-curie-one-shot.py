#!/usr/bin/env python3
"""Run Curie's fixed board-control diagnostic once and preserve evidence."""

from __future__ import annotations

import hashlib
import pathlib
import stat
import sys

sys.dont_write_bytecode = True


FERMI_RUNNER = (
    "experiments/2026-07-28-da9214-fermi/scripts/run-fermi-one-shot.py"
)
FERMI_RUNNER_SHA256 = (
    "e391f02ff5cc99296e1508e4a7b5bc4211c025a1e65f7f7a85adc6caa6fe7e11"
)
FERMI_PACKAGE_VALIDATOR_SHA256 = (
    "20c15b859a1fb04f562ff4955fff034bec65edbdceea17c1a9062f4be3585fc2"
)
FERMI_RESULT_VALIDATOR_SHA256 = (
    "546dd097a7497627351684759d60377f14b7b4aae1a869a5e1eafda767cde3a3"
)
CURIE_PACKAGE_VALIDATOR_SHA256 = (
    "1984c5bd7e63ce6cf88d9fb59d015567fb4051028bea53a473b6c14edcc5b04c"
)
CURIE_RESULT_VALIDATOR_SHA256 = (
    "2ed36315ef7c011c48673c06c63f5ea268aec10e9158600376905e6b821a2426"
)


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"runner token count changed for {old!r}: "
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
            FERMI_PACKAGE_VALIDATOR_SHA256,
            CURIE_PACKAGE_VALIDATOR_SHA256,
            1,
        ),
        (
            FERMI_RESULT_VALIDATOR_SHA256,
            CURIE_RESULT_VALIDATOR_SHA256,
            1,
        ),
        ("FERMI", "CURIE", 8),
        ("Fermi", "Curie", 4),
        ("fermi", "curie", 12),
        ("fixed topology diagnostic", "fixed board-control diagnostic", 1),
    ):
        text = replace_exact(text, old, new, count)
    required = {
        "import candidate_curie as co": 1,
        '"validate-package-curie.py"': 1,
        'KERNEL_RELEASE = "7.1.3-gemini-curie"': 1,
        "GEMINI_CURIE_20260728": 1,
        "curie-run-native": 3,
        "guard_path=/run/curie-run-all.invoked": 1,
        "debugfs_root=/run/curie-debugfs": 1,
        '"validate-curie-result.py"': 1,
        "validation=curie-runtime-one-shot": 1,
        "validation=curie-exact-serviceability-gated-one-shot": 1,
        CURIE_PACKAGE_VALIDATOR_SHA256: 1,
        CURIE_RESULT_VALIDATOR_SHA256: 1,
        "post_capture=unconditional-even-after-negative-write": 1,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise ValueError(f"derived Curie runner changed for {token!r}")
    for stale in (
        "candidate_fermi",
        "validate-package-fermi.py",
        "validate-fermi-result.py",
        "gemini-fermi",
        "GEMINI_FERMI",
        "fermi-run-native",
        "fixed topology diagnostic",
        FERMI_PACKAGE_VALIDATOR_SHA256,
        FERMI_RESULT_VALIDATOR_SHA256,
    ):
        if stale in text:
            raise ValueError(f"derived Curie runner retained {stale!r}")
    return text


def load_source() -> str:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    path = repository / FERMI_RUNNER
    data = regular(path, "source-pinned Fermi one-shot runner")
    if hashlib.sha256(data).hexdigest() != FERMI_RUNNER_SHA256:
        raise ValueError("source-pinned Fermi one-shot runner changed")
    return derive_source(data.decode("utf-8", "strict"))


exec(compile(load_source(), __file__, "exec"), globals(), globals())
