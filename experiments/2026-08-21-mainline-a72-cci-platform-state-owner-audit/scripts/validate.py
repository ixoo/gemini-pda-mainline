#!/usr/bin/env python3
"""Validate the frozen MT6797 A72 CCI/platform ownership audit."""

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

    for token in (
        "capture-only source selected",
        "`0x10396000`",
        "global `0x1039000c` bit 0",
        "do **not** poll",
        "`0x1039600c`. The earlier EF24",
        "intersection of the two words",
        "reset_control_status()",
        "A34, lifecycle publication, CPU8/CPU9 requests",
    ):
        require(token in readme, f"README token: {token}")

    for token in (
        "named `mcucfg` and `cci` resources",
        "zeroes the destination on every failure",
        "not poll, retry, write",
        "PWRAP state comes only from `reset_control_status()`",
        "must hold the A72 transition/hotplug owner",
    ):
        require(token in design, f"design token: {token}")

    with (HERE / "results/ownership-matrix.tsv").open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    require([row["id"] for row in rows] == [
        "O01", "O02", "O03", "O04", "O05", "O06",
        "O07", "O08", "O09", "O10", "O11", "O12",
    ], "ownership matrix identities")
    by_id = {row["id"]: row for row in rows}
    require(by_id["O02"]["address_or_api"] == "0x10396000",
            "MP2 port address")
    require(by_id["O03"]["address_or_api"] == "0x1039000c" and
            by_id["O03"]["decision"] == "capture-no-poll",
            "global CCI status address")
    require(by_id["O04"]["decision"] == "reject-as-owner",
            "generic CCI rejection")
    require(by_id["O11"]["safe_read"] == "locked-status-callback",
            "TOPRGU owner accessor")
    require(all("writel" not in row["safe_read"] for row in rows),
            "MMIO write path invented")

    for token in (
        "repository_input=a72e9032c3be9d329cb28d7bee491547d5396599",
        "cci_mp2_port_control=0x10396000",
        "cci_global_status=0x1039000c",
        "corrected_rejected_address=0x1039600c",
        "generic_arm_cci_owner=reject-missing-MP2-port-and-read-getter",
        "selected_next=default-off-capture-only-platform-state-source",
        "device_write=none",
    ):
        require(token in provenance, f"provenance token: {token}")

    prior = ROOT / "experiments/2026-08-05-a72-secure-cpu-off-attribution"
    effects = (prior / "results/effect-inventory.tsv").read_text()
    prior_readme = (prior / "README.md").read_text()
    require("EF24\tlast-a72-off\t12\tpower_off_cl3\t0x1027b4-0x1027c4\t0x1039000c" in effects,
            "corrected EF24 target")
    require("2026-08-21 correction" in prior_readme,
            "explicit prior-audit correction")

    roadmap = (ROOT / "docs/ROADMAP.md").read_text()
    index = (ROOT / "experiments/README.md").read_text()
    hardware = (ROOT / "docs/hardware/mt6797-live-resource-map.md").read_text()
    require("A72 CCI and platform-state ownership audit" in roadmap,
            "roadmap boundary")
    require("A72 CCI and platform-state owner audit" in index,
            "experiment index")
    require("0x10396000" in hardware and "0x1039000c" in hardware,
            "durable CCI result")

    print("audit=pass")
    print("ownership_rows=12")
    print("cci_mp2_port=0x10396000")
    print("cci_global_status=0x1039000c")
    print("generic_arm_cci_owner=rejected")
    print("selected_next=default-off-capture-only-platform-state-source")
    print("a34_owner=closed")
    print("device_write=none")


if __name__ == "__main__":
    main()
