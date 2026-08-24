#!/usr/bin/env python3
"""Validate the staged A72 physical-source qualification contract."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments/2026-08-24-mainline-a72-physical-source-qualification-contract"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    readme = (EXP / "README.md").read_text()
    design = (EXP / "DESIGN.md").read_text()
    contract = json.loads((EXP / "contract.json").read_text())
    provenance = (EXP / "results/source-contract-20260824.txt").read_text()
    fields = dict(
        line.split("=", 1) for line in provenance.splitlines() if "=" in line
    )
    matrix = [
        line
        for line in (EXP / "results/decision-matrix.tsv").read_text().splitlines()
        if line
    ]
    prior = (
        ROOT
        / "experiments/2026-08-24-mainline-a72-production-input-ownership-audit"
        / "results/source-ownership-audit-20260824.txt"
    ).read_text()
    index = (ROOT / "experiments/README.md").read_text()
    roadmap = (ROOT / "docs/ROADMAP.md").read_text()

    for token in (
        "confirmed-two-phase-contract",
        "positive writable transaction remains uncompiled",
        "no read-only profile",
        "public direct snapshot exactly once",
        "record 1 only",
        "hardware-free DA921x read-only",
        "snapshot separation",
    ):
        require(token in readme, f"README is missing {token!r}")

    for token in (
        "Phase A: read-only DA921x snapshot separation",
        "0x56`, `0x51`, `0x5e`, `0xd9`, `0xda",
        "positive Kconfig guard",
        "Phase B: staged candidate-only physical observer",
        "checkpoint=before-bigidvfs",
        "exactly one two-sample call",
        "Why the clock call is not an unchanged repetition",
    ):
        require(token in design, f"DESIGN is missing {token!r}")

    require(contract["schema"] == 1, "contract schema changed")
    require(
        contract["repository_commit"]
        == "3d7eae1f33cfb8d8837df68ed6317e85c5cbfdba",
        "repository input changed",
    )
    require(
        contract["current_block"]["positive_option_compiles_buckb_writer"],
        "writer coupling must remain explicit",
    )
    require(not contract["phase_a"]["positive_provider_transaction"],
            "Phase A must keep the positive writer off")
    require(not contract["phase_a"]["physical_i2c"],
            "Phase A must remain hardware-free")
    require(contract["phase_b_design"]["retained_slots"] == [1, 2],
            "retained slots changed")
    require(
        contract["phase_b_design"]["retained_checkpoints"]
        == ["before-bigidvfs", "after-bigidvfs"],
        "retained checkpoints changed",
    )
    require(contract["phase_b_design"]["bigidvfs_smc_reads"] == 8,
            "BigiDVFS read ceiling changed")
    require(contract["phase_b_design"]["publisher_calls"] == 0,
            "publisher must remain absent")

    expected_files = {
        "production_input_audit": (
            "experiments/2026-08-24-mainline-a72-production-input-ownership-audit/"
            "results/source-ownership-audit-20260824.txt"
        ),
        "direct_compositor_design": (
            "experiments/2026-08-23-mainline-a72-direct-state-compositor-audit/"
            "DESIGN.md"
        ),
        "protected_clock_runtime": (
            "experiments/2026-08-23-mainline-protected-clock-first-dmesg-call/"
            "results/runtime-attempt-1-pass-20260823.txt"
        ),
        "bigidvfs_firmware_audit": (
            "experiments/2026-08-21-mainline-protected-readback-firmware-audit/"
            "results/audit-20260821.txt"
        ),
    }
    for key, path in expected_files.items():
        evidence = contract["prior_evidence"][key]
        require(evidence["path"] == path,
                f"prior evidence path changed: {key}")
        require((ROOT / path).is_file(), f"prior evidence missing: {path}")
        require(sha256(ROOT / path) == evidence["sha256"],
                f"prior evidence hash mismatch: {key}")

    expected_fields = {
        "provider_snapshot_callback_guard": (
            "REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION"
        ),
        "positive_option_compiles_buckb_writer": "true",
        "read_only_provider_snapshot_available": "false",
        "phase_a_positive_provider_transaction": "false",
        "phase_a_physical_i2c": "false",
        "phase_a_boot_candidate": "false",
        "phase_b_bigidvfs_smc_reads": "8",
        "phase_b_publisher_calls": "0",
        "build": "none",
        "hardware_operation": "none",
        "result": "confirmed-two-phase-contract",
        "selected_next": "hardware-free-da921x-readonly-snapshot-separation",
    }
    for key, value in expected_fields.items():
        require(fields.get(key) == value, f"provenance mismatch for {key}")

    require(
        "provider_snapshot_read_only_profile=false" in prior,
        "production-input audit does not retain the provider correction",
    )
    require(
        "provider_snapshot_writable_transaction_compiled=true" in prior,
        "production-input audit does not retain writer coupling",
    )

    require(len(matrix) == 16, "decision matrix must contain 15 rows plus header")
    require(
        matrix[0] == "id\tboundary\tcurrent_state\trequired_state\tdecision",
        "decision matrix header changed",
    )
    require(sum("missing-block" in row for row in matrix[1:]) == 1,
            "decision matrix missing-block count changed")
    require(matrix[-2].endswith("\tstop"),
            "Phase-A boot candidate must remain stopped")
    require(matrix[-1].endswith("\tdeferred"),
            "Phase-B device attempt must remain deferred")

    link = "2026-08-24-mainline-a72-physical-source-qualification-contract/README.md"
    require(link in index, "experiment index link is missing")
    require("physical-source qualification contract" in roadmap,
            "Roadmap does not name this contract")
    require("DA921x read-only snapshot" in roadmap,
            "Roadmap does not name the selected source slice")
    require("positive writable provider option" in roadmap,
            "Roadmap does not keep the writer closed")

    print("A72 physical-source qualification contract validation passed")


if __name__ == "__main__":
    main()
