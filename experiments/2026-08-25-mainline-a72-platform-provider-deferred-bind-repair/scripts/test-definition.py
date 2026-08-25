#!/usr/bin/env python3
"""Require the repair-definition validator to reject meaningful mutations."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


EXPERIMENT = "2026-08-25-mainline-a72-platform-provider-deferred-bind-repair"
PREDECESSOR = "2026-08-25-mainline-a72-platform-provider-snapshot-second-read"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"fixture anchor changed: {path}: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def make_fixture(repository: Path, root: Path) -> None:
    exp_root = root / "experiments"
    exp_root.mkdir(parents=True)
    shutil.copytree(repository / "experiments" / EXPERIMENT, exp_root / EXPERIMENT)
    predecessor = exp_root / PREDECESSOR
    predecessor.mkdir()
    shutil.copytree(
        repository / "experiments" / PREDECESSOR / "source",
        predecessor / "source",
    )
    (root / "scripts").mkdir()
    shutil.copy2(repository / "scripts/buildbox", root / "scripts/buildbox")
    (root / "kernel").mkdir()
    shutil.copy2(repository / "kernel/manifest.json", root / "kernel/manifest.json")
    shutil.copytree(repository / "configs", root / "configs")
    patch_root = root / "patches/v7.1.3"
    patch_root.mkdir(parents=True)
    patch = repository / "patches/v7.1.3/0370-soc-mediatek-test-A72-platform-provider-snapshot-observer.patch"
    shutil.copy2(patch, patch_root / patch.name)


def main() -> None:
    repository = Path(__file__).resolve().parents[3]
    validator = Path("experiments") / EXPERIMENT / "scripts/validate-definition.py"
    mutations = (
        ("parent-hash", f"experiments/{EXPERIMENT}/contract.json", "53acfdd3", "63acfdd3"),
        ("cpu-gate", f"experiments/{EXPERIMENT}/contract.json", '"maxcpus": 8', '"maxcpus": 9'),
        ("read-ceiling", f"experiments/{EXPERIMENT}/contract.json", '"provider_i2c_reads": 10', '"provider_i2c_reads": 11'),
        ("gate-result", f"experiments/{EXPERIMENT}/contract.json", '"not_ready_result": "-EPROBE_DEFER"', '"not_ready_result": "-ENODEV"'),
        ("source-gate", f"experiments/{EXPERIMENT}/scripts/source_edits.py", '"\\tif (!provider)\\n"', '"\\tif (!platform)\\n"'),
        ("patch-name", f"experiments/{EXPERIMENT}/contract.json", "0373-soc-mediatek-test-A72-platform-provider-readiness.patch", "0374-soc-mediatek-test-A72-platform-provider-readiness.patch"),
        ("profile-name", f"experiments/{EXPERIMENT}/contract.json", '"a72-platform-provider-ready-kunit"', '"a72-platform-provider-broken-kunit"'),
        ("localversion", "configs/gemini-a72-platform-provider-ready-candidate.fragment", 'CONFIG_LOCALVERSION="-gemini-a72-provider-ready"', 'CONFIG_LOCALVERSION="-gemini-a72-provider-broken"'),
        ("kunit-plan", f"experiments/{EXPERIMENT}/scripts/classify-kunit.py", '"1..7"', '"1..8"'),
        ("candidate-dtb", f"experiments/{EXPERIMENT}/contract.json", "923575e4e25498f2", "823575e4e25498f2"),
        ("buildbox-dispatch", "scripts/buildbox", "  generate-a72-platform-provider-ready-patches) generate_a72_platform_provider_ready_patches ;;", "  generate-a72-platform-provider-broken-patches) generate_a72_platform_provider_ready_patches ;;"),
    )
    rejected = 0
    for name, relative, old, new in mutations:
        with tempfile.TemporaryDirectory(prefix="a72-provider-ready-definition-") as temp:
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
    print(f"definition_rejected_mutations={rejected}")
    print("result=pass")


if __name__ == "__main__":
    main()
