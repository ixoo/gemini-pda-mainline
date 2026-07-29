#!/usr/bin/env python3
"""Validate Candidate Curie's exact kernel package and fail-closed DT."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True


FERMI_VALIDATOR = (
    "experiments/2026-07-28-da9214-fermi/scripts/validate-package-fermi.py"
)
FERMI_VALIDATOR_SHA256 = (
    "20c15b859a1fb04f562ff4955fff034bec65edbdceea17c1a9062f4be3585fc2"
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


def load_fermi(repository: pathlib.Path) -> ModuleType:
    source = repository / FERMI_VALIDATOR
    data = read_regular(source, "source-pinned Fermi package validator")
    if hashlib.sha256(data).hexdigest() != FERMI_VALIDATOR_SHA256:
        raise ValueError("source-pinned Fermi package validator changed")
    script_dir = source.parent
    sys.path.insert(0, str(script_dir))
    try:
        spec = importlib.util.spec_from_file_location(
            "curie_fermi_package_validator", source
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load source-pinned Fermi validator")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(spec.name, None)
            raise
        return module
    finally:
        sys.path.remove(str(script_dir))


def derive_source(source: str) -> str:
    text = source
    for old, new, count in (
        (
            '        b"topology_mask=07 topology_expected=05 ",',
            '        b"board_control_register=d3 board_control_expected=1f ",',
            1,
        ),
        (
            "if len(entries) != 109 or tuple(entries[-7:]) != co.FERMI_PATCHES:",
            "if len(entries) != 110 or tuple(entries[-8:]) != co.FERMI_PATCHES:",
            1,
        ),
        ('    print("patch_count=109")', '    print("patch_count=110")', 1),
        ("FERMI", "CURIE", 15),
        ("Fermi", "Curie", 29),
        ("fermi", "curie", 10),
    ):
        text = replace_exact(text, old, new, count)

    text = replace_exact(
        text,
        '    "mtk_i2c_quasar_write",\n}',
        '    "mtk_i2c_quasar_write",\n'
        '    "mtk_i2c_fermi_fops",\n'
        '    "mtk_i2c_fermi_read",\n'
        '    "mtk_i2c_fermi_write",\n'
        "}",
        1,
    )
    text = replace_exact(
        text,
        '    if "CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC=y" in config:\n'
        '        raise ValueError("Curie unexpectedly compiles the Quasar diagnostic")',
        '    if "CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC=y" in config:\n'
        '        raise ValueError("Curie unexpectedly compiles the Quasar diagnostic")\n'
        '    if "CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC=y" in config:\n'
        '        raise ValueError("Curie unexpectedly compiles the Fermi diagnostic")',
        1,
    )
    text = replace_exact(
        text,
        '        b"quasar-run-native",\n'
        '        b"modes=packed-fifo,packed-dma,aux-dma",',
        '        b"quasar-run-native",\n'
        '        b"GEMINI_FERMI_NATIVE_DIAGNOSTIC state=ready",\n'
        '        b"fermi-run-native",\n'
        '        b"modes=packed-fifo,packed-dma,aux-dma",',
        1,
    )

    required = {
        "import candidate_curie as co": 1,
        'CONFIG_LOCALVERSION="-gemini-curie"': 1,
        "GEMINI_CURIE_20260728": 2,
        "CONFIG_I2C_MT65XX_CURIE_DIAGNOSTIC=y": 1,
        "# CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC is not set": 1,
        "mtk_i2c_curie_fops": 1,
        "mtk_i2c_curie_read": 1,
        "mtk_i2c_curie_write": 1,
        "GEMINI_CURIE_NATIVE_DIAGNOSTIC state=ready": 1,
        "curie-run-native": 1,
        "addresses=0x69,0x68 passes=2": 1,
        "board_control_register=d3 board_control_expected=1f": 1,
        "stability_registers=d3,5e,d9,da stability_validated=%u": 1,
        "tuple(entries[-8:]) != co.CURIE_PATCHES": 1,
        'print("patch_count=110")': 1,
        'print("da9214_provider=absent")': 1,
        'print("cpu8_cpu9=fail-closed-unrequested")': 1,
        "CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC=y": 1,
        "GEMINI_FERMI_NATIVE_DIAGNOSTIC state=ready": 1,
        "fermi-run-native": 1,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise ValueError(
                f"derived Curie package validator changed for {token!r}"
            )
    allowed_stale = {
        "CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC=y": 1,
        "GEMINI_FERMI_NATIVE_DIAGNOSTIC state=ready": 1,
        "fermi-run-native": 1,
        "mtk_i2c_fermi_fops": 1,
        "mtk_i2c_fermi_read": 1,
        "mtk_i2c_fermi_write": 1,
    }
    for stale in (
        "candidate_fermi",
        "topology_mask=07 topology_expected=05",
        'print("patch_count=109")',
        *allowed_stale,
    ):
        if text.count(stale) != allowed_stale.get(stale, 0):
            raise ValueError(
                f"derived Curie package validator retains stale token: {stale}"
            )
    return text


def load_source() -> str:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    fermi = load_fermi(repository)
    return derive_source(fermi.load_source())


exec(compile(load_source(), __file__, "exec"), globals(), globals())
