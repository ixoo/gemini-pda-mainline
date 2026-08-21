#!/usr/bin/env python3
"""Validate the frozen MT6797 secure replay epoch audit."""

from __future__ import annotations

import csv
from pathlib import Path


HERE = Path(__file__).resolve().parents[1]
REPOSITORY_INPUT = "b597ea85c3069b477ae41ad62f025b498e62cf17"
PRELOADER_SHA256 = (
    "25319ce877bd17b204fa264645aebf4583ec10ae2f05f6d8a7fff5efe4c06246"
)
TEE_SHA256 = (
    "2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def parse_hex_field(provenance: dict[str, str], key: str) -> int:
    require(key in provenance, f"missing provenance field: {key}")
    return int(provenance[key], 16)


def main() -> None:
    readme = (HERE / "README.md").read_text()
    design = (HERE / "DESIGN.md").read_text()
    provenance_lines = (
        HERE / "results/provenance-20260821.txt"
    ).read_text().splitlines()
    provenance = dict(line.split("=", 1) for line in provenance_lines if line)

    require(provenance["repository_commit"] == REPOSITORY_INPUT,
            "repository input drifted")
    require(provenance["preloader_boot_region_1_sha256"] == PRELOADER_SHA256,
            "preloader region 1 identity drifted")
    require(provenance["preloader_boot_region_2_sha256"] == PRELOADER_SHA256,
            "preloader region 2 identity drifted")
    require(provenance["tee1_sha256"] == TEE_SHA256,
            "tee1 identity drifted")
    require(provenance["tee2_sha256"] == TEE_SHA256,
            "tee2 identity drifted")

    start = parse_hex_field(provenance, "secure_bss_start")
    size = parse_hex_field(provenance, "secure_bss_size")
    end = parse_hex_field(provenance, "secure_bss_end_exclusive")
    replay = parse_hex_field(provenance, "private_replay_ledger")
    replay_offset = parse_hex_field(
        provenance, "private_replay_offset_within_bss"
    )
    require(start + size == end, "BSS range arithmetic")
    require(start <= replay < end, "replay byte outside cleared BSS")
    require(replay - start == replay_offset, "replay offset arithmetic")

    for key, expected in (
        ("preloader_boot_regions_byte_identical", "yes"),
        ("tee_slots_byte_identical", "yes"),
        ("private_firmware_bytes_committed", "no"),
        ("private_replay_owner_safe_zero", "confirmed-after-primary-entry"),
        ("pre_a34_set_writer", "blocked-by-A26"),
        ("atf_log_epoch_attestation", "rejected"),
        ("runtime_secure_image_measurement", "absent"),
        ("ordinary_linux_reboot_provenance", "still-rejected"),
        ("separate_platform_or_external_reset_proof", "still-required"),
        ("a34_owner", "closed"),
        ("cpu8_request", "none"),
        ("build", "none"),
        ("device_action", "none"),
    ):
        require(provenance.get(key) == expected,
                f"provenance decision drifted: {key}")

    with (HERE / "results/control-flow.tsv").open(newline="") as stream:
        rows = {row["id"]: row for row in csv.DictReader(stream, delimiter="\t")}

    require(set(rows) == {
        *(f"S{index:02d}" for index in range(1, 11)),
        "N01", "N02", "N03",
    }, "control-flow inventory")
    for identifier in ("S01", "S02", "S03", "S04", "S05", "S06",
                       "S07", "S08", "S10"):
        require(rows[identifier]["decision"].startswith("confirm"),
                f"positive chain drifted: {identifier}")
    require(rows["S09"]["decision"] ==
            "confirm-owner-safe-zero-after-primary-entry",
            "replay-zero conclusion drifted")
    require(rows["N01"]["decision"] == "reject-as-attestation",
            "ATF log promoted")
    require(rows["N02"]["decision"] == "defer-to-reset-classifier",
            "reset history prematurely promoted")
    require(rows["N03"]["decision"] == "keep-closed",
            "A34 owner opened")

    for token in (
        "explicitly overwritten with zero by primary",
        "Ordinary Linux reboot provenance remains rejected",
        "private replay-zero half of A34 is now closed conditionally",
        "The production A34 owner",
    ):
        require(token in readme, f"README token missing: {token}")

    for token in (
        "zero [0x11d340, 0x122acc)",
        "MT6797_A72_A34_PRIVATE_REPLAY_OWNER_SAFE_ZERO",
        "This audit does not convert an ordinary Linux reboot",
        "Freeze the strict platform/external reset classifier",
    ):
        require(token in design, f"design token missing: {token}")

    forbidden = ("/" + "Users/", "/" + "home/", "mmc" + "blk", "art" + "ifacts/")
    for path in HERE.rglob("*"):
        if not path.is_file():
            continue
        contents = path.read_text()
        for token in forbidden:
            require(token not in contents,
                    f"private token {token} in {path.name}")

    print("audit=pass")
    print(f"repository_input={REPOSITORY_INPUT}")
    print("control_flow_rows=13")
    print("tee_slots=byte-identical")
    print("secure_bss_range=0x11d340-0x122acc-exclusive")
    print("private_replay_ledger=0x11ea24")
    print("private_replay_owner_safe_zero=confirmed-after-primary-entry")
    print("ordinary_linux_reboot_provenance=still-rejected")
    print("next=strict-platform-external-reset-classifier-audit")
    print("a34_owner=closed")
    print("device_action=none")


if __name__ == "__main__":
    main()
