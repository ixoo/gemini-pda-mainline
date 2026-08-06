#!/usr/bin/env python3
"""Validate the negative DA921x page/ownership audit without hardware access."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH_0170 = ROOT / "patches/v7.1.3/0170-regulator-add-legacy-DA921x-resource-only-provider.patch"
PATCH_0164 = ROOT / "patches/v7.1.3/0164-arm64-validate-frozen-A72-A36-prestates.patch"
PATCH_0172 = ROOT / "patches/v7.1.3/0172-arm64-add-provider-owner-callback-refusal-boundary.patch"
PATCH_0173 = ROOT / "patches/v7.1.3/0173-arm64-add-provider-release-refusal-boundary.patch"
LEDGER = Path(__file__).resolve().parents[1] / "results/source-audit.tsv"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"missing={label}:{needle}")


def main() -> None:
    p0170 = PATCH_0170.read_text()
    p0164 = PATCH_0164.read_text()
    p0172 = PATCH_0172.read_text()
    p0173 = PATCH_0173.read_text()
    ledger = LEDGER.read_text()

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
        "page_encoding\tunproven",
        "page_owner\tunproven",
        "write_transport\tunproven",
        "control_mask\tunproven",
        "post_settle_readback\tunproven",
        "rollback_owner\tunproven",
        "hardware_action\tnone",
    ):
        require(ledger, field, field.replace("\t", "="))

    print("page_encoding=unproven")
    print("page_owner=unproven")
    print("write_transport=unproven")
    print("control_mask=unproven")
    print("post_settle_readback=unproven")
    print("rollback_owner=unproven")
    print("decision=BLOCK_WRITABLE_PROVIDER")
    print("hardware_action=none")
    print("status=PASS_NEGATIVE_AUDIT")


if __name__ == "__main__":
    main()
