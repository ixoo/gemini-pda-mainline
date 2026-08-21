#!/usr/bin/env python3
"""Validate the frozen A34 provenance-owner audit."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]
PARENT = "8513b645fb122e766779f276e30ce74b4af82ec5"
PATCH_SHA256 = "f07b490279cedf9ee7c4f9d294c4b4e966db72715a78b2d25c2abd64b3fd861b"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> None:
    readme = (EXPERIMENT / "README.md").read_text()
    design = (EXPERIMENT / "DESIGN.md").read_text()
    provenance = (EXPERIMENT / "results/provenance-20260821.txt").read_text()
    patch = ROOT / "patches/v7.1.3/0302-arm64-add-A72-A34-eligibility-evaluator.patch"

    require(sha256(patch) == PATCH_SHA256, "canonical patch 0302 drifted")
    require(f"repository_parent={PARENT}" in provenance, "repository parent drifted")
    require("wdt_status_reader_call_count=0" in provenance,
            "LK status-reader result drifted")
    require("private_replay_image_value=0x00" in provenance,
            "secure replay initial value drifted")
    require("independent_non_smc_reader=absent" in provenance,
            "private reader finding drifted")
    require("production_a34_open=forbidden" in provenance,
            "production owner safety result drifted")

    with (EXPERIMENT / "results/authority-matrix.tsv").open(newline="") as stream:
        rows = {row["id"]: row for row in csv.DictReader(stream, delimiter="\t")}

    require(set(rows) == {f"R0{index}" for index in range(1, 8)},
            "authority matrix row set drifted")
    require(rows["R01"]["result"] == "capture-selected",
            "TOPRGU capture is no longer selected")
    for identifier, row in rows.items():
        require(row["can_supply_authority_alone"] == "no",
                f"{identifier} was promoted to standalone authority")
    require(rows["R06"]["result"] == "rejected",
            "ordinary reboot is no longer rejected")
    require(rows["R07"]["result"] == "rejected",
            "active affinity query is no longer rejected")

    for token in (
        "capture exactly once",
        "before `mtk_wdt_init()`",
        "no A34 caller",
        "preserve A26",
        "accepting a warm reboot",
    ):
        require(token in design, f"design token missing: {token}")

    for token in (
        "ordinary Linux reboot",
        "capture-only TOPRGU snapshot",
        "No CPU8 request or device boot",
    ):
        require(token in readme, f"README token missing: {token}")

    # Construct sensitive path/device tokens so this validator can inspect its
    # own source without matching the token definitions themselves.
    forbidden = ("/" + "Users/", "/" + "home/", "mmc" + "blk", "art" + "ifacts/")
    for path in EXPERIMENT.rglob("*"):
        if path.is_file():
            contents = path.read_text()
            for token in forbidden:
                require(token not in contents, f"private token {token} in {path.name}")

    print("audit=pass")
    print(f"repository_parent={PARENT}")
    print(f"canonical_patch_sha256={PATCH_SHA256}")
    print("authority_rows=7")
    print("toprgu_capture=selected")
    print("standalone_authority_rows=0")
    print("ordinary_reboot=rejected")
    print("active_affinity_reader=rejected")
    print("production_a34_open=forbidden")
    print("device_action=none")


if __name__ == "__main__":
    main()
