#!/usr/bin/env python3
"""Validate exact generation, evidence, scope, and mutations for patch 0524."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import subprocess
import tempfile
from pathlib import Path


PATCH = "patches/v7.1.3/0524-pstore-match-Gemini-thermal-ledger-after-LK-model-rewrite.patch"
SERIES_ENTRY = "v7.1.3/0524-pstore-match-Gemini-thermal-ledger-after-LK-model-rewrite.patch"
PATCH_SHA256 = "c99d16ced8952df6c8c6eefa27304e9bfe6e3685bef6f3e554f58fa79a022e03"
EVIDENCE = "experiments/2026-09-04-mt6797-thermal-serviceability-dt-repair/results/runtime-attempt-1-live-ledger-model-rejection-20260904.txt"
EVIDENCE_SHA256 = "012fa2ec367424da240359a34b82f3285f289eb91b07499e3b7d213440bb1a0c"
GENERATOR = "experiments/2026-09-04-mt6797-thermal-ledger-live-model-repair/scripts/generate_patch.py"
TARGET = "fs/pstore/gemini_mt6797_thermal_ledger.c"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_generator(path: Path):
    spec = importlib.util.spec_from_file_location("thermal_model_generator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=Path)
    args = parser.parse_args()
    repository = args.repository.resolve(strict=True)
    patch_path = repository / PATCH
    evidence_path = repository / EVIDENCE
    generator_path = repository / GENERATOR
    require(digest(patch_path) == PATCH_SHA256, "successor patch identity changed")
    require(digest(evidence_path) == EVIDENCE_SHA256, "runtime evidence identity changed")
    evidence = evidence_path.read_text()
    for token in (
        "live_dt_model=MT6797X",
        "thermal_probe_retry=refused-errno-19-ENODEV-after-calibration-provider",
        "thermal_mmio_transaction_executed=no",
        "post_cycle_boot2_match=yes",
        "decision=repair only the diagnostic ledger live-model predicate",
    ):
        require(token in evidence, f"runtime evidence lost token: {token}")

    with tempfile.TemporaryDirectory(prefix="thermal-model-validation-") as temporary:
        generated = Path(temporary) / "0524.patch"
        module = load_generator(generator_path)
        module.run(repository, generated)
        require(generated.read_bytes() == patch_path.read_bytes(), "patch generation is not byte-identical")

    patch = patch_path.read_text()
    require(patch.count(f"diff --git a/{TARGET} b/{TARGET}") == 1, "changed-path boundary")
    require(patch.count("diff --git ") == 1, "multiple changed paths")
    require(patch.count("Planet Computers Gemini PDA (thermal serviceability)") == 1, "old predicate boundary")
    require(patch.count('strcmp(model, "MT6797X")') == 1, "new predicate boundary")
    for token in (
        'of_machine_is_compatible("planet,gemini-pda")',
        'of_property_read_string(of_root, "model", &model)',
        "/reserved-memory/ramoops@44410000",
    ):
        require(token in patch, f"preserved gate context absent: {token}")
    require("Signed-off-by: Gemini Mainline Experiment" not in patch, "synthetic sign-off")
    require("artifacts/" not in patch and "/Users/" not in patch and "/workspace/" not in patch, "private path")
    series = (repository / "patches/series").read_text().splitlines()
    require(series[-1] == SERIES_ENTRY, "patch is not the canonical terminal successor")
    require(series.count(SERIES_ENTRY) == 1, "patch appears more than once")

    mutations = (
        patch.replace('strcmp(model, "MT6797X")', 'strcmp(model, "Planet Computers Gemini PDA")'),
        patch.replace('of_machine_is_compatible("planet,gemini-pda")', 'of_machine_is_compatible("mediatek,mt6797")'),
        patch.replace(" 1 file changed, 1 insertion(+), 2 deletions(-)", " 2 files changed, 1 insertion(+), 2 deletions(-)"),
    )
    rejected = 0
    for candidate in mutations:
        try:
            require(candidate.count(f"diff --git a/{TARGET} b/{TARGET}") == 1, "mutation path")
            require(candidate.count('strcmp(model, "MT6797X")') == 1, "mutation live model")
            require(candidate.count('of_machine_is_compatible("planet,gemini-pda")') == 1, "mutation compatible")
            require(" 1 file changed, 1 insertion(+), 2 deletions(-)" in candidate, "mutation stat")
        except ValueError:
            rejected += 1
        else:
            raise ValueError("unsafe mutation accepted")

    subprocess.run([repository / "scripts/validate-manifest-series"], check=True)
    print("validation=mt6797-thermal-ledger-live-model-repair")
    print("patch_generation=byte-identical")
    print("changed_paths=1")
    print("changed_predicates=1")
    print(f"mutation_rejections={rejected}")
    print("manifest_series_invariant=passed")
    print("hardware_action=none")
    print("boot_candidate=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
