#!/usr/bin/env python3
"""Require the third-reader definition validator to reject unsafe mutations."""

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
    patch_root = root / "patches/v7.1.3"
    patch_root.mkdir(parents=True)
    patch = repository / (
        "patches/v7.1.3/"
        "0373-soc-mediatek-test-A72-platform-provider-readiness.patch"
    )
    shutil.copy2(patch, patch_root / patch.name)


def main() -> None:
    repository = Path(__file__).resolve().parents[3]
    validator = Path("experiments") / EXPERIMENT / "scripts/validate-definition.py"
    contract = f"experiments/{EXPERIMENT}/contract.json"
    readme = f"experiments/{EXPERIMENT}/README.md"
    design = f"experiments/{EXPERIMENT}/DESIGN.md"
    audit = (
        f"experiments/{EXPERIMENT}/results/"
        "prebuild-source-audit-20260825.txt"
    )
    mutations = (
        ("parent-hash", contract, "de668030d4dc0fbf", "ce668030d4dc0fbf"),
        ("clock-order", contract, '"retained-before-clock",', '"protected-clock-call",'),
        ("record-crc", contract, '"crc32": "7a63713c"', '"crc32": "6a63713c"'),
        ("retained-ceiling", contract, '"retained_write_attempts_maximum": 2', '"retained_write_attempts_maximum": 3'),
        ("clock-calls", contract, '"backend_calls": 1', '"backend_calls": 2'),
        ("clock-pair", contract, '"balanced_i2c_clock_enable_disable_pairs": 1', '"balanced_i2c_clock_enable_disable_pairs": 2'),
        ("write-ceiling", contract, '"explicit_mmio_writes_maximum": 401', '"explicit_mmio_writes_maximum": 400'),
        ("read-ceiling", contract, '"explicit_mmio_reads_maximum": 419', '"explicit_mmio_reads_maximum": 418'),
        ("cpu-gate", contract, '"maxcpus": 8', '"maxcpus": 9'),
        ("bigidvfs", contract, '"bigidvfs_call": false', '"bigidvfs_call": true'),
        ("retry-rule", contract, '"probe_returns_success_after_clock_call_returns": true', '"probe_returns_success_after_clock_call_returns": false'),
        ("candidate-sha", contract, '"padded_sha256": "1f7bd9600e11846a', '"padded_sha256": "0f7bd9600e11846a'),
        ("deployment-state", contract, '"deployment": "write-verified-and-shut-down"', '"deployment": "installed-unverified"'),
        ("runtime-probe", contract, '"remote_probe_sha256": "cd5f30e02a2d93b5', '"remote_probe_sha256": "dd5f30e02a2d93b5'),
        ("runtime-branches", contract, '"accepted_decision_branches": 4', '"accepted_decision_branches": 3'),
        ("runtime-mutations", contract, '"rejected_mutations": 19', '"rejected_mutations": 18'),
        ("safety-wording", readme, "deliberately not hardware-read-only", "hardware-read-only"),
        ("retained-wording", design, "Maximum retained write attempts are two", "Maximum retained write attempts are three"),
        ("audit-state", audit, "prepared_source_state=c5bc1470", "prepared_source_state=d5bc1470"),
    )
    rejected = 0
    for name, relative, old, new in mutations:
        with tempfile.TemporaryDirectory(prefix="a72-third-reader-definition-") as temp:
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
