#!/usr/bin/env python3
"""Validate the negative DA921x page/ownership audit without hardware access."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH_0170 = ROOT / "patches/v7.1.3/0170-regulator-add-legacy-DA921x-resource-only-provider.patch"
PATCH_0164 = ROOT / "patches/v7.1.3/0164-arm64-validate-frozen-A72-A36-prestates.patch"
PATCH_0172 = ROOT / "patches/v7.1.3/0172-arm64-add-provider-owner-callback-refusal-boundary.patch"
PATCH_0173 = ROOT / "patches/v7.1.3/0173-arm64-add-provider-release-refusal-boundary.patch"
PATCH_0100 = ROOT / "patches/v7.1.3/0100-soc-mediatek-require-ready-MT6797-DVFSP-handoff-supplier.patch"
PATCH_0101 = ROOT / "patches/v7.1.3/0101-i2c-mediatek-require-MT6797-DVFSP-handoff.patch"
PATCH_0102 = ROOT / "patches/v7.1.3/0102-arm64-dts-mediatek-enable-childless-Gemini-I2C6-after-handoff.patch"
HANDOFF_FRAGMENT = ROOT / "configs/gemini-dvfsp-handoff-owner.fragment"
MANIFEST = ROOT / "kernel/manifest.json"
LEDGER = Path(__file__).resolve().parents[1] / "results/source-audit.tsv"
RECONCILIATION = Path(__file__).resolve().parents[1] / "results/source-reconciliation-20260806.txt"
CROSSCHECK = ROOT / "experiments/2026-07-23-da9214-resource-only/results/da9214-datasheet-crosscheck-20260723.txt"
OBSERVER_DESIGN = ROOT / "experiments/2026-07-23-gemian-a72-owner-observer/DESIGN.md"
OBSERVER_PATCH = ROOT / "experiments/2026-07-23-gemian-a72-owner-observer/patches/0002-diagnostic-add-owner-local-fixed-A72-snapshots.patch"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"missing={label}:{needle}")


def main() -> None:
    p0170 = PATCH_0170.read_text()
    p0164 = PATCH_0164.read_text()
    p0172 = PATCH_0172.read_text()
    p0173 = PATCH_0173.read_text()
    p0100 = PATCH_0100.read_text()
    p0101 = PATCH_0101.read_text()
    p0102 = PATCH_0102.read_text()
    handoff_fragment = HANDOFF_FRAGMENT.read_text()
    manifest = MANIFEST.read_text()
    ledger = LEDGER.read_text()
    reconciliation = RECONCILIATION.read_text()
    crosscheck = CROSSCHECK.read_text()
    observer_design = OBSERVER_DESIGN.read_text()
    observer_patch = OBSERVER_PATCH.read_text()

    for needle, label in (
        ("primary_address\t0x68", "primary-address"),
        ("page2_client_address\t0x69", "page2-address"),
        ("0xd7,0xd9", "vsel-registers"),
        ("0x5d,0x5e", "control-registers"),
        ("provider_vsel_mask\t0x7f", "vsel-mask"),
        ("provider_enable_mask\t0x01", "enable-mask"),
    ):
        # The source ledger contains the normalized facts; the selected patch
        # must also contain the corresponding implementation token.
        require(ledger, needle, f"ledger-{label}")
    for needle, label in (
        ("a36_page_value\t0x80", "a36-page"),
        ("a36_buckb_vsel\t0x46", "a36-vsel"),
    ):
        require(ledger, needle, f"ledger-{label}")
    for needle, label in (
        ("#define DA9213_LEGACY_PRIMARY_ADDR\t0x68", "source-primary"),
        ("#define DA9213_LEGACY_PAGE2_ADDR\t0x69", "source-page2"),
        ("0xd7, 0xd9", "source-vsel"),
        ("0x5d, 0x5e", "source-control"),
    ):
        require(p0170, needle, label)
    require(p0164, "#define MT6797_A72_A36_DA921X_PAGE 0x80", "source-a36-page")
    require(p0164, "#define MT6797_A72_A36_BUCKB_VSEL 0x46", "source-a36-vsel")
    require(p0172, "provider-owner acquire refused: read-only resource boundary", "acquire-refusal")
    require(p0173, "provider-owner release refused: no rollback owner", "release-refusal")
    for needle, label in (
        ("mt6797_dvfsp_handoff_require_ready", "handoff-ready-api"),
        ("EXPORT_SYMBOL_GPL(mt6797_dvfsp_handoff_require_ready)", "handoff-ready-export"),
    ):
        require(p0100, needle, label)
    require(p0101, "ret = mt6797_dvfsp_handoff_require_ready(", "i2c6-transfer-handoff-check")
    require(p0102, "access-controllers = <&dvfsp_handoff>;", "i2c6-access-controller")
    require(handoff_fragment, "CONFIG_MTK_MT6797_DVFSP_HANDOFF=y", "handoff-config")
    require(manifest, '"configs/gemini-dvfsp-handoff-owner.fragment"', "handoff-profile-fragment")
    for needle, label in (
        ("observation_legacy_page_control=I2C_REG_PAGE_00x_selects_0x000_through_0x0ff", "legacy-page-window"),
        ("observation_legacy_page_control_2=I2C_REG_PAGE_01x_selects_0x100_through_0x17f", "legacy-page-window-2"),
        ("observation_live_page_con=0x80_REVERT_set", "observed-page-revert"),
        ("active_rail_write_gate=prove_DVFSP_quiescent_or_implement_and_validate_the_matching_I2C6_ownership_protocol", "dvfsp-gate"),
    ):
        require(crosscheck, needle, label)
    for needle, label in (
        ("DA9214 | page", "vendor-register-contract"),
        ("da9214_i2c_access", "vendor-owner-mutex"),
    ):
        require(observer_design, needle, label)
    for needle, label in (
        ("DA9214_A72_PAGE_REVERT", "page-revert-token"),
        ("da9214_a72_write_locked", "vendor-write-helper"),
        ("da9214_a72_config_locked", "vendor-rmw-helper"),
    ):
        require(observer_patch, needle, label)
    for needle, label in (
        ("vendor_transfer_shape=pointer/read_and_two-byte_read-modify-write", "reconciliation-transfer"),
        ("vendor_dvfsp_arbitration=SEMA_I2C_DRV_pause_around_each_I2C6_transfer", "reconciliation-dvfsp"),
        ("mainline_dvfsp_arbitration=unproven", "reconciliation-mainline-gap"),
    ):
        require(reconciliation, needle, label)

    # Restrict the negative write check to the provider's transfer block. The
    # source is allowed to mention future writes in documentation comments.
    transfer_start = p0170.index("static int da9213_legacy_read_reg")
    transfer_end = p0170.index("static int da9213_legacy_get_voltage_sel")
    transfer = p0170[transfer_start:transfer_end]
    for forbidden in ("i2c_smbus_write", "I2C_M_RD = 0", "PAGE_CON", "i2c_write"):
        if forbidden in transfer:
            raise SystemExit(f"unexpected-provider-write-token={forbidden}")
    require(transfer, "msgs[1].flags = I2C_M_RD", "read-only-transfer")
    for field in (
        "page_encoding\tpartially-proven",
        "page_owner\tcandidate-owner;handoff-unproven",
        "write_transport\tvendor-shape-known;mainline-arbitration-unproven",
        "control_mask\tvendor-bit0-known;mainline-contract-unproven",
        "post_settle_readback\tvendor-observed;provider-unimplemented",
        "rollback_owner\tpre-isolation-accepted;post-isolation-unresolved",
        "hardware_action\tnone",
    ):
        require(ledger, field, field.replace("\t", "="))

    print("page_encoding=partially-proven")
    print("page_owner=candidate-owner;mainline-handoff-unproven")
    print("write_transport=vendor-shape-known;mainline-arbitration-unproven")
    print("control_mask=vendor-bit0-known;mainline-contract-unproven")
    print("post_settle_readback=vendor-observed;provider-unimplemented")
    print("rollback_owner=pre-isolation-accepted;post-isolation-unresolved")
    print("mainline_handoff=profile-selected;I2C6-access-controller;ready-gate-present")
    print("provider_transfer=direct-__i2c_transfer;write-absent")
    print("per_transfer_lease=unproven;dispatch-expansion-not-pinned")
    print("decision=BLOCK_WRITABLE_PROVIDER")
    print("hardware_action=none")
    print("status=PASS_NEGATIVE_AUDIT")


if __name__ == "__main__":
    main()
