#!/usr/bin/env python3
"""Validate the negative DA921x page/ownership audit without hardware access."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH_0170 = ROOT / "patches/v7.1.3/0170-regulator-add-legacy-DA921x-resource-only-provider.patch"
PATCH_0164 = ROOT / "patches/v7.1.3/0164-arm64-validate-frozen-A72-A36-prestates.patch"
PATCH_0172 = ROOT / "patches/v7.1.3/0172-arm64-add-provider-owner-callback-refusal-boundary.patch"
PATCH_0173 = ROOT / "patches/v7.1.3/0173-arm64-add-provider-release-refusal-boundary.patch"
PATCH_0174 = ROOT / "patches/v7.1.3/0174-soc-mediatek-add-I2C6-DVFSP-transfer-lease.patch"
PATCH_0098 = ROOT / "patches/v7.1.3/0098-soc-mediatek-add-MT6797-DVFSP-one-way-handoff.patch"
PATCH_0100 = ROOT / "patches/v7.1.3/0100-soc-mediatek-require-ready-MT6797-DVFSP-handoff-supplier.patch"
PATCH_0101 = ROOT / "patches/v7.1.3/0101-i2c-mediatek-require-MT6797-DVFSP-handoff.patch"
PATCH_0102 = ROOT / "patches/v7.1.3/0102-arm64-dts-mediatek-enable-childless-Gemini-I2C6-after-handoff.patch"
HANDOFF_FRAGMENT = ROOT / "configs/gemini-dvfsp-handoff-owner.fragment"
MANIFEST = ROOT / "kernel/manifest.json"
CORE_DISPATCH = Path(__file__).resolve().parents[1] / "results/i2c-core-dispatch-20260806.txt"
DVFSP_LEASE = Path(__file__).resolve().parents[1] / "results/dvfsp-lease-audit-20260806.txt"
BUILDBOX_LEASE = Path(__file__).resolve().parents[1] / "results/buildbox-transfer-lease-20260806.txt"
FIRMWARE_LEASE = Path(__file__).resolve().parents[1] / "results/firmware-owner-lease-20260806.txt"
PCM_SCAN = Path(__file__).resolve().parents[1] / "results/pcm-firmware-owner-scan-20260806.txt"
SECURE_IMAGE_SCAN = Path(__file__).resolve().parents[1] / "results/secure-owner-image-scan-20260806.txt"
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
    p0174 = PATCH_0174.read_text()
    p0098 = PATCH_0098.read_text()
    p0100 = PATCH_0100.read_text()
    p0101 = PATCH_0101.read_text()
    p0102 = PATCH_0102.read_text()
    handoff_fragment = HANDOFF_FRAGMENT.read_text()
    manifest = MANIFEST.read_text()
    core_dispatch = CORE_DISPATCH.read_text()
    dvfsp_lease = DVFSP_LEASE.read_text()
    buildbox_lease = BUILDBOX_LEASE.read_text()
    firmware_lease = FIRMWARE_LEASE.read_text()
    pcm_scan = PCM_SCAN.read_text()
    secure_image_scan = SECURE_IMAGE_SCAN.read_text()
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
        ("struct mt6797_dvfsp_i2c6_lease", "lease-struct"),
        ("mt6797_dvfsp_handoff_begin_i2c6_transfer", "lease-begin-api"),
        ("mt6797_dvfsp_handoff_end_i2c6_transfer", "lease-end-api"),
        ("MT6797_DVFSP_TRANSFER_COOKIE_XOR", "lease-cookie"),
        ("i2c6-transfer-lease-mismatch", "lease-mismatch-fault"),
        ("mutex_lock(&handoff->transfer_lock)", "lease-lock"),
        ("lease_active", "consumer-lease-use"),
    ):
        require(p0174, needle, label)
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
        ("function=__i2c_transfer", "core-transfer-function"),
        ("adapter_dispatch=adap->algo->master_xfer(adap, msgs, num)", "core-master-xfer-dispatch"),
        ("public_wrapper=ret = __i2c_transfer(adap, msgs, num)", "core-public-wrapper"),
        ("status=PASS_CORE_DISPATCH", "core-dispatch-status"),
    ):
        require(core_dispatch, needle, label)
    for needle, label in (
        ("ready_check=mt6797_dvfsp_handoff_require_ready_locks_handoff_and_checks_both", "ready-check-contract"),
        ("transfer_entry=mtk_i2c_transfer_calls_require_ready_before_transfer", "transfer-entry-check"),
        ("transfer_lease_api=0174-validated;Buildbox-pass", "lease-api-validated"),
        ("ready_check_scope=entry_predicate_only;0174-holds-lease-across-transfer-validated", "lease-scope-validated"),
        ("firmware_semaphore=vendor_SEMA_I2C_DRV_not_represented", "vendor-semaphore-gap"),
        ("status=", "handoff-audit-present"),
    ):
        require(dvfsp_lease, needle, label)
    for needle, label in (
        ("repository_commit=8b9bf76f81484551d759f8753ecf9b3979324d6f", "buildbox-commit"),
        ("artifact=linux-7.1.3-gemini-a72-p24-provider-owner-refusal-57066ffc-a1b4e306", "buildbox-artifact"),
        ("patchset_sha256=57066ffc155374ba7e6453367dde8a98bd10d9b237d88857d39c8c2365ae084b", "buildbox-patchset"),
        ("config_sha256=2e3dfb4d9f545bbbf21522d1790aeba531a21a9a49fac427467713ed94dc7389", "buildbox-config"),
        ("sha256sums=passed", "buildbox-checksums"),
        ("hardware_write=none", "buildbox-no-write"),
        ("status=PASS_BUILDBOX_TRANSFER_LEASE", "buildbox-status"),
    ):
        require(buildbox_lease, needle, label)
    for needle, label in (
        ("vendor_user=SEMA_I2C_DRV;enum_user=1", "firmware-user"),
        ("vendor_pause_source=PAUSE_I2CDRV;pause_map_bit=0x2", "firmware-pause-source"),
        ("vendor_acquire_success=drop_DVFSP_prepared_I2C_APPM_reference;record_pause_map_bit", "firmware-clock-release"),
        ("external_writer_audit=negative_for_direct_PCM_restart_writer_in_retained_LK_TEE_SCP_payloads", "firmware-writer-audit"),
        ("external_attribution=ATF_secure_CSPM_clock_and_semaphore_access", "firmware-atf-attribution"),
        ("external_residual=SCP_computed_or_local_alias_unexcluded;PCM_restart_SEMA_I2C_DRV_owner_unproven", "firmware-residual-gap"),
        ("receiver_stopped_state=Candidate_AO_runtime_validated;PCM_signature_stable;45s_late_check_passed", "receiver-stopped-state"),
        ("receiver_shared_clock=Candidate_AO_runtime_validated;one_CCF_enable_disable;ungated_to_gated;late_gate_stable", "receiver-clock-normalization"),
        ("receiver_i2c6_activity=none;I2C6_disabled_childless", "receiver-no-i2c6"),
        ("receiver_semantic_mapping=absent;AO_does_not_implement_PAUSE_I2CDRV_or_FW_DONE", "receiver-semantic-gap"),
        ("mainline_firmware_lease=unproven", "firmware-lease-gap"),
        ("reviewed_protocol=0175_callback_contract;default-unregistered;Buildbox-pass", "firmware-protocol-contract"),
        ("protocol_effect=contract-only;no_MMIO;no_I2C;no_regulator;no_CPU_ON", "firmware-protocol-no-effect"),
        ("required_closure=prove_one-way_receiver_authoritative_for_SEMA_I2C_DRV_or_add_reviewed_firmware_protocol;explicit_external-owner-proof;sticky-fault_and_resume-revalidation", "firmware-closure"),
        ("repeat_prohibition=do_not_repeat_Candidate_AO_stopped-state_or_clock-normalization_boot", "no-repeat-ao"),
        ("decision=BLOCK_WRITABLE_PROVIDER", "firmware-decision"),
        ("status=PASS_FIRMWARE_LEASE_RECONCILIATION_NEGATIVE", "firmware-status"),
    ):
        require(firmware_lease, needle, label)
    for needle, label in (
        ("files=9;group=pcm_*.bin", "pcm-file-set"),
        ("scan=cspm_base_0x11015000=0_all_files", "pcm-cspm-base-negative"),
        ("scan=pcm_con0_0x11015018=0_all_files", "pcm-control-negative"),
        ("scan=csram_base_0x0012a000=0_all_files", "pcm-csram-negative"),
        ("scan=fw_done_bit_0x8000=0_all_files", "pcm-fw-done-negative"),
        ("archive_boundary=contains_Gemian_userspace_SPM_PCM_blobs_only;no_LK_TEE_SCP_payloads", "pcm-archive-boundary"),
        ("interpretation=negative_direct-literal-evidence;encoded-key-and-bit-values_not_owner-proof", "pcm-interpretation"),
        ("decision=NO_NEW_OWNER_AUTHORITY", "pcm-decision"),
        ("status=PASS_LIMITED_PCM_SCAN_NEGATIVE", "pcm-status"),
    ):
        require(pcm_scan, needle, label)
    for needle, label in (
        ("source=project-start-full-backup;read_only;no_new_backup;raw_contents_not_staged", "secure-scan-source"),
        ("lk_sha256=75ec9f0ba97af9e68d964b304e0de809f9b4546982570bd16b2e7fe88823282c", "secure-lk-hash"),
        ("tee1_sha256=2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3", "secure-tee-hash"),
        ("scp1_sha256=3c65097eeeb4e2d29dd125752cfb648c6da5e3651eabc9dad1da672b2558cd66", "secure-scp-hash"),
        ("lk_named_sema_i2cdrv_strings=0", "secure-lk-semaphore-gap"),
        ("tee_i2c6_strings=0", "secure-tee-i2c6-gap"),
        ("scp_i2c6_strings=0", "secure-scp-i2c6-gap"),
        ("scp_named_sema_i2cdrv_strings=0", "secure-scp-semaphore-gap"),
        ("crosscheck=external-cspm-writer-audit-20260724;ATF_CSPM_owner_attributed;PCM_restart_owner_not-found", "secure-owner-crosscheck"),
        ("tee_direct_constructor_cspm=found;keyed_0x0b160001;secure_semaphore_0x11015448", "secure-atf-owner"),
        ("tee_direct_pcm_con0_kick_reset=not-found", "secure-pcm-restart-gap"),
        ("negative_result=secure_images_do_not_identify_the_PCM_restart_SEMA_I2C_DRV_lease_owner", "secure-owner-negative"),
        ("interpretation=bounded_strings_and_literal_scan;computed_or_secure_alias_access_remains_unexcluded", "secure-scan-boundary"),
        ("status=PASS_LIMITED_SECURE_IMAGE_SCAN_NEGATIVE", "secure-scan-status"),
    ):
        require(secure_image_scan, needle, label)
    require(p0098, "I2C6 remains disabled", "ao-i2c6-disabled-contract")
    require(p0098, "does not implement per-transfer DVFSP coordination", "ao-no-per-transfer-contract")
    for forbidden, label in (("PAUSE_I2CDRV", "ao-pause-source"), ("FW_DONE", "ao-firmware-ack")):
        if forbidden in p0098:
            raise SystemExit(f"unexpected-ao-vendor-lease-token={label}:{forbidden}")
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
    require(transfer, "i2c_lock_bus(chip->client->adapter, I2C_LOCK_ROOT_ADAPTER)", "provider-root-lock")
    require(core_dispatch, "core_lock_precondition=Adapter lock must be held when calling this function", "core-lock-precondition")
    for field in (
        "page_encoding\tpartially-proven",
        "page_owner\tcandidate-owner;ready-gate-only;firmware-lease-unproven",
        "write_transport\tvendor-shape-known;mainline-arbitration-unproven",
        "control_mask\tvendor-bit0-known;mainline-contract-unproven",
        "post_settle_readback\tvendor-observed;provider-unimplemented",
        "rollback_owner\tpre-isolation-accepted;post-isolation-unresolved",
        "hardware_action\tnone",
        "firmware_protocol_contract\t0175-default-unregistered;Buildbox-pass",
        "pcm_firmware_owner_scan\tnegative-direct-literal;archive-boundary-only",
        "secure_owner_image_scan\tLK-generic-I2C;ATF-CSPM-interference-attributed;SCP-DVFS-SPM;no-PCM-restart-SEMA-owner",
    ):
        require(ledger, field, field.replace("\t", "="))

    print("page_encoding=partially-proven")
    print("page_owner=candidate-owner;ready-gate-only;firmware-lease-unproven")
    print("write_transport=vendor-shape-known;mainline-arbitration-unproven")
    print("control_mask=vendor-bit0-known;mainline-contract-unproven")
    print("post_settle_readback=vendor-observed;provider-unimplemented")
    print("rollback_owner=pre-isolation-accepted;post-isolation-unresolved")
    print("mainline_handoff=profile-selected;I2C6-access-controller;ready-gate-present")
    print("provider_transfer=direct-__i2c_transfer;write-absent")
    print("core_dispatch=expanded;master_xfer-path-proven")
    print("linux_bus_lock=provider-root-lock;core-lock-precondition-proven")
    print("dvfsp_ready=state-and-permission-ready;entry-check-proven")
    print("mainline_transfer_lease=0174-validated;generation-cookie;PM-lock-integrated;Buildbox-pass")
    print("firmware_owner_lease=unproven;vendor_SEMA_I2C_DRV_not_represented")
    print("secure_owner_image_scan=negative;ATF-CSPM-interference-attributed;LK-generic-I2C;SCP-DVFS-SPM;no-PCM-restart-SEMA-owner")
    print("decision=BLOCK_WRITABLE_PROVIDER")
    print("hardware_action=none")
    print("status=PASS_NEGATIVE_AUDIT")


if __name__ == "__main__":
    main()
