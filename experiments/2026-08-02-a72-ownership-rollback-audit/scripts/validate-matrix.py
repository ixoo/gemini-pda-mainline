#!/usr/bin/env python3
"""Validate the exact Gate 4 A72 ownership/rollback inventory."""

from __future__ import annotations

import csv
from pathlib import Path


MATRIX = Path(__file__).resolve().parents[1] / "results/ownership-matrix.tsv"
FIELDS = (
    "id",
    "boundary",
    "physical_writer",
    "requester",
    "owner_evidence",
    "prestate",
    "readback",
    "rollback",
    "cpu9_delta",
    "resume_owner",
    "decision",
)
EXPECTED_IDS = tuple(f"{number:02d}" for number in range(1, 20))
EVIDENCE = {
    "active-binary",
    "active-source-equivalent",
    "firmware-analysis",
    "known-design",
    "missing",
}
DECISIONS = {
    "closed-forward",
    "excluded-first-cpu8",
    "observer-required",
    "rollback-missing",
    "owner-unresolved",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


with MATRIX.open(newline="") as stream:
    reader = csv.DictReader(stream, delimiter="\t")
    require(tuple(reader.fieldnames or ()) == FIELDS, "matrix schema changed")
    rows = list(reader)

require(tuple(row["id"] for row in rows) == EXPECTED_IDS, "row inventory changed")
require(len({row["boundary"] for row in rows}) == len(rows), "duplicate boundary")
for row in rows:
    require(all(row[field] for field in FIELDS), f"empty field in row {row['id']}")
    require(row["owner_evidence"] in EVIDENCE, f"invalid evidence in row {row['id']}")
    require(row["decision"] in DECISIONS, f"invalid decision in row {row['id']}")
    if row["physical_writer"] == "unresolved" or row["requester"] == "unresolved":
        require(row["decision"] == "owner-unresolved",
                f"unresolved owner is not fail-closed in row {row['id']}")
    if row["rollback"].startswith("unproven") or "unsafe" in row["rollback"]:
        require(row["decision"] in {"rollback-missing", "owner-unresolved"},
                f"missing rollback is not fail-closed in row {row['id']}")

unresolved_owner = sum(row["decision"] == "owner-unresolved" for row in rows)
rollback_missing = sum(row["decision"] == "rollback-missing" for row in rows)
observer_required = sum(row["decision"] == "observer-required" for row in rows)
closed_forward = sum(row["decision"] == "closed-forward" for row in rows)
excluded = sum(row["decision"] == "excluded-first-cpu8" for row in rows)
resume_unresolved = sum(row["resume_owner"] == "unresolved" for row in rows)
prestate_missing = sum(row["prestate"] == "missing-live" for row in rows)
readback_missing = sum(row["readback"] == "missing-live" for row in rows)
require(unresolved_owner > 0, "audit incorrectly claims every owner is resolved")
require(rollback_missing > 0, "audit incorrectly claims complete rollback")
require(observer_required > 0, "audit has no synchronized observation gate")
require(resume_unresolved == len(rows), "resume ownership was silently promoted")

print("validation=a72-ownership-rollback-matrix")
print(f"boundaries={len(rows)}")
print(f"closed_forward={closed_forward}")
print(f"observer_required={observer_required}")
print(f"rollback_missing={rollback_missing}")
print(f"excluded_first_cpu8={excluded}")
print(f"owner_unresolved={unresolved_owner}")
print(f"prestate_missing={prestate_missing}")
print(f"readback_missing={readback_missing}")
print(f"resume_unresolved={resume_unresolved}")
print("gate4=OPEN")
print("next_action=owner-local-synchronized-gemian-observer")
