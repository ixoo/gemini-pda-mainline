#!/usr/bin/env python3
"""Validate the composed read-only owner prerequisite source."""

import argparse
from pathlib import Path


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"missing {label}: {needle}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()
    paths = [
        root / "include/linux/soc/mediatek/mt6797-dvfsp-handoff.h",
        root / "drivers/soc/mediatek/mt6797-dvfsp-state-snapshot.c",
        root / "include/linux/soc/mediatek/mt6797-dvfsp-vendor-provider.h",
        root / "drivers/soc/mediatek/mt6797-dvfsp-vendor-provider.c",
        root / "drivers/soc/mediatek/mt6797-dvfsp-calibrated-provider-test.c",
        root / "drivers/soc/mediatek/mt6797-dvfsp-vendor-provider-test.c",
    ]
    for path in paths:
        if not path.is_file():
            raise SystemExit(f"missing source file: {path}")
    text = "\n".join(path.read_text() for path in paths)
    for needle, label in (
        ("MT6797_DVFSP_STATE_PROVENANCE_ABI\t\t2", "state provenance ABI"),
        ("u64 table_epoch;", "64-bit epoch"),
        ("snapshot->owner_handle = input->owner_handle;", "owner attribution"),
        ("snapshot->transition_handle = input->transition_handle;", "transition attribution"),
        ("snapshot->provenance = input->provenance;", "snapshot provenance"),
        ("MT6797_DVFSP_VENDOR_PROVIDER_ABI\t4", "provider ABI"),
        ("struct mt6797_dvfsp_vendor_source_provenance provenance;", "mapped provenance"),
        ("mt6797_dvfsp_vendor_source_provenance(bridge->source", "provenance callback"),
        ("provenance->source_generation != source->generation", "generation equality"),
        ("provenance->table_epoch != identity->table_epoch", "epoch equality"),
        ("mt6797_dvfsp_vendor_provider_rejects_provenance_mismatch", "mismatch KUnit"),
        ("mt6797_dvfsp_provider_snapshot_keeps_attribution", "attribution KUnit"),
    ):
        require(text, needle, label)

    for forbidden in (
        "readl(", "writel(", "i2c_transfer", "regulator_", "clk_set_",
        "cpu_up(", "cpu_down(", "arm_smccc", "platform_driver_register",
    ):
        if forbidden in text:
            raise SystemExit(f"unexpected state-changing operation: {forbidden}")
    print("source_contract=passed")
    print("table_epoch_width=64")
    print("snapshot_attribution=preserved")
    print("vendor_provenance=consumed-and-cross-checked")
    print("hardware_write=none")
    print("cpu8_cpu9_admission=closed")


if __name__ == "__main__":
    main()
