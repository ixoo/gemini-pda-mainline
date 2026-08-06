#!/usr/bin/env python3
"""Check the default-off MT6797 firmware-owner lease contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0175-soc-mediatek-define-I2C6-firmware-lease-contract.patch"
STATE_OWNER_PATCH = ROOT / "patches/v7.1.3/0192-soc-mediatek-define-MT6797-state-owner-contract.patch"
STATE_HOLD_PATCH = ROOT / "patches/v7.1.3/0193-soc-mediatek-add-MT6797-state-owner-transition-hold.patch"
PCM_ADAPTER_PATCH = ROOT / "patches/v7.1.3/0194-soc-mediatek-add-bounded-MT6797-PCM-admission.patch"
SERIES = ROOT / "patches/series"
DESIGN = Path(__file__).resolve().parents[1] / "DESIGN.md"
START_RESULT = Path(__file__).resolve().parents[1] / "results/pcm-start-contract-20260806.txt"
OWNER_RESULT = Path(__file__).resolve().parents[1] / "results/public-hybrid-owner-source-20260806.txt"
STATE_RESULT = Path(__file__).resolve().parents[1] / "results/public-owner-startup-state-20260806.txt"
ADAPTER_DESIGN = Path(__file__).resolve().parents[1] / "PCM_ADAPTER_DESIGN.md"
ADAPTER_RESULT = Path(__file__).resolve().parents[1] / "results/pcm-adapter-model-20260806.txt"
CLOCK_RESULT = Path(__file__).resolve().parents[1] / "results/mainline-clock-owner-inventory-20260806.txt"
BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/state-owner-transition-hold-buildbox-20260806.txt"
ADAPTER_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/pcm-adapter-shell-buildbox-20260806.txt"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing {label}: {needle}")


def main() -> None:
    patch = PATCH.read_text()
    state_owner_patch = STATE_OWNER_PATCH.read_text()
    state_hold_patch = STATE_HOLD_PATCH.read_text()
    pcm_adapter_patch = PCM_ADAPTER_PATCH.read_text()
    design = DESIGN.read_text()
    start_result = START_RESULT.read_text()
    owner_result = OWNER_RESULT.read_text()
    state_result = STATE_RESULT.read_text()
    adapter_design = ADAPTER_DESIGN.read_text()
    adapter_result = ADAPTER_RESULT.read_text()
    clock_result = CLOCK_RESULT.read_text()
    build_result = BUILD_RESULT.read_text()
    adapter_build_result = ADAPTER_BUILD_RESULT.read_text()
    source = patch[patch.index("diff --git"):]
    state_owner_source = state_owner_patch[state_owner_patch.index("diff --git"):]
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
        ("MT6797_DVFSP_STATE_OWNER_ABI", "state-owner-abi"),
        ("MT6797_DVFSP_STATE_FIELD_ALL", "state-owner-fields"),
        ("mt6797_dvfsp_handoff_state_owner_register", "state-owner-register"),
        ("mt6797_dvfsp_handoff_state_snapshot", "state-owner-snapshot"),
        ("mt6797_dvfsp_handoff_state_validate", "state-owner-validate"),
        ("mt6797_dvfsp_handoff_state_invalidate", "state-owner-invalidate"),
        ("state_owner_ops->snapshot", "state-owner-callback"),
        ("state_owner_ops->invalidate", "state-owner-fault"),
        ("ret = -EOPNOTSUPP", "state-owner-absent"),
        ("This patch adds no clock provider", "state-owner-no-provider"),
    ):
        require(state_owner_patch, needle, label)

    for needle, label in (
        ("struct mt6797_dvfsp_state_hold", "state-hold-struct"),
        ("int (*hold)(", "state-hold-callback"),
        ("int (*release)(", "state-release-callback"),
        ("mt6797_dvfsp_handoff_state_hold", "state-hold-api"),
        ("mt6797_dvfsp_handoff_state_release", "state-release-api"),
        ("state_hold_active", "state-hold-lifetime"),
        ("mt6797_dvfsp_state_hold_check", "state-hold-token-check"),
        ("memcmp(&handoff->state_hold", "state-hold-exact-token"),
        ("a failed\nrelease remains sticky", "state-hold-sticky-description"),
    ):
        require(state_hold_patch, needle, label)

    for needle, label in (
        ("MT6797_DVFSP_PCM_ADAPTER_ABI", "pcm-adapter-abi"),
        ("MT6797_DVFSP_PCM_IMAGE_HASH_BYTES", "pcm-image-hash"),
        ("MT6797_DVFSP_PCM_RESOURCE_ALL", "pcm-resource-mask"),
        ("MT6797_DVFSP_PCM_CSPM_BASE", "pcm-cspm-identity"),
        ("MT6797_DVFSP_PCM_CSRAM_BASE", "pcm-csram-identity"),
        ("MT6797_DVFSP_PCM_PHASE_UNAVAILABLE", "pcm-phase-unavailable"),
        ("MT6797_DVFSP_PCM_PHASE_STATE_HELD", "pcm-phase-state-held"),
        ("MT6797_DVFSP_PCM_PHASE_RESOURCES_HELD", "pcm-phase-resources"),
        ("MT6797_DVFSP_PCM_PHASE_IMAGE_READY", "pcm-phase-image"),
        ("MT6797_DVFSP_PCM_PHASE_RESET_INITIALIZED", "pcm-phase-reset"),
        ("MT6797_DVFSP_PCM_PHASE_IMAGE_ACKED", "pcm-phase-image-ack"),
        ("MT6797_DVFSP_PCM_PHASE_CONTROL_INITIALIZED", "pcm-phase-control"),
        ("MT6797_DVFSP_PCM_PHASE_RUNNING", "pcm-phase-running"),
        ("MT6797_DVFSP_PCM_PHASE_LEASE_REGISTERED", "pcm-phase-lease"),
        ("mt6797_dvfsp_handoff_pcm_adapter_register", "pcm-adapter-register"),
        ("mt6797_dvfsp_handoff_pcm_adapter_start", "pcm-adapter-start"),
        ("mt6797_dvfsp_handoff_pcm_adapter_stop", "pcm-adapter-stop"),
        ("mt6797_dvfsp_handoff_pcm_adapter_invalidate", "pcm-adapter-invalidate"),
        ("mt6797_dvfsp_pcm_resource_check", "pcm-resource-check"),
        ("mt6797_dvfsp_pcm_image_equal", "pcm-image-equality"),
        ("mt6797_dvfsp_pcm_adapter_revalidate_locked", "pcm-generation-revalidation"),
        ("pcm_adapter_sticky_fault", "pcm-sticky-fault"),
        ("All callbacks remain external and unregistered by default", "pcm-default-off-claim"),
    ):
        require(pcm_adapter_patch, needle, label)
    for needle, label in (
        ("## Startup-state adapter seam", "design-state-seam"),
        ("`snapshot`", "design-snapshot"),
        ("`validate`", "design-validate"),
        ("`publish`", "design-publish"),
        ("`invalidate`", "design-invalidate"),
        ("UNAVAILABLE -> SNAPSHOTTED -> RESOURCES_HELD", "design-lifecycle"),
        ("not yet a kernel API", "design-not-implemented"),
    ):
        require(design, needle, label)
    for needle, label in (
        ("required_image_identity=exact_image_hash;target_revision;license_or_access_boundary;loader_domain", "start-image-identity"),
        ("required_memory_contract=stable_physical_base_and_length;alignment;cache_maintenance;lifetime", "start-memory"),
        ("required_resource_contract=CSPM_0x11015000_plus_0x1000;CSRAM_0x0012a000_plus_0x3000;I2C_APPM_clock;EMI_or_semaphore_owner", "start-resources"),
        ("required_start_order=reset_init;IM_PTR_IM_LEN;IM_KICK;FSM_IM_READY;register_event_wakeup_init;PCM_KICK;CSRAM_records", "start-order"),
        ("required_startup_state_owner=authoritative_current_opp;frequency;voltage;vsram;ceiling;floor;cluster_membership;clock_and_rail_state", "start-state-owner"),
        ("required_startup_state_lifetime=sample_under_owner_lock;consistent_with_regulator_and_clock_state;revalidate_after_suspend_resume;invalidate_on_fault", "start-state-lifetime"),
        ("required_runtime_lease=three_SW_PAUSE_bit13;three_FW_DONE_bit15;2ms_bound;generation_bound_owner_handle;paired_release", "start-runtime-lease"),
        ("current_mainline_residency=unproven;CSPM-only-read-only-handoff;CSRAM-unmapped", "start-current-residency"),
        ("current_mainline_start=absent;no_firmware_request;no_image_buffer;no_IM_KICK;no_PCM_KICK;no_CS_RAM_records", "start-current-path"),
        ("current_mainline_startup_state=unproven;no_mt6797_opp_voltage_vsram_owner;generic_opp_core_not_owner", "start-current-state"),
        ("state_owner_contract=0192-dormant;registered_owner=0;incomplete_snapshot_rejected;generation_revalidation;invalidation_reasons=owner_removed|clock_transition|rail_transition|suspend_resume|pcm_fault", "start-state-owner-contract"),
        ("current_mainline_owner=0175-default-unregistered;state_owner=0192-unregistered;registered_owner=0", "start-current-owner"),
        ("direct_handshake_policy=reject_SW_PAUSE_FW_DONE_without_residency_and_start_proof", "start-fail-closed"),
        ("decision=DEFINE_REQUIRED_PCM_START_BOUNDARY;REQUIRE_STARTUP_STATE_OWNER;KEEP_PROVIDER_FAIL_CLOSED", "start-decision"),
        ("status=PASS_PCM_START_CONTRACT_DEFINED", "start-status"),
    ):
        require(start_result, needle, label)

    for needle, label in (
        ("claim=PUBLIC_HYBRID_PCM_STARTUP_STATE_OWNER_REVALIDATED", "state-claim"),
        ("startup_state_api=struct_init_sta;passed_into_kick_dvfsp_path", "state-api"),
        ("startup_state_fields=is_on;init_opp;init_freq;init_volt;init_vsram;ceiling_freq;floor_freq", "state-fields"),
        ("startup_state_records=CSRAM_OFFS_INIT_OPP;CSRAM_OFFS_INIT_FREQ;CSRAM_OFFS_INIT_VOLT;CSRAM_OFFS_INIT_VSRAM;ceiling_and_floor", "state-records"),
        ("dvfs_control_inputs=twam_wfi_init=1;r7_ctrl_en=1;wake_src=WAKE_SRC_TWAM|WAKE_SRC_CPU", "state-control-inputs"),
        ("required_state_owner=authoritative_current_opp;frequency;voltage;vsram;ceiling;floor;cluster_membership;clock_and_rail_state", "state-required-owner"),
        ("mainline_handoff_resources=CSPM_only;I2C_APPM_clock;CSRAM_unmapped", "state-mainline-resources"),
        ("mainline_init_sta_symbol=absent;word_bounded_search", "state-mainline-init"),
        ("mainline_kick_dvfsp_symbol=absent;word_bounded_search", "state-mainline-kick"),
        ("mainline_mt6797_cpufreq_owner=absent;no_MT6797_specific_cpufreq_provider", "state-mainline-cpufreq"),
        ("mainline_mt6797_opp_voltage_vsram_owner=absent;generic_OPP_core_and_unrelated_VSRAM_couplers_only", "state-mainline-rails"),
        ("mainline_cpu_topology=cpu8_cpu9_A72;mediatek_mt6797_psci;A72_power_node_disabled", "state-mainline-topology"),
        ("mainline_rail_nodes=DA9214_legacy_no_CPU_supply_or_OPP_binding;RT5735_VGPU_disabled;GPU_only_mali_supply", "state-mainline-rail-nodes"),
        ("existing_state_observer=mt6797_a72_power;read_only_vproc_snapshot;CPU_ON_denied;not_OPP_or_VSRAM_state_owner", "state-observer-boundary"),
        ("clock_backend_dependency=MT6797_CPU_PLL_mux_divider_provider;MCUMIXED_DVFSP_semaphore_owner;BigiDVFS_SMCCC_backend_for_A72", "state-clock-dependency"),
        ("clock_backend_status=design_only;read_only_contract_next;direct_CPU_PLL_MMIO_unsafe", "state-clock-status"),
        ("opp_calibration_boundary=EEM_PTP_mutable_tables;static_downstream_OPP_table_rejected", "state-opp-boundary"),
        ("decision=ADAPTER_BLOCKED_UNTIL_STARTUP_STATE_OWNER;KEEP_PROVIDER_BLOCKED", "state-decision"),
        ("status=PASS_STARTUP_STATE_DEPENDENCY_IDENTIFIED", "state-status"),
    ):
        require(state_result, needle, label)

    for needle, label in (
        ("## Preconditions", "adapter-preconditions"),
        ("## Admission lifecycle", "adapter-lifecycle"),
        ("UNAVAILABLE", "adapter-unavailable"),
        ("STATE_HELD", "adapter-state-hold"),
        ("RESET_INITIALIZED", "adapter-reset"),
        ("IMAGE_ACKED", "adapter-image-ack"),
        ("CONTROL_INITIALIZED", "adapter-control"),
        ("LEASE_REGISTERED", "adapter-lease"),
        ("Immediately before each irreversible-looking checkpoint", "adapter-revalidation"),
        ("sticky `FAULTED`", "adapter-sticky-fault"),
        ("does not select or copy a firmware image", "adapter-no-image"),
        ("`scripts/pcm_adapter_oracle.py`", "adapter-model"),
    ):
        require(adapter_design, needle, label)

    for needle, label in (
        ("claim=SOURCE_ONLY_BOUNDED_PCM_ADAPTER_ADMISSION", "adapter-claim"),
        ("happy_path=SNAPSHOTTED>STATE_HELD>RESOURCES_HELD>IMAGE_READY>RESET_INITIALIZED>IMAGE_ACKED>CONTROL_INITIALIZED>RUNNING>LEASE_REGISTERED", "adapter-happy-path"),
        ("negative_cases=8", "adapter-negative-cases"),
        ("state_hold=exact_generation_cluster_mask_owner_handle;unregister_blocked_while_active", "adapter-state-hold"),
        ("resource_identity=exact", "adapter-resources"),
        ("generation_revalidation=reject_stale_and_invalidate", "adapter-generation"),
        ("owner_handle=exact_and_generation_bound", "adapter-handle"),
        ("status=PASS_PCM_ADAPTER_MODEL", "adapter-status"),
    ):
        require(adapter_result, needle, label)

    for needle, label in (
        ("claim=MAINLINE_MT6797_CLOCK_STATE_OWNER_INVENTORY", "clock-inventory-claim"),
        ("clock_compatibles=mediatek,mt6797-topckgen;mediatek,mt6797-apmixedsys", "clock-generic-providers"),
        ("mt6797_cpufreq_source=absent", "clock-no-cpufreq"),
        ("protected_clock_owner=absent", "clock-no-protected-owner"),
        ("big_cluster_secure_owner=absent", "clock-no-bigi-owner"),
        ("a72_observer_writes=none", "clock-observer-read-only"),
        ("a72_cpu_on=denied", "clock-observer-denies-cpu-on"),
        ("decision=DO_NOT_EXTEND_GENERIC_CCF_OR_OBSERVER", "clock-decision"),
        ("status=PASS_READ_ONLY_INVENTORY", "clock-status"),
    ):
        require(clock_result, needle, label)

    for needle, label in (
        ("claim=COMPILE_ONLY_DORMANT_STATE_OWNER_TRANSITION_HOLD", "build-claim"),
        ("repository_commit=9ba17484c9312798fdfa7115ec2460664c94200e", "build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "build-origin"),
        ("build_backend=buildbox", "build-backend"),
        ("buildbox_status=validated", "build-status"),
        ("patch_count=182", "build-patch-count"),
        ("artifact=linux-7.1.3-gemini-835255b2e374", "build-artifact"),
        ("dtb_count=119", "build-dtb-count"),
        ("sha256sums=passed", "build-checksums"),
        ("package_fetch=success;validated_package_only", "build-fetch"),
        ("state_owner_contract=0192+0193;dormant;registered_owner=0;transition_hold=defined;no_provider;no_mmio;no_transition", "build-state-owner"),
        ("pcm_adapter_model=pass;negative_cases=8", "build-adapter-model"),
        ("hardware_write=none", "build-no-write"),
        ("device_action=none", "build-no-device"),
        ("boot_candidate=false", "build-not-candidate"),
    ):
        require(build_result, needle, label)

    for needle, label in (
        ("claim=COMPILE_ONLY_BOUNDED_PCM_ADAPTER_SHELL", "adapter-build-claim"),
        ("repository_commit=e1c88a653eab8702817ce71a5fbccc07714afe9d", "adapter-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "adapter-build-origin"),
        ("build_backend=buildbox", "adapter-build-backend"),
        ("buildbox_status=validated", "adapter-build-status"),
        ("patch_count=183", "adapter-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-865cfc786d73", "adapter-build-artifact"),
        ("dtb_count=119", "adapter-build-dtb-count"),
        ("sha256sums=passed", "adapter-build-checksums"),
        ("package_fetch=success;validated_package_only", "adapter-build-fetch"),
        ("pcm_adapter_shell=0194;default_off;registered_adapter=0;no_provider;no_mmio;no_transition", "adapter-build-shell"),
        ("hardware_write=none", "adapter-build-no-write"),
        ("device_action=none", "adapter-build-no-device"),
        ("boot_candidate=false", "adapter-build-not-candidate"),
    ):
        require(adapter_build_result, needle, label)

    for needle, label in (
        ("claim=PUBLIC_GEMIAN_HYBRID_DVFSP_OWNER_REVALIDATED", "owner-claim"),
        ("source_commit=8cfe6596a503612e3332d9c26e292a19525a7f07", "owner-source"),
        ("source_license_basis=repository_COPYING_and_LICENSE_GPLv2;hybrid_header_GPLv2", "owner-license"),
        ("resource_cspm=0x11015000_plus_0x1000", "owner-cspm"),
        ("resource_csram=0x0012a000_plus_0x3000", "owner-csram"),
        ("start_order=reset_and_init_PCM;IM_PTR_IM_LEN;IM_KICK;FSM_IM_READY;PCM_registers;event_vectors;wakeup_events;PCM_KICK;CSRAM_records", "owner-start"),
        ("lease_pause=three_SW_PAUSE_bit13_words;three_FW_DONE_bit15_words;2ms_timeout", "owner-lease"),
        ("historical_descriptor_match=pcm_dvfs_v0.1_160131_02;retained_vendor_ELF_string_match", "owner-descriptor-match"),
        ("reference_target_descriptor=pcm_dvfs_v0.1_160131_02;2025_u32", "owner-reference-target"),
        ("selected_descriptor_for_mainline=unproven", "owner-variant"),
        ("current_mainline_owner=unimplemented", "owner-mainline-state"),
        ("decision=SOURCE_OWNER_IDENTIFIED;KEEP_MAINLINE_PROVIDER_BLOCKED", "owner-decision"),
    ):
        require(owner_result, needle, label)

    if names.index("0174-soc-mediatek-add-I2C6-DVFSP-transfer-lease.patch") >= names.index("0175-soc-mediatek-define-I2C6-firmware-lease-contract.patch"):
        raise AssertionError("firmware lease contract is not after Linux transfer lease")
    if names.index("0191-arm64-arm-P32-publication-from-on-issued-phase.patch") >= names.index("0192-soc-mediatek-define-MT6797-state-owner-contract.patch"):
        raise AssertionError("state-owner contract is not after the current handoff series")
    if names.index("0192-soc-mediatek-define-MT6797-state-owner-contract.patch") >= names.index("0193-soc-mediatek-add-MT6797-state-owner-transition-hold.patch"):
        raise AssertionError("state-owner transition hold is not after the state-owner contract")
    if names.index("0193-soc-mediatek-add-MT6797-state-owner-transition-hold.patch") >= names.index("0194-soc-mediatek-add-bounded-MT6797-PCM-admission.patch"):
        raise AssertionError("PCM adapter shell is not after the transition hold")

    for forbidden in ("readl(", "writel(", "i2c_transfer", "regulator_enable(",
                      "regulator_disable(", "psci_ops.cpu_on", "cpu_up("):
        if forbidden in source:
            raise AssertionError(f"unexpected hardware operation: {forbidden}")
        if forbidden in state_owner_source:
            raise AssertionError(f"unexpected state-owner hardware operation: {forbidden}")
        if forbidden in state_hold_patch:
            raise AssertionError(f"unexpected state-hold hardware operation: {forbidden}")
        if forbidden in pcm_adapter_patch:
            raise AssertionError(f"unexpected PCM adapter hardware operation: {forbidden}")

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
    print("state_owner_contract=0192+0193-dormant;registered_owner=0;no_provider;no_mmio;transition_hold_only")
    print("state_owner_buildbox=validated;transition_hold_compile_only;boot_candidate=false")
    print("pcm_adapter_shell=0194;default_off;registered_adapter=0;no_provider;no_mmio;transition_order_enforced")
    print("pcm_adapter_contract=source-only;bounded-admission-model;callback-registration-gated")
    print("clock_owner_inventory=generic_ccf_only;protected_owner_absent;A72_observer_read_only")
    print("pcm_start_contract=defined;residency_and_start_required_before_callback_registration")
    print("startup_state_owner=unproven;mainline=absent")
    print("historical_owner_source=identified;public_gemian_hybrid")
    print("mainline_owner=unimplemented;provider=blocked")
    print("image_variant=unproven;firmware_redistribution=unproven")
    print("status=PASS_STATIC")


if __name__ == "__main__":
    main()
