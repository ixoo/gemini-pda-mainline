#!/usr/bin/env python3
"""Exercise recovery-only patch mutation tripwires."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


VALIDATOR = Path(__file__).with_name("validate_patches.py")


def run_validator(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--patch-dir", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def expect_rejected(
    patch_dir: Path, patch_name: str, old: str, new: str, expected: str
) -> None:
    with tempfile.TemporaryDirectory(prefix="a72-recovery-static-") as temporary:
        copied = Path(temporary) / "patches"
        shutil.copytree(patch_dir, copied)
        path = copied / patch_name
        text = path.read_text()
        if text.count(old) != 1:
            raise AssertionError(f"mutation target count changed for {old!r}")
        path.write_text(text.replace(old, new, 1))
        result = run_validator(copied)
        output = result.stdout + result.stderr
        if result.returncode == 0 or expected not in output:
            raise AssertionError(f"unsafe mutation not correctly rejected:\n{output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", required=True, type=Path)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    result = run_validator(patch_dir)
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)

    p1, p2, p3 = (
        "0001-diagnostic-reject-A72-during-recovery-gate.patch",
        "0002-diagnostic-add-exclusive-TOPRGU-recovery-owner.patch",
        "0003-diagnostic-run-bounded-watchdog-pstore-gate.patch",
    )
    cases = [
        (p1, "+\tdefault n", "+\tdefault y", "default n"),
        (p1, "+\tif (cpu == 8 || cpu == 9)", "+\tif (cpu == 9)", "if (cpu == 8 || cpu == 9)"),
        (p2, "+\tif (!state || timeout != 12)", "+\tif (!state)", "timeout != 12"),
        (p2, "+\tmtk_wdt_recovery_owned = true;", "+\tmtk_wdt_recovery_owned = false;", "mtk_wdt_recovery_owned = true"),
        (p2, "+\tmt_reg_sync_writel(MTK_WDT_RESTART_KEY, MTK_WDT_RESTART);", "+\t/* restart removed */", "missing or unordered 'mt_reg_sync_writel(MTK_WDT_RESTART_KEY'"),
        (p3, "+\tg_enable = 0;", "+\tg_enable = 1;", "g_enable = 0"),
        (p3, "+\tcpu_hotplug_disable();", "+\t/* hotplug exclusion removed */", "cpu_hotplug_disable()"),
        (p3, "+\tret = mtk_wdt_recovery_arm(12, &state);", "+\tret = mtk_wdt_recovery_arm(30, &state);", "ret = mtk_wdt_recovery_arm(12, &state)"),
        (p3, "+\tschedule_delayed_work(&recovery_discriminator_work, 15 * HZ);", "+\tschedule_delayed_work(&recovery_discriminator_work, 0);", "schedule_delayed_work(&recovery_discriminator_work, 15 * HZ)"),
        (p3, "+\t\tpr_emerg(\"gemini-a72-recovery-v1 stage=armed timeout=12s a72=forbidden\\n\");", "+\t\tpr_emerg(\"recovery armed\\n\");", "stage=armed timeout=12s a72=forbidden"),
    ]
    for case in cases:
        expect_rejected(patch_dir, *case)
    print(f"PASS: recovery-only patches and {len(cases)} mutation tripwires")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
