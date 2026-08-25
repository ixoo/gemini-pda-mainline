#!/usr/bin/env python3
"""Require the third-reader tooling validator to reject unsafe mutations."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


EXPERIMENT = "2026-08-25-mainline-a72-platform-provider-protected-clock-third-read"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"fixture anchor changed: {path}: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def make_fixture(repository: Path, root: Path) -> None:
    target = root / "experiments" / EXPERIMENT
    target.parent.mkdir(parents=True)
    shutil.copytree(repository / "experiments" / EXPERIMENT, target)
    (root / "scripts").mkdir()
    shutil.copy2(repository / "scripts/buildbox", root / "scripts/buildbox")
    (root / "docs").mkdir()
    shutil.copy2(repository / "docs/BUILDBOX.md", root / "docs/BUILDBOX.md")


def main() -> None:
    repository = Path(__file__).resolve().parents[3]
    validator = Path("experiments") / EXPERIMENT / "scripts/validate-tooling.py"
    exp = f"experiments/{EXPERIMENT}"
    generator = f"{exp}/scripts/generate-on-buildbox"
    edits = f"{exp}/scripts/source_edits.py"
    observer = f"{exp}/source/mt6797-a72-platform-provider-clock-observer.c"
    tests = f"{exp}/source/mt6797-a72-platform-provider-clock-observer-test.c"
    source_validator = f"{exp}/scripts/validate_source.py"
    mutations = (
        ("source-state", generator, "PARENT_SOURCE_STATE=c5bc1470", "PARENT_SOURCE_STATE=d5bc1470"),
        ("patch-count", generator, "generated_patch_count=4", "generated_patch_count=5"),
        ("retry", generator, "protected_clock_caller_retries=0", "protected_clock_caller_retries=1"),
        ("write-ceiling", generator, "explicit_mmio_writes_maximum=401", "explicit_mmio_writes_maximum=402"),
        ("clock-call", observer, "ops->clock(context, clock, &snapshot->clock)", "ops->clock(context, clock, &snapshot->clock) + ops->clock(context, clock, &snapshot->clock)"),
        ("clock-terminal", observer, "A returned hardware call is terminal", "A returned hardware call may retry"),
        ("style-open", observer, "static int mt6797_a72_ppc_platform(void *context, struct device *dev,", "static int mt6797_a72_ppc_platform(\n\tvoid *context, struct device *dev,"),
        ("kconfig-cycle", edits, 'mode + "config PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER\\n",', 'mode + "config PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER\\n" "\\tdepends on !PSTORE_GEMINI_A72_PLATFORM_PROVIDER_CLOCK_LEDGER\\n",'),
        ("helper-endpoint", source_validator, '("get_platform", "static struct device *mt6797_a72_ppc_get_provider",', '("get_platform", "static struct device *mt6797_a72_ppc_get_platform",'),
        ("kunit-count", tests, "KUNIT_CASE(mt6797_a72_ppc_clock_identity_terminal_test)", "mt6797_a72_ppc_clock_identity_terminal_test"),
        ("generate-dispatch", "scripts/buildbox", "  generate-a72-platform-provider-clock-patches) generate_a72_platform_provider_clock_patches ;;", "  generate-a72-platform-provider-clock-broken) generate_a72_platform_provider_clock_patches ;;"),
        ("fetch-purpose", "scripts/buildbox", ".purpose == \"mainline-a72-platform-provider-clock-patch-generation\" and", ".purpose == \"mainline-a72-platform-provider-broken\" and"),
        ("docs", "docs/BUILDBOX.md", "terminal no-retry behavior", "retry behavior"),
    )
    rejected = 0
    for name, relative, old, new in mutations:
        with tempfile.TemporaryDirectory(prefix="a72-third-reader-tooling-") as temp:
            root = Path(temp)
            make_fixture(repository, root)
            replace_once(root / relative, old, new)
            result = subprocess.run(
                ["python3", str(root / validator), "--repository-root", str(root)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode == 0:
                raise SystemExit(f"FAIL: accepted mutation: {name}")
            rejected += 1
    print(f"tooling_rejected_mutations={rejected}")
    print("result=pass")


if __name__ == "__main__":
    main()
