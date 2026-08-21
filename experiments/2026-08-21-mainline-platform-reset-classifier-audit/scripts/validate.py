#!/usr/bin/env python3
"""Validate the frozen platform-reset classifier audit."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def main() -> None:
    readme = (HERE / "README.md").read_text()
    design = (HERE / "DESIGN.md").read_text()
    provenance = (HERE / "results/provenance-20260821.txt").read_text()
    runtime = (HERE / "results/runtime-probe-20260821.txt").read_text()

    for token in (
        "no positive classifier is transportable to Linux",
        "lossy semantic projection",
        "class `4`",
        "not transported",
        "must not be repeated",
        "direct, immutable A34 recovery-state attestation",
    ):
        require(token in readme, f"README token: {token}")

    for token in (
        "A strict classifier over only these inputs has no positive row",
        "permanent no-access boundary",
        "direct A34 recovery-state attestation",
        "Any unobservable, non-owner-safe, mutable,",
    ):
        require(token in design, f"design token: {token}")

    with (HERE / "results/classifier-matrix.tsv").open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    require([row["id"] for row in rows] == [
        "C01", "C02", "C03", "C04", "C05",
        "T01", "T02", "T03", "T04", "N01",
    ], "classifier matrix identity")
    require(all(row["decision"].startswith("reject")
                for row in rows[:-1]), "all current paths reject")
    require(rows[-1]["decision"] == "select-audit",
            "direct recovery-state audit selected")

    for token in (
        "repository_input=a313a85b05095dcba811f580d4354f995064637f",
        "preloader_wdt_initializer_analysis=0x21d560",
        "preloader_power_class_global_analysis=0x23d3bc",
        "preloader_power_on_predicate=raw-status-zero-and-entry-interval-low2-equals-3",
        "implemented_snapshot_positive_classifier=none",
        "selected_next_boundary=direct-A34-recovery-state-attestation-audit",
    ):
        require(token in provenance, f"provenance token: {token}")

    for token in (
        "probe_result=no-value;access-did-not-return",
        "automatic_recovery_observed=no",
        "repeat_same_probe=forbidden",
        "device_write=none",
    ):
        require(token in runtime, f"runtime token: {token}")

    roadmap = (ROOT / "docs/ROADMAP.md").read_text()
    index = (ROOT / "experiments/README.md").read_text()
    hardware = (ROOT / "docs/hardware/mt6797-live-resource-map.md").read_text()
    require("platform-reset classifier audit" in roadmap,
            "roadmap link")
    require("mainline platform-reset classifier audit" in index,
            "experiment index link")
    require("entry-time `INTERVAL`" in hardware and
            "not safely readable from Linux" in hardware,
            "durable hardware result")

    print("audit=pass")
    print("classifier_rows=10")
    print("current_snapshot_positive_rows=0")
    print("preloader_power_on_class=source-confirmed-but-not-transported")
    print("direct_preloader_cell=reject-no-repeat")
    print("next=direct-A34-recovery-state-attestation-audit")
    print("a34_owner=closed")
    print("device_write=none")


if __name__ == "__main__":
    main()
