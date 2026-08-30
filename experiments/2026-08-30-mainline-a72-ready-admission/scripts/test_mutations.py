#!/usr/bin/env python3
"""Reject unsafe READY-candidate repair mutations."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import shutil
import tempfile
from typing import Callable


SCRIPT_DIR = Path(__file__).resolve().parent
FILES = (
    "arch/arm64/include/asm/late_cpu_profile.h",
    "arch/arm64/kernel/mt6797_psci.c",
)


def load_validator():
    spec = importlib.util.spec_from_file_location(
        "ready_candidate_validate", SCRIPT_DIR / "validate_source.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALIDATE = load_validator()


def replace(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"mutation anchor changed: {relative}: {old!r}")
    path.write_text(text.replace(old, new, 1))


def mutations() -> list[tuple[str, Callable[[Path], None]]]:
    header = "arch/arm64/include/asm/late_cpu_profile.h"
    profile = "arch/arm64/kernel/mt6797_psci.c"
    return [
        ("drop-always-visible-boot-cap-prototype", lambda root: replace(
            root, header, "int arm64_late_cpu_validate_boot_caps(void);\n\n", "")),
        ("duplicate-boot-cap-prototype", lambda root: replace(
            root, header, "int arm64_late_cpu_validate_boot_caps(void);\n",
            "int arm64_late_cpu_validate_boot_caps(void);\n"
            "int arm64_late_cpu_validate_boot_caps(void);\n")),
        ("drop-config-off-preflight", lambda root: replace(
            root, header,
            "static inline int\narm64_validate_late_cpu_preflight(unsigned int cpu)\n"
            "{\n\treturn 0;\n}\n\n", "")),
        ("fail-closed-when-disabled", lambda root: replace(
            root, header,
            "arm64_validate_late_cpu_preflight(unsigned int cpu)\n"
            "{\n\treturn 0;\n}",
            "arm64_validate_late_cpu_preflight(unsigned int cpu)\n"
            "{\n\treturn -EINVAL;\n}")),
        ("call-boot-cap-scan-when-disabled", lambda root: replace(
            root, header,
            "arm64_validate_late_cpu_preflight(unsigned int cpu)\n"
            "{\n\treturn 0;\n}",
            "arm64_validate_late_cpu_preflight(unsigned int cpu)\n"
            "{\n\treturn arm64_late_cpu_validate_boot_caps();\n}")),
        ("restore-obsolete-config-identity", lambda root: replace(
            root, profile,
            "\t0x5968c24f1904c055, 0x9dea25480c41fbc7,\n"
            "\t0xdb49e822dc3600d1, 0xbdd7632330853f40,\n",
            "\t0x699f14786e1d64eb, 0x3811f0b6c481c31d,\n"
            "\t0x9e0e77fc96b64eb4, 0xd12ebbbfde3b23b0,\n")),
        ("mutate-candidate-config-identity", lambda root: replace(
            root, profile, "0xbdd7632330853f40", "0xbdd7632330853f41")),
        ("mutate-fixture-identity", lambda root: replace(
            root, profile, "0x94cfddf0be8d7a74", "0x94cfddf0be8d7a75")),
        ("drop-runtime-config-comparison", lambda root: replace(
            root, profile,
            "\t    memcmp(evidence->config_input_identity,\n"
            "\t\t   mt6797_a72_config_input_identity,\n"
            "\t\t   sizeof(evidence->config_input_identity)) ||\n"
            "\t    memcmp(&evidence->expected_pair, &mt6797_a72_expected_pair,\n",
            "\t    memcmp(&evidence->expected_pair, &mt6797_a72_expected_pair,\n")),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    rejected = 0
    for name, mutate in mutations():
        with tempfile.TemporaryDirectory(prefix="a72-ready-mutation-") as tmp:
            root = Path(tmp)
            for relative in FILES:
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / relative, destination)
            mutate(root)
            try:
                VALIDATE.validate(root)
            except (OSError, ValueError, VALIDATE.ValidationError):
                rejected += 1
            else:
                raise AssertionError(f"unsafe mutation accepted: {name}")
    print("mutation_validation=pass")
    print(f"unsafe_source_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
