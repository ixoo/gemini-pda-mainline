#!/usr/bin/env python3
"""Exercise generated rollback patch validation and mutation tripwires."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


VALIDATOR = Path(__file__).with_name("validate_patches.py")


def run_validator(patch_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--patch-dir", str(patch_dir)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def mutate(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise AssertionError(
            f"{path.name}: expected one mutation target {old!r}, "
            f"found {text.count(old)}"
        )
    path.write_text(text.replace(old, new, 1))


def expect_rejected(
    patch_dir: Path,
    label: str,
    patch_name: str,
    old: str,
    new: str,
    expected: str,
) -> None:
    with tempfile.TemporaryDirectory(prefix="a72-preiso-static-") as temporary:
        copied = Path(temporary) / "patches"
        shutil.copytree(patch_dir, copied)
        mutate(copied / patch_name, old, new)
        result = run_validator(copied)
        if result.returncode == 0:
            raise AssertionError(f"{label}: unsafe mutation was accepted")
        output = result.stdout + result.stderr
        if expected not in output:
            raise AssertionError(f"{label}: unexpected rejection:\n{output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", required=True, type=Path)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    result = run_validator(patch_dir)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)

    p1, p2, p3 = (
        "0001-diagnostic-extend-A72-observer-rollback-ABI.patch",
        "0002-diagnostic-add-exact-A72-rollback-owner-operations.patch",
        "0003-diagnostic-stop-and-unwind-first-CPU8-pre-isolation.patch",
    )
    cases = [
        ("writable config", p3, "+\tdefault n", "+\tdefault y", "default n"),
        (
            "one-shot removal",
            p3,
            "+\tif (cpu != 8 || atomic_xchg(&mt6797_a72_preiso_attempted, 1))",
            "+\tif (cpu != 8)",
            "atomic_xchg",
        ),
        (
            "CPU9 admission",
            p3,
            "+\t\tif (cpu == 9) {",
            "+\t\tif (cpu == 10) {",
            "CPU9 rejection count changed",
        ),
        (
            "bypass admission",
            p3,
            "+\t\tif (bypass_boot > 0) {",
            "+\t\tif (bypass_boot < 0) {",
            "diagnostic bypass rejection count changed",
        ),
        (
            "PSCI dominance removal",
            p3,
            "+\t\t\t\t\tgoto mt6797_a72_boot_out;",
            "+\t\t\t\t\treturn err;",
            "caller exit count changed",
        ),
        (
            "isolation boundary",
            p3,
            "+\t\t\tMT6797_A72_PHASE_POWER_ON_PRE, 0x290, 0x2, 0x2);",
            "+\t\t\tMT6797_A72_PHASE_SPM_ISOLATION_CLEAR, 0x290, 0x2, 0);",
            "isolation boundary crossed",
        ),
        (
            "DA921x page drift",
            p2,
            "+\tif (snapshot.page_before != 0x80) {",
            "+\tif (snapshot.page_before != 0x00) {",
            "snapshot.page_before != 0x80",
        ),
        (
            "DA921x VSEL drift",
            p2,
            "+\tif (!!(buck & 1) != expected || snapshot.buck_vsel != 0x46) {",
            "+\tif (!!(buck & 1) != expected || snapshot.buck_vsel != 0x45) {",
            "VSEL entry/final equality count changed",
        ),
        (
            "SPM compare inversion",
            p2,
            "+\tif (mutation.before != expected) {",
            "+\tif (mutation.before == expected) {",
            "mutation.before != expected",
        ),
        (
            "TOPRGU readback inversion",
            p2,
            "+\t\tif (!!(snapshot.after & snapshot.mask) != requested)",
            "+\t\tif (!!(snapshot.after & snapshot.mask) == requested)",
            "snapshot.after & snapshot.mask",
        ),
        (
            "terminal disposition drift",
            p1,
            '+\tcase MT6797_A72_OBS_ROLLED_BACK: return "rolled-back";',
            '+\tcase MT6797_A72_OBS_ROLLED_BACK: return "complete";',
            'return "rolled-back"',
        ),
        (
            "userspace control",
            p3,
            "+static atomic_t mt6797_a72_preiso_attempted = ATOMIC_INIT(0);",
            "+module_param_named(run, mt6797_a72_preiso_attempted, int, 0600);",
            "module control",
        ),
    ]
    for case in cases:
        expect_rejected(patch_dir, *case)
    print(f"PASS: generated rollback patches and {len(cases)} mutation tripwires")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
