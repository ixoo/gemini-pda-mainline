#!/usr/bin/env python3
"""Validate the frozen direct A34 recovery-state audit."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    readme = (HERE / "README.md").read_text()
    design = (HERE / "DESIGN.md").read_text()
    provenance = (HERE / "results/provenance-20260821.txt").read_text()

    for token in (
        "complete current-mainline attestation absent",
        "0x2a00005c",
        "The Gemini DTS deletes",
        "no positive direct-state row",
        "A34, the production lifecycle opener, CPU8 request",
    ):
        require(token in readme, f"README token: {token}")

    for token in (
        "Accepted reference, absent current proof",
        "read fresh through its owner",
        "CCI PLL frequency without A72 snoop/DVM port state",
        "No magic physical mapping or CCI write",
    ):
        require(token in design, f"design token: {token}")

    with (HERE / "results/state-matrix.tsv").open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    require([row["id"] for row in rows] == [
        "D01", "D02", "D03", "D04", "D05", "D06", "D07",
        "D08", "D09", "D10", "D11", "D12", "D13",
    ], "state matrix identities")
    require(rows[-1]["decision"] == "reject-keep-closed",
            "complete tuple remains rejected")
    require(all(row["fresh_owner_safe"] != "yes" for row in rows),
            "no complete fresh owner-safe row was invented")

    first_cycle = ROOT / (
        "experiments/2026-08-02-gemian-a72-first-cycle-latch/results/"
        "runtime-first-natural-pair-20260802.txt"
    )
    require(sha256(first_cycle) ==
            "6db6ea41ba4689541cb504a0486c0a1b7249834ebdb8613f0e73b0bf56e808f5",
            "historical first-cycle evidence changed")
    first_text = first_cycle.read_text()
    for token in (
        "r0=0x2a00005c",
        "r4=0x00010132 r5=0x00000002",
        "pll_con1=0xc1130000 muxsel=0x00000054 ckdiv=0x00042168",
        "final=0x00000000",
    ):
        require(first_text.count(token) >= 2,
                f"pre/post reference token: {token}")

    for token in (
        "repository_input=7a955db19d90450f4243a0334ea82ff3736af17e",
        "current_gemini_a72_power_node=deleted",
        "current_mt6797_cci_description=absent",
        "selected_next_boundary=A72-CCI-and-platform-state-ownership-audit",
        "device_write=none",
    ):
        require(token in provenance, f"provenance token: {token}")

    roadmap = (ROOT / "docs/ROADMAP.md").read_text()
    index = (ROOT / "experiments/README.md").read_text()
    hardware = (ROOT / "docs/hardware/mt6797-live-resource-map.md").read_text()
    require("direct recovery-state attestation audit" in roadmap,
            "roadmap decision")
    require("mainline A34 direct recovery-state audit" in index,
            "experiment index")
    require("probe-time cache" in hardware and
            "A72 CCI" in hardware,
            "durable hardware result")

    print("audit=pass")
    print("state_rows=13")
    print("historical_reference=pre-post-identical")
    print("current_complete_direct_tuple=absent")
    print("selected_next=A72-CCI-and-platform-state-ownership-audit")
    print("a34_owner=closed")
    print("device_write=none")


if __name__ == "__main__":
    main()
