#!/usr/bin/env python3
"""Validate the Gate-7 remaining-boundary audit."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    contract = json.loads((HERE / "contract.json").read_text())
    require(contract["schema"] == 1, "contract schema")
    require(contract["selected_boundary"] == "A34_ELIGIBILITY_EVALUATOR",
            "selected boundary")

    scope = contract["implementation_scope"]
    expected_true = {"default_off", "hardware_free", "injected_evaluator",
                     "reset_provenance_input_required",
                     "private_replay_input_required"}
    expected_false = {"production_init_caller", "opens_owner",
                      "transaction_caller", "cpu_on", "cpu_off",
                      "provider_call", "p27_or_p28_effect", "device_action"}
    require(all(scope[name] is True for name in expected_true),
            "positive scope flags")
    require(all(scope[name] is False for name in expected_false),
            "negative scope flags")

    series_lines = (ROOT / "patches/series").read_bytes().splitlines(keepends=True)
    prefix = contract["canonical_prefix"]
    count = prefix["entry_count"]
    require(len(series_lines) >= count, "canonical series prefix length")
    prefix_bytes = b"".join(series_lines[:count])
    require(hashlib.sha256(prefix_bytes).hexdigest() == prefix["sha256"],
            "canonical series prefix identity")
    require(series_lines[count - 1].decode().strip() == prefix["last_entry"],
            "canonical series prefix endpoint")

    for relative, expected in contract["pinned_inputs"].items():
        path = ROOT / relative
        require(path.is_file(), f"pinned input exists: {relative}")
        require(sha256(path) == expected, f"pinned input identity: {relative}")

    with (HERE / "results/remaining-boundary-matrix.tsv").open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    require([row["id"] for row in rows] ==
            ["B01", "B02", "B03", "B04", "B05", "B06"],
            "matrix row identity and order")
    selected = [row for row in rows if row["decision"] == "selected"]
    require(len(selected) == 1 and selected[0]["id"] == "B01",
            "single selected matrix boundary")
    require(all(row["decision"] == "defer" for row in rows[1:]),
            "all downstream boundaries deferred")
    require(selected[0]["hardware_effect"] == "none",
            "selected boundary is hardware-free")

    readme = (HERE / "README.md").read_text()
    design = (HERE / "DESIGN.md").read_text()
    for marker in (
        "hardware-free A34 eligibility evaluator next",
        "no physical write",
        "cannot supply A34 reset provenance by itself",
        "does not include the future transaction caller",
    ):
        require(marker in readme, f"README marker: {marker}")
    for marker in (
        "performs no state\ntransition",
        "does not initialize attempts",
        "adds no production init caller",
    ):
        require(marker in design, f"design marker: {marker}")

    print("experiment=2026-08-20-mainline-cpu8-gate7-remaining-boundary-audit")
    print("canonical_prefix_entries=293")
    print("selected_boundary=A34_ELIGIBILITY_EVALUATOR")
    print("independent_hardware_free=yes")
    print("transaction_caller=no")
    print("cpu_on=no")
    print("device_action=no")
    print("result=pass")


if __name__ == "__main__":
    main()
