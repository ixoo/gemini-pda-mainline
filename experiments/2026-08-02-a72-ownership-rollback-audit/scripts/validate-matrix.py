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
    "latched-first-pair",
    "missing",
    "retained-live-observer",
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
    if row["decision"] == "rollback-missing":
        require("unproven" in row["rollback"] or "failure-" in row["rollback"],
                f"rollback-missing row lacks an explicit open boundary in row {row['id']}")
    if row["owner_evidence"] in {"latched-first-pair", "retained-live-observer"}:
        require(row["prestate"] != "missing-live" and
                row["readback"] != "missing-live",
                f"retained live evidence leaves a live field missing in row {row['id']}")

unresolved_owner = sum(row["decision"] == "owner-unresolved" for row in rows)
rollback_missing = sum(row["decision"] == "rollback-missing" for row in rows)
observer_required = sum(row["decision"] == "observer-required" for row in rows)
closed_forward = sum(row["decision"] == "closed-forward" for row in rows)
excluded = sum(row["decision"] == "excluded-first-cpu8" for row in rows)
resume_unresolved = sum(row["resume_owner"] == "unresolved" for row in rows)
prestate_missing = sum(row["prestate"] == "missing-live" for row in rows)
readback_missing = sum(row["readback"] == "missing-live" for row in rows)
retained_live = sum(row["owner_evidence"] == "retained-live-observer" for row in rows)
latched_first_pair = sum(row["owner_evidence"] == "latched-first-pair" for row in rows)
require((closed_forward, observer_required, rollback_missing, excluded,
         unresolved_owner) == (9, 1, 5, 3, 1),
        "post-observer decision counts changed")
require((prestate_missing, readback_missing, retained_live, latched_first_pair) ==
        (2, 2, 0, 16),
        "post-observer evidence counts changed")
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
print(f"retained_live_observer={retained_live}")
print(f"latched_first_pair={latched_first_pair}")
print(f"resume_unresolved={resume_unresolved}")
print("gate4=OPEN")
print("next_action=failure-rollback-discriminator-plus-cpu9-and-resume-audits")
