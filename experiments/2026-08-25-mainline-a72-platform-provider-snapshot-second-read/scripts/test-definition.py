#!/usr/bin/env python3
"""Require the frozen-definition validator to reject meaningful mutations."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


EXPERIMENT = "2026-08-25-mainline-a72-platform-provider-snapshot-second-read"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"fixture anchor changed: {path}: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    repository = Path(__file__).resolve().parents[3]
    validator_relative = Path("experiments") / EXPERIMENT / "scripts/validate-definition.py"
    mutations = (
        ("contract-parent", "contract.json", "a2affef6", "b2affef6"),
        ("record-crc", "contract.json", "0150f9c7", "1150f9c7"),
        (
            "call-order",
            "source/mt6797-a72-platform-provider-snapshot-observer.c",
            "ops->checkpoint(context, 0)",
            "ops->checkpoint(context, 1)",
        ),
        ("cpu-gate", "contract.json", '"maxcpus": 8', '"maxcpus": 9'),
        (
            "later-reader",
            "source/mt6797-a72-platform-provider-snapshot-observer.c",
            "return mt6797_a72_provider_snapshot(snapshot);",
            "mt6797_dvfsp_clock_backend_read(NULL, NULL);\n\treturn mt6797_a72_provider_snapshot(snapshot);",
        ),
        (
            "patch-name",
            "contract.json",
            "0370-soc-mediatek-test-A72-platform-provider-snapshot-observer.patch",
            "0371-soc-mediatek-test-A72-platform-provider-snapshot-observer.patch",
        ),
        (
            "kunit-case",
            "source/mt6797-a72-platform-provider-snapshot-observer-test.c",
            "\tKUNIT_CASE(mt6797_platform_provider_after_failure_test),\n",
            "",
        ),
        (
            "buildbox-dispatch",
            "../../scripts/buildbox",
            "  generate-a72-platform-provider-patches) generate_a72_platform_provider_patches ;;",
            "  generate-a72-platform-provider-broken) generate_a72_platform_provider_patches ;;",
        ),
    )
    rejected = 0
    for name, relative, old, new in mutations:
        with tempfile.TemporaryDirectory(prefix="a72-platform-provider-definition-") as temp:
            root = Path(temp)
            destination = root / "experiments" / EXPERIMENT
            destination.parent.mkdir(parents=True)
            shutil.copytree(repository / "experiments" / EXPERIMENT, destination)
            (root / "scripts").mkdir()
            shutil.copy2(repository / "scripts/buildbox", root / "scripts/buildbox")
            patch = repository / "patches/v7.1.3/0366-soc-mediatek-test-A72-platform-snapshot-observer.patch"
            patch_destination = root / "patches/v7.1.3"
            patch_destination.mkdir(parents=True)
            shutil.copy2(patch, patch_destination / patch.name)
            target = destination / relative
            replace_once(target.resolve(), old, new)
            result = subprocess.run(
                [
                    "python3",
                    str(root / validator_relative),
                    "--repository-root",
                    str(root),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode == 0:
                raise SystemExit(f"FAIL: accepted mutation: {name}")
            rejected += 1
    print(f"definition_rejected_mutations={rejected}")
    print("result=pass")


if __name__ == "__main__":
    main()
