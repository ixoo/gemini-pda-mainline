#!/usr/bin/env python3
"""Exercise deterministic mask generation and reject contract mutations."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
GENERATOR_PATH = SCRIPT_DIR / "generate-patches.py"
spec = importlib.util.spec_from_file_location("mask_generator", GENERATOR_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("FAIL: generator import unavailable")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def validate(root: Path, phase: str) -> int:
    return subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_source.py"),
         "--source-root", str(root), "--phase", phase],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    ).returncode


with tempfile.TemporaryDirectory(prefix="a72-cpu-status-mask-test-") as temp:
    root = Path(temp) / "source"
    generator.prepare_parent(root)
    subprocess.run(["python3", str(SCRIPT_DIR / "source_edits.py"),
                    "--source-root", str(root), "--phase", "production"], check=True)
    if validate(root, "production") != 0:
        raise SystemExit("FAIL: valid production source rejected")
    subprocess.run(["python3", str(SCRIPT_DIR / "source_edits.py"),
                    "--source-root", str(root), "--phase", "tests"], check=True)
    if validate(root, "tests") != 0:
        raise SystemExit("FAIL: valid test source rejected")

    mutations = (
        ("drivers/soc/mediatek/mt6797-a72-platform-state.c",
         "GENMASK(7, 6)", "GENMASK(7, 5)"),
        ("drivers/soc/mediatek/mt6797-a72-platform-state.c",
         "MT6797_A72_CPU_PWR_STATUS_MASK)\n\t\tmovement |=",
         "GENMASK(31, 0))\n\t\tmovement |="),
        ("drivers/soc/mediatek/mt6797-a72-platform-state.c",
         "ops->read_once(context, &first)",
         "ops->read_once(context, &first) + ops->read_once(context, &first)"),
        ("drivers/soc/mediatek/mt6797-a72-platform-state.c",
         "return -EBUSY;", "return -EAGAIN;"),
        ("drivers/soc/mediatek/mt6797-a72-platform-state-test.c",
         "status_bits[] = { BIT(6), BIT(7) }", "status_bits[] = { BIT(6) }"),
        ("drivers/soc/mediatek/mt6797-a72-platform-state-test.c",
         "word < 2", "word < 1"),
        ("drivers/soc/mediatek/mt6797-a72-platform-state-test.c",
         "0x003dcf08", "0x003dc708"),
        ("drivers/soc/mediatek/mt6797-a72-platform-state-test.c",
         "KUNIT_CASE(mt6797_state_each_a72_identity_bit_test),", ""),
    )
    rejected = 0
    for relative, old, new in mutations:
        path = root / relative
        original = path.read_text(encoding="utf-8")
        if original.count(old) < 1:
            raise SystemExit(f"FAIL: fixture anchor changed: {old}")
        path.write_text(original.replace(old, new, 1), encoding="utf-8")
        if validate(root, "tests") == 0:
            raise SystemExit(f"FAIL: accepted mutation: {old}")
        rejected += 1
        path.write_text(original, encoding="utf-8")

with tempfile.TemporaryDirectory(prefix="a72-cpu-status-mask-packages-") as temp:
    roots = [Path(temp) / "first", Path(temp) / "second"]
    for root in roots:
        subprocess.run(["python3", str(GENERATOR_PATH), "--output", str(root)],
                       check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["python3", str(SCRIPT_DIR / "validate_patch.py"),
                        "--patch-dir", str(root)], check=True,
                       stdout=subprocess.DEVNULL)
    files = (*generator.PATCHES, "series", "SHA256SUMS")
    for name in files:
        if (roots[0] / name).read_bytes() != (roots[1] / name).read_bytes():
            raise SystemExit(f"FAIL: nondeterministic generated file: {name}")

print("tooling_validation=pass")
print("generated_patch_count=2")
print(f"tooling_rejected_mutations={rejected}")
print("deterministic_generations=2")
print("native_vm_build=false")
print("device_action=none")
