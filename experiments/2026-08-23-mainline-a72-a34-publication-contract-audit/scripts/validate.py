#!/usr/bin/env python3
"""Validate the frozen A34 publication-contract audit."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "experiments/2026-08-23-mainline-a72-a34-publication-contract-audit"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    readme = (EXP / "README.md").read_text()
    design = (EXP / "DESIGN.md").read_text()
    provenance = (EXP / "results/source-audit-20260824.txt").read_text()
    matrix = [
        line
        for line in (EXP / "results/decision-matrix.tsv").read_text().splitlines()
        if line
    ]
    index = (ROOT / "experiments/README.md").read_text()
    roadmap = (ROOT / "docs/ROADMAP.md").read_text()

    for token in (
        "rejected-current-input",
        "structural `valid=1`",
        "current-boot",
        "secure replay",
        "P30",
        "both CPU vetoes",
        "no production callers",
    ):
        require(token in readme, f"README is missing {token!r}")

    for token in (
        "direct.source.valid == 1",
        "CPU hotplug read lock",
        "bootstrap",
        "interlock",
        "health = AVAILABLE",
        "No physical source registration",
    ):
        require(token in design, f"DESIGN is missing {token!r}")

    expected_provenance = {
        "repository_input": "5176ebf418c331a2e8aefba7aaafcabfc3234f8c",
        "prepared_source_state": "c020a36a674ca8ac6516f022649f143cd1d1d8834f17e5de758bc3fe0268c72e",
        "a34_production_callers": "0",
        "direct_state_production_callers": "0",
        "p30_prepare_production_callers": "0",
        "publication": "none",
        "decision": "rejected-current-input",
    }
    fields = dict(line.split("=", 1) for line in provenance.splitlines() if "=" in line)
    for key, value in expected_provenance.items():
        require(fields.get(key) == value, f"provenance mismatch for {key}")

    require(len(matrix) == 15, "decision matrix must contain 14 rows plus header")
    require(matrix[0] == "id\tboundary\tcanonical_state\tpublication_requirement\tdecision",
            "decision matrix header changed")
    require(sum("missing-block" in row for row in matrix[1:]) == 5,
            "decision matrix missing-block count changed")
    require(matrix[-1].endswith("\tstop"), "production publication must remain stopped")

    link = "2026-08-23-mainline-a72-a34-publication-contract-audit/README.md"
    require(link in index, "experiment index link is missing")
    require("A34 publication contract audit" in roadmap,
            "roadmap does not name the publication contract audit")
    require("Direct-state `valid=1` is structural" in roadmap,
            "roadmap does not retain the structural-validity blocker")
    require("A34-v2 evaluator and P30 bootstrap interlock" in roadmap,
            "roadmap does not name the selected next slice")

    print("A34 publication-contract audit validation passed")


if __name__ == "__main__":
    main()
