#!/usr/bin/env python3
"""Run Fermi's fixed topology diagnostic once and preserve evidence."""

from __future__ import annotations

import hashlib
import pathlib
import stat
import sys

sys.dont_write_bytecode = True


QUASAR_RUNNER = (
    "experiments/2026-07-27-mt6797-i2c6-quasar/"
    "scripts/run-quasar-one-shot.py"
)
QUASAR_RUNNER_SHA256 = (
    "5a2f0b2c30ff0e2ab2d32fb80a87cffbade769cc37bc943dd0ae95c80b1e5198"
)
QUASAR_PACKAGE_VALIDATOR_SHA256 = (
    "bdf18fcf4b8dd1668ff80d50645ea57488e98eee05bb6eb65520faaad40602d5"
)
QUASAR_RESULT_VALIDATOR_SHA256 = (
    "0a2c532dae2ff19438cdfecc0b12ac8c473b23a4b7a40dfce1c151cd9acc19f5"
)
FERMI_PACKAGE_VALIDATOR_SHA256 = (
    "20c15b859a1fb04f562ff4955fff034bec65edbdceea17c1a9062f4be3585fc2"
)
FERMI_RESULT_VALIDATOR_SHA256 = (
    "546dd097a7497627351684759d60377f14b7b4aae1a869a5e1eafda767cde3a3"
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
    replacements = (
        ("QUASAR", "FERMI", 35),
        ("Quasar", "Fermi", 28),
        ("quasar", "fermi", 20),
        (
            QUASAR_PACKAGE_VALIDATOR_SHA256,
            FERMI_PACKAGE_VALIDATOR_SHA256,
            1,
        ),
        (
            QUASAR_RESULT_VALIDATOR_SHA256,
            FERMI_RESULT_VALIDATOR_SHA256,
            1,
        ),
        ("20260727", "20260728", 3),
    )
    text = source
    for old, new, count in replacements:
        text = replace_exact(text, old, new, count)
    text = replace_exact(
        text,
        '        ("orion-run-all", "fermi-run-native", 4),\n'
        "        (\n"
        "            VEGA_PACKAGE_VALIDATOR_SHA256,",
        '        ("orion-run-all", "fermi-run-native", 4),\n'
        '        ("20260727", "20260728", 1),\n'
        "        (\n"
        "            VEGA_PACKAGE_VALIDATOR_SHA256,",
        1,
    )
    required = {
        "import candidate_fermi as co": 1,
        '"validate-package-fermi.py"': 1,
        'KERNEL_RELEASE = "7.1.3-gemini-fermi"': 1,
        "GEMINI_FERMI_20260728": 2,
        "fermi-run-native": 3,
        "guard_path=/run/fermi-run-all.invoked": 1,
        "debugfs_root=/run/fermi-debugfs": 1,
        '"validate-fermi-result.py"': 1,
        "validation=fermi-runtime-one-shot": 1,
        "validation=fermi-exact-serviceability-gated-one-shot": 1,
        FERMI_PACKAGE_VALIDATOR_SHA256: 1,
        FERMI_RESULT_VALIDATOR_SHA256: 1,
        "post_capture=unconditional-even-after-negative-write": 2,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise ValueError(f"derived Fermi runner changed for {token!r}")
    for stale in (
        "candidate_quasar",
        "validate-package-quasar.py",
        "validate-quasar-result.py",
        "gemini-quasar",
        "GEMINI_QUASAR",
        "quasar-run-native",
    ):
        if stale in text:
            raise ValueError(f"derived Fermi runner retained {stale!r}")
    return text


def load_source() -> str:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    path = repository / QUASAR_RUNNER
    data = regular(path, "source-pinned Quasar one-shot runner")
    if hashlib.sha256(data).hexdigest() != QUASAR_RUNNER_SHA256:
        raise ValueError("source-pinned Quasar one-shot runner changed")
    return derive_source(data.decode("utf-8", "strict"))


exec(compile(load_source(), __file__, "exec"), globals(), globals())
