#!/usr/bin/env python3
"""Check the default-off MT6797 firmware-owner lease contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0175-soc-mediatek-define-I2C6-firmware-lease-contract.patch"
SERIES = ROOT / "patches/series"
START_RESULT = Path(__file__).resolve().parents[1] / "results/pcm-start-contract-20260806.txt"
OWNER_RESULT = Path(__file__).resolve().parents[1] / "results/public-hybrid-owner-source-20260806.txt"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing {label}: {needle}")


def main() -> None:
    patch = PATCH.read_text()
    start_result = START_RESULT.read_text()
    owner_result = OWNER_RESULT.read_text()
    source = patch[patch.index("diff --git"):]
    names = [Path(line).name for line in SERIES.read_text().splitlines()
             if line and not line.startswith("#")]

    require(patch, "MT6797_DVFSP_I2C6_FW_ABI", "protocol-abi")
    require(patch, "MT6797_DVFSP_I2C6_FW_PAUSE_SOURCE\t0x2", "pause-source")
    require(patch, "MT6797_DVFSP_I2C6_FW_SW_PAUSE_BIT\tBIT(13)", "sw-pause")
    require(patch, "MT6797_DVFSP_I2C6_FW_DONE_BIT\t\tBIT(15)", "fw-done")
    require(patch, "MT6797_DVFSP_I2C6_FW_TIMEOUT_US\t2000", "timeout")
    require(patch, "!ops->acquire || !ops->release", "paired-registration")
    require(patch, "mt6797_dvfsp_i2c6_fw_refusal_valid", "structured-refusal")
    require(patch, "mt6797_dvfsp_handoff_i2c6_fw_fault", "sticky-fault")
    require(patch, "lockdep_assert_held(&handoff->transfer_lock)", "transfer-owner")
    require(patch, "lease->generation != handoff->transfer_generation", "generation-check")
    require(patch, "lease->cookie != handoff->transfer_cookie", "cookie-check")
    require(patch, "handoff->fw_lease_active", "lease-lifetime")
    require(patch, "ret = -EBUSY", "unregister-while-held")
    require(patch, "No callback is registered by this patch", "default-off-claim")
    for needle, label in (
        ("required_image_identity=exact_image_hash;target_revision;license_or_access_boundary;loader_domain", "start-image-identity"),
        ("required_memory_contract=stable_physical_base_and_length;alignment;cache_maintenance;lifetime", "start-memory"),
        ("required_resource_contract=CSPM_0x11015000_plus_0x1000;CSRAM_0x0012a000_plus_0x3000;I2C_APPM_clock;EMI_or_semaphore_owner", "start-resources"),
        ("required_start_order=reset_init;IM_PTR_IM_LEN;IM_KICK;FSM_IM_READY;register_event_wakeup_init;PCM_KICK;CSRAM_records", "start-order"),
        ("required_runtime_lease=three_SW_PAUSE_bit13;three_FW_DONE_bit15;2ms_bound;generation_bound_owner_handle;paired_release", "start-runtime-lease"),
        ("current_mainline_residency=unproven;CSPM-only-read-only-handoff;CSRAM-unmapped", "start-current-residency"),
        ("current_mainline_start=absent;no_firmware_request;no_image_buffer;no_IM_KICK;no_PCM_KICK;no_CS_RAM_records", "start-current-path"),
        ("current_mainline_owner=0175-default-unregistered;registered_owner=0", "start-current-owner"),
        ("direct_handshake_policy=reject_SW_PAUSE_FW_DONE_without_residency_and_start_proof", "start-fail-closed"),
        ("decision=DEFINE_REQUIRED_PCM_START_BOUNDARY;KEEP_PROVIDER_FAIL_CLOSED", "start-decision"),
        ("status=PASS_PCM_START_CONTRACT_DEFINED", "start-status"),
    ):
        require(start_result, needle, label)

    for needle, label in (
        ("claim=PUBLIC_GEMIAN_HYBRID_DVFSP_OWNER_REVALIDATED", "owner-claim"),
        ("source_commit=8cfe6596a503612e3332d9c26e292a19525a7f07", "owner-source"),
        ("resource_cspm=0x11015000_plus_0x1000", "owner-cspm"),
        ("resource_csram=0x0012a000_plus_0x3000", "owner-csram"),
        ("start_order=reset_and_init_PCM;IM_PTR_IM_LEN;IM_KICK;FSM_IM_READY;PCM_registers;event_vectors;wakeup_events;PCM_KICK;CSRAM_records", "owner-start"),
        ("lease_pause=three_SW_PAUSE_bit13_words;three_FW_DONE_bit15_words;2ms_timeout", "owner-lease"),
        ("historical_descriptor_match=pcm_dvfs_v0.1_160131_02;retained_vendor_ELF_string_match", "owner-descriptor-match"),
        ("selected_descriptor_for_mainline=unproven", "owner-variant"),
        ("current_mainline_owner=unimplemented", "owner-mainline-state"),
        ("decision=SOURCE_OWNER_IDENTIFIED;KEEP_MAINLINE_PROVIDER_BLOCKED", "owner-decision"),
    ):
        require(owner_result, needle, label)

    if names.index("0174-soc-mediatek-add-I2C6-DVFSP-transfer-lease.patch") >= names.index("0175-soc-mediatek-define-I2C6-firmware-lease-contract.patch"):
        raise AssertionError("firmware lease contract is not after Linux transfer lease")

    for forbidden in ("readl(", "writel(", "i2c_transfer", "regulator_enable(",
                      "regulator_disable(", "psci_ops.cpu_on", "cpu_up("):
        if forbidden in source:
            raise AssertionError(f"unexpected hardware operation: {forbidden}")

    print("claim=PARTIAL_FIRMWARE_LEASE_CALLBACK_CONTRACT")
    print("registered_owner=0")
    print("pause_source=0x2")
    print("sw_pause_bit=13")
    print("fw_done_bit=15")
    print("timeout_us=2000")
    print("acquire_words=3_pause;3_fw_done")
    print("release_requires_same_owner_handle=1")
    print("hardware_writes=0")
    print("device_action=none")
    print("pcm_start_contract=defined;residency_and_start_required_before_callback_registration")
    print("historical_owner_source=identified;public_gemian_hybrid")
    print("mainline_owner=unimplemented;provider=blocked")
    print("image_variant=unproven;firmware_redistribution=unproven")
    print("status=PASS_STATIC")


if __name__ == "__main__":
    main()
