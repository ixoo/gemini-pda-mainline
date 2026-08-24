#!/usr/bin/env python3
"""Validate the frozen A72 production-input ownership audit."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments/2026-08-24-mainline-a72-production-input-ownership-audit"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    readme = (EXP / "README.md").read_text()
    design = (EXP / "DESIGN.md").read_text()
    contract = json.loads((EXP / "contract.json").read_text())
    provenance = (EXP / "results/source-ownership-audit-20260824.txt").read_text()
    fields = dict(
        line.split("=", 1) for line in provenance.splitlines() if "=" in line
    )
    matrix = [
        line
        for line in (EXP / "results/decision-matrix.tsv").read_text().splitlines()
        if line
    ]
    index = (ROOT / "experiments/README.md").read_text()
    roadmap = (ROOT / "docs/ROADMAP.md").read_text()

    for token in (
        "rejected-current-production-inputs",
        "blocked-no-current-boot-primary-bl31-applicability-owner",
        "no production registration",
        "17 of its 18 raw",
        "no named-device mainline runtime sample",
        "no production publisher caller",
    ):
        require(token in readme, f"README is missing {token!r}")

    for token in (
        "Two-authority boundary",
        "Initialization and lifetime",
        "cpu_hotplug_lock (read)",
        "platform-state source mutex",
        "Rejected replay substitutes",
        "Selected next experiment contract",
        "This audit adds no source adapter",
    ):
        require(token in design, f"DESIGN is missing {token!r}")

    require(contract["schema"] == 1, "contract schema changed")
    require(
        contract["repository_commit"]
        == "84325e329b4c2605071c9704a2e49572121077fd",
        "repository input changed",
    )
    require(
        sha256(ROOT / contract["canonical_tail"])
        == contract["canonical_tail_sha256"],
        "canonical tail hash mismatch",
    )
    require(
        sha256(ROOT / "patches/series") == contract["canonical_series_sha256"],
        "canonical series hash mismatch",
    )
    for evidence in contract["prior_evidence"].values():
        require(
            sha256(ROOT / evidence["path"]) == evidence["sha256"],
            f"prior evidence hash mismatch: {evidence['path']}",
        )

    expected_fields = {
        "prepared_source_state": contract["prepared_source_state"],
        "prepared_source_integrity": contract["prepared_source_integrity"],
        "direct_source_register_production_call_sites": "0",
        "bootstrap_publisher_production_call_sites": "0",
        "positive_replay_production_producers": "0",
        "qualified_clock_raw_nonzero_words": "17-of-18",
        "qualified_clock_matches_expected": "false",
        "publication": "stopped",
        "boot_candidate": "false",
        "hardware_operation": "none",
        "decision": "rejected-current-production-inputs",
        "selected_next": "offline-staged-physical-source-qualification-contract",
    }
    for key, value in expected_fields.items():
        require(fields.get(key) == value, f"provenance mismatch for {key}")

    require(len(matrix) == 16, "decision matrix must contain 15 rows plus header")
    require(
        matrix[0]
        == "id\tauthority\tcanonical_input\trequired_positive\tdecision",
        "decision matrix header changed",
    )
    require(sum("missing-block" in row for row in matrix[1:]) == 5,
            "decision matrix missing-block count changed")
    require(sum("mismatch-block" in row for row in matrix[1:]) == 1,
            "decision matrix mismatch-block count changed")
    require(matrix[-1].endswith("\tstop"),
            "production publication must remain stopped")

    link = "2026-08-24-mainline-a72-production-input-ownership-audit/README.md"
    require(link in index, "experiment index link is missing")
    require("production-input ownership audit" in roadmap,
            "Roadmap does not name this audit")
    require("static zero protected-clock vector contradicts" in roadmap,
            "Roadmap does not retain the clock mismatch")
    require("staged physical-source qualification" in roadmap,
            "Roadmap does not name the selected next contract")

    print("A72 production-input ownership audit validation passed")


if __name__ == "__main__":
    main()
