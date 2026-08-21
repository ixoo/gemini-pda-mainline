#!/usr/bin/env python3
"""Validate the frozen retained ram-console copy-owner audit."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]
REPOSITORY_INPUT = "1d0b3c55d8743d0fa2983dda0a228e5a61e6d41b"
PATCHES = {
    "patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch":
        "6aee8e45d2498479c9231fdd98d678c780cff93a08e6da5ef17664f993f6bb24",
    "patches/v7.1.3/0303-watchdog-mtk-capture-raw-boot-status.patch":
        "29fbdb0190d3dd3931839bbb6f0ea936cf4e0c4219f44b4e183422a343cae97a",
    "patches/v7.1.3/0304-soc-mediatek-add-retained-ram-console-parser.patch":
        "5d0f76141311b3036eddeca5672ef090d36b1fd040038a2bd011373ac9a1fc99",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    readme = (HERE / "README.md").read_text()
    design = (HERE / "DESIGN.md").read_text()
    provenance = (HERE / "results/source-provenance-20260821.txt").read_text()

    require(f"repository_commit={REPOSITORY_INPUT}" in provenance,
            "repository input drifted")
    for path, expected in PATCHES.items():
        require(sha256(ROOT / path) == expected, f"canonical input drifted: {path}")
        require(f"{Path(path).stem}_sha256={expected}" in provenance or
                expected in provenance,
                f"canonical input not frozen: {path}")

    for token in (
        "custom_reserved_child_auto_platform_device=no",
        "memory_region_resource_api=of_reserved_mem_region_to_resource",
        "arm64_nomap_pfn_is_map_memory=false",
        "selected_map_primitive=memremap-MEMREMAP_WB",
        "selected_copy_count=1",
        "selected_unmap_before_parse=yes",
        "mainline_physical_ram_console_writer=absent",
        "copies_full_region_before_mutation=yes",
        "secure_epoch_attestation=unresolved",
        "reset_history_combiner=forbidden",
        "a34_owner=closed",
        "device_action=none",
    ):
        require(token in provenance, f"provenance token missing: {token}")

    with (HERE / "results/decision-matrix.tsv").open(newline="") as stream:
        rows = {row["id"]: row for row in csv.DictReader(stream, delimiter="\t")}

    require(set(rows) == {
        *(f"M0{index}" for index in range(1, 10)),
        "W01", "W02", "W03",
        *(f"E0{index}" for index in range(1, 7)),
    }, "decision matrix inventory")
    require(rows["M03"]["decision"] == "select", "platform consumer selection")
    require(rows["M05"]["decision"] == "select", "exact phandle selection")
    require(rows["M07"]["decision"] == "select", "transient mapping selection")
    require(rows["M09"]["decision"] == "select", "snapshot selection")
    require(rows["M02"]["decision"] == "reject", "generic NVMEM rejection")
    require(rows["M06"]["decision"] == "reject", "persistent map rejection")
    for identifier in ("E01", "E02", "E03", "E04", "E05"):
        require("reject" in rows[identifier]["decision"],
                f"epoch shortcut promoted: {identifier}")
    require(rows["E06"]["decision"] == "unresolved",
            "secure attestation no longer unresolved")

    for token in (
        "copy once at probe",
        "unmap before parsing",
        "production A34 owner and CPU8/CPU9 admission remain CLOSED",
        "No complete public preloader source",
    ):
        require(token in readme, f"README token missing: {token}")

    for token in (
        "exactly one `memory-region` phandle",
        "memremap(resource.start, resource_size, MEMREMAP_WB)",
        "call `memunmap()` before parsing",
        "No secure-epoch implementation is selected",
    ):
        require(token in design, f"design token missing: {token}")

    forbidden = ("/" + "Users/", "/" + "home/", "mmc" + "blk", "art" + "ifacts/")
    for path in HERE.rglob("*"):
        if not path.is_file():
            continue
        contents = path.read_text()
        for token in forbidden:
            require(token not in contents, f"private token {token} in {path.name}")

    print("audit=pass")
    print(f"repository_input={REPOSITORY_INPUT}")
    print("decision_rows=18")
    print("copy_owner=selected")
    print("mapping=transient-MEMREMAP_WB")
    print("copy_count=1")
    print("unmap_before_parse=yes")
    print("secure_epoch_attestation=unresolved")
    print("reset_history_combiner=forbidden")
    print("a34_owner=closed")
    print("device_action=none")


if __name__ == "__main__":
    main()
