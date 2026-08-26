#!/usr/bin/env python3
"""Exercise deterministic generation and reject movement-contract mutations."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
GENERATOR_PATH = SCRIPT_DIR / "generate-patches.py"
spec = importlib.util.spec_from_file_location("movement_generator", GENERATOR_PATH)
if spec is None or spec.loader is None:
    raise SystemExit("FAIL: generator import unavailable")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


def run_validator(root: Path, phase: str) -> int:
    return subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_source.py"),
         "--source-root", str(root), "--phase", phase],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    ).returncode


with tempfile.TemporaryDirectory(prefix="a72-platform-movement-test-") as temp:
    root = Path(temp) / "source"
    generator.prepare_parent(root)
    subprocess.run(
        ["python3", str(SCRIPT_DIR / "source_edits.py"),
         "--source-root", str(root), "--phase", "production"], check=True,
    )
    if run_validator(root, "production") != 0:
        raise SystemExit("FAIL: valid production source rejected")
    subprocess.run(
        ["python3", str(SCRIPT_DIR / "source_edits.py"),
         "--source-root", str(root), "--phase", "tests"], check=True,
    )
    if run_validator(root, "tests") != 0:
        raise SystemExit("FAIL: valid test source rejected")

    mutations = (
        ("include/linux/soc/mediatek/mt6797-a72-platform-state.h",
         "MT6797_A72_PLATFORM_MOVED_PWRAP_RESET = BIT(8)",
         "MT6797_A72_PLATFORM_MOVED_PWRAP_RESET = BIT(7)"),
        ("drivers/soc/mediatek/mt6797-a72-platform-state.c",
         "ops->read_once(context, &first)",
         "ops->read_once(context, &first) + ops->read_once(context, &first)"),
        ("drivers/soc/mediatek/mt6797-a72-platform-state.c",
         "return -EBUSY;", "return -EAGAIN;"),
        ("drivers/soc/mediatek/mt6797-a72-platform-provider-clock-observer.c",
         "movement=%03x", "movement=%02x"),
        ("drivers/soc/mediatek/mt6797-a72-platform-provider-clock-observer.c",
         "ret == -EAGAIN &&", "ret &&"),
        ("drivers/soc/mediatek/mt6797-a72-platform-state-test.c",
         "KUNIT_CASE(mt6797_state_masked_noise_test),", ""),
        ("drivers/soc/mediatek/mt6797-a72-platform-provider-clock-observer-test.c",
         "platform_failure.movement_mask", "snapshot.platform.spm_pwr_status"),
        ("drivers/soc/mediatek/Kconfig",
         "config MTK_MT6797_A72_PLATFORM_STATE_KUNIT_TEST",
         "config MTK_MT6797_A72_PLATFORM_STATE_TEST"),
    )
    rejected = 0
    for relative, old, new in mutations:
        path = root / relative
        original = path.read_text(encoding="utf-8")
        if original.count(old) < 1:
            raise SystemExit(f"FAIL: fixture anchor changed: {old}")
        path.write_text(original.replace(old, new, 1), encoding="utf-8")
        if run_validator(root, "tests") == 0:
            raise SystemExit(f"FAIL: accepted tooling mutation: {old}")
        rejected += 1
        path.write_text(original, encoding="utf-8")

with tempfile.TemporaryDirectory(prefix="a72-platform-movement-packages-") as temp:
    roots = [Path(temp) / "first", Path(temp) / "second"]
    for root in roots:
        subprocess.run(
            ["python3", str(GENERATOR_PATH), "--output", str(root)],
            check=True, stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            ["python3", str(SCRIPT_DIR / "validate_patch.py"),
             "--patch-dir", str(root)], check=True, stdout=subprocess.DEVNULL,
        )
    files = ("0380-soc-mediatek-report-A72-platform-state-movement.patch",
             "0381-soc-mediatek-test-A72-platform-state-movement.patch",
             "series", "SHA256SUMS")
    for name in files:
        if (roots[0] / name).read_bytes() != (roots[1] / name).read_bytes():
            raise SystemExit(f"FAIL: nondeterministic generated file: {name}")

print("tooling_validation=pass")
print("generated_patch_count=2")
print(f"tooling_rejected_mutations={rejected}")
print("deterministic_generations=2")
print("native_vm_build=false")
print("device_action=none")
