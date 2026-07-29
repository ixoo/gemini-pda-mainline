#!/usr/bin/env python3
"""Validate Candidate Fermi's exact kernel package and fail-closed DT."""

from __future__ import annotations

import hashlib
import pathlib
import stat
import sys

sys.dont_write_bytecode = True


QUASAR_VALIDATOR = (
    "experiments/2026-07-27-mt6797-i2c6-quasar/"
    "scripts/validate-package-quasar.py"
)
QUASAR_VALIDATOR_SHA256 = (
    "bdf18fcf4b8dd1668ff80d50645ea57488e98eee05bb6eb65520faaad40602d5"
)


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"package-validator token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def derive_source(source: str) -> str:
    replacements = (
        ("QUASAR", "FERMI", 15),
        ("Quasar", "Fermi", 28),
        ("quasar", "fermi", 10),
        ("20260727", "20260728", 2),
        (
            '    "# CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC is not set",\n'
            "    \"CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC=y\",",
            '    "# CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC is not set",\n'
            '    "# CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC is not set",\n'
            "    \"CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC=y\",",
            1,
        ),
        (
            '    "mtk_i2c_orion_run",\n}',
            '    "mtk_i2c_orion_run",\n'
            '    "mtk_i2c_quasar_read",\n'
            '    "mtk_i2c_quasar_write",\n'
            "}",
            1,
        ),
        (
            '    if "CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC=y" in config:\n'
            '        raise ValueError("Fermi unexpectedly compiles the Orion diagnostic")',
            '    if "CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC=y" in config:\n'
            '        raise ValueError("Fermi unexpectedly compiles the Orion diagnostic")\n'
            '    if "CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC=y" in config:\n'
            '        raise ValueError("Fermi unexpectedly compiles the Quasar diagnostic")',
            1,
        ),
        (
            '        b"GEMINI_ORION_DIAGNOSTIC state=ready",\n'
            '        b"modes=packed-fifo,packed-dma,aux-dma",',
            '        b"GEMINI_ORION_DIAGNOSTIC state=ready",\n'
            '        b"GEMINI_QUASAR_NATIVE_DIAGNOSTIC state=ready",\n'
            '        b"quasar-run-native",\n'
            '        b"modes=packed-fifo,packed-dma,aux-dma",',
            1,
        ),
        (
            '        b"candidate=Fermi state=%s one_shot=%s",\n'
            '        b"forced_length_mode=none forced_engine=none reset_pending=0",',
            '        b"candidate=%s state=%s one_shot=%s",\n'
            '        b"Fermi",\n'
            '        b"addresses=0x69,0x68 passes=2 ",\n'
            '        b"transfer_order=69:05,69:06,69:47,68:d3,68:5e,68:d9,68:da ",\n'
            '        b"topology_mask=07 topology_expected=05 ",\n'
            '        b"stability_registers=d3,5e,d9,da stability_validated=%u ",\n'
            '        b"sample=%u pass=%u index=%u address=%02x ",\n'
            '        b"forced_length_mode=none forced_engine=none reset_pending=0",',
            1,
        ),
        (
            "if len(entries) != 108 or tuple(entries[-6:]) != co.FERMI_PATCHES:",
            "if len(entries) != 109 or tuple(entries[-7:]) != co.FERMI_PATCHES:",
            1,
        ),
        ('    print("patch_count=108")', '    print("patch_count=109")', 1),
    )
    text = source
    for old, new, count in replacements:
        text = replace_exact(text, old, new, count)
    restored = text
    for old, new, count in reversed(replacements):
        restored = replace_exact(restored, new, old, count)
    if restored != source:
        raise ValueError(
            "Fermi package validator cannot restore exact Quasar foundation"
        )
    required = {
        "import candidate_fermi as co": 1,
        'CONFIG_LOCALVERSION="-gemini-fermi"': 1,
        "GEMINI_FERMI_20260728": 2,
        "CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC=y": 1,
        "# CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC is not set": 1,
        "mtk_i2c_fermi_fops": 1,
        "mtk_i2c_fermi_read": 1,
        "mtk_i2c_fermi_write": 1,
        "GEMINI_FERMI_NATIVE_DIAGNOSTIC state=ready": 1,
        "fermi-run-native": 1,
        "addresses=0x69,0x68 passes=2": 1,
        "topology_mask=07 topology_expected=05": 1,
        "stability_registers=d3,5e,d9,da stability_validated=%u": 1,
        "tuple(entries[-7:]) != co.FERMI_PATCHES": 1,
        'print("patch_count=109")': 1,
        'print("da9214_provider=absent")': 1,
        'print("cpu8_cpu9=fail-closed-unrequested")': 1,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise ValueError(
                f"derived Fermi package validator changed for {token!r}"
            )
    for stale in (
        "candidate_quasar",
        "CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC=y",
        "GEMINI_QUASAR_NATIVE_DIAGNOSTIC state=ready",
        "quasar-run-native",
        'print("patch_count=108")',
    ):
        # The Quasar symbol/markers remain only in explicit rejection strings.
        allowed = {
            "CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC=y": 1,
            "GEMINI_QUASAR_NATIVE_DIAGNOSTIC state=ready": 1,
            "quasar-run-native": 1,
        }.get(stale, 0)
        if text.count(stale) != allowed:
            raise ValueError(
                f"derived Fermi package validator retains stale token: {stale}"
            )
    return text


def load_source() -> str:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    path = repository / QUASAR_VALIDATOR
    data = read_regular(path, "source-pinned Quasar package validator")
    if hashlib.sha256(data).hexdigest() != QUASAR_VALIDATOR_SHA256:
        raise ValueError("source-pinned Quasar package validator changed")
    return derive_source(data.decode("utf-8", "strict"))


exec(compile(load_source(), __file__, "exec"), globals(), globals())
