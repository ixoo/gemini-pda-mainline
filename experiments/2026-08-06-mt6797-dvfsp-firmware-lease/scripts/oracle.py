#!/usr/bin/env python3
"""Check the default-off MT6797 firmware-owner lease contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0175-soc-mediatek-define-I2C6-firmware-lease-contract.patch"
STATE_OWNER_PATCH = ROOT / "patches/v7.1.3/0192-soc-mediatek-define-MT6797-state-owner-contract.patch"
STATE_HOLD_PATCH = ROOT / "patches/v7.1.3/0193-soc-mediatek-add-MT6797-state-owner-transition-hold.patch"
PCM_ADAPTER_PATCH = ROOT / "patches/v7.1.3/0194-soc-mediatek-add-bounded-MT6797-PCM-admission.patch"
STATE_IDENTITY_PATCH = ROOT / "patches/v7.1.3/0195-soc-mediatek-require-protected-state-owner-identity.patch"
STATE_BACKEND_PATCH = ROOT / "patches/v7.1.3/0196-soc-mediatek-compose-protected-state-backends.patch"
CLOCK_READBACK_PATCH = ROOT / "patches/v7.1.3/0197-soc-mediatek-add-disabled-MT6797-protected-clock-readback.patch"
BIGIDVFS_READBACK_PATCH = ROOT / "patches/v7.1.3/0198-soc-mediatek-add-disabled-MT6797-BigiDVFS-readback.patch"
TRANSITION_OWNER_PATCH = ROOT / "patches/v7.1.3/0199-soc-mediatek-bind-protected-state-to-transition-owner.patch"
PROVENANCE_PATCH = ROOT / "patches/v7.1.3/0200-soc-mediatek-require-calibrated-state-provenance.patch"
CALIBRATION_LIFECYCLE_PATCH = ROOT / "patches/v7.1.3/0201-soc-mediatek-bind-calibration-lifecycle-to-state-owner.patch"
TRANSITION_LOCK_PATCH = ROOT / "patches/v7.1.3/0202-soc-mediatek-bind-protected-owner-to-transition-lock.patch"
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
IDENTITY_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/state-owner-identity-buildbox-20260806.txt"
STATE_BACKEND_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/protected-state-backend-composition-buildbox-20260806.txt"
PROTOCOL_RESULT = Path(__file__).resolve().parents[1] / "results/protected-owner-protocol-20260806.txt"
DVFS_STATE_RESULT = Path(__file__).resolve().parents[1] / "results/public-dvfs-state-owner-20260806.txt"
READBACK_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/protected-readback-buildbox-20260806.txt"
TRANSITION_OWNER_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/protected-transition-owner-buildbox-20260806.txt"
PROVENANCE_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/calibrated-state-provenance-buildbox-20260806.txt"
CALIBRATION_LIFECYCLE_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/calibration-lifecycle-buildbox-20260806.txt"
TRANSITION_LOCK_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/transition-lock-buildbox-20260806.txt"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing {label}: {needle}")


def main() -> None:
    patch = PATCH.read_text()
    state_owner_patch = STATE_OWNER_PATCH.read_text()
    state_hold_patch = STATE_HOLD_PATCH.read_text()
    pcm_adapter_patch = PCM_ADAPTER_PATCH.read_text()
    state_identity_patch = STATE_IDENTITY_PATCH.read_text()
    state_backend_patch = STATE_BACKEND_PATCH.read_text()
    clock_readback_patch = CLOCK_READBACK_PATCH.read_text()
    bigidvfs_readback_patch = BIGIDVFS_READBACK_PATCH.read_text()
    transition_owner_patch = TRANSITION_OWNER_PATCH.read_text()
    provenance_patch = PROVENANCE_PATCH.read_text()
    calibration_lifecycle_patch = CALIBRATION_LIFECYCLE_PATCH.read_text()
    transition_lock_patch = TRANSITION_LOCK_PATCH.read_text()
    design = DESIGN.read_text()
    start_result = START_RESULT.read_text()
    owner_result = OWNER_RESULT.read_text()
    state_result = STATE_RESULT.read_text()
    adapter_design = ADAPTER_DESIGN.read_text()
    adapter_result = ADAPTER_RESULT.read_text()
    clock_result = CLOCK_RESULT.read_text()
    build_result = BUILD_RESULT.read_text()
    adapter_build_result = ADAPTER_BUILD_RESULT.read_text()
    identity_build_result = IDENTITY_BUILD_RESULT.read_text()
    state_backend_build_result = STATE_BACKEND_BUILD_RESULT.read_text()
    protocol_result = PROTOCOL_RESULT.read_text()
    dvfs_state_result = DVFS_STATE_RESULT.read_text()
    readback_build_result = READBACK_BUILD_RESULT.read_text()
    transition_owner_build_result = TRANSITION_OWNER_BUILD_RESULT.read_text()
    provenance_build_result = PROVENANCE_BUILD_RESULT.read_text()
    calibration_lifecycle_build_result = CALIBRATION_LIFECYCLE_BUILD_RESULT.read_text()
    transition_lock_build_result = TRANSITION_LOCK_BUILD_RESULT.read_text()
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
        ("MT6797_DVFSP_STATE_OWNER_IDENTITY_ABI", "state-owner-identity-abi"),
        ("MT6797_DVFSP_STATE_OWNER_RESOURCE_ALL", "state-owner-identity-resources"),
        ("MT6797_DVFSP_STATE_OWNER_BACKEND_MCUMIXED_DVFSP", "state-owner-cpu-pll-backend"),
        ("MT6797_DVFSP_STATE_OWNER_BACKEND_BIGIDVFS_SMCCC", "state-owner-bigi-backend"),
        ("struct mt6797_dvfsp_state_owner_identity", "state-owner-identity-struct"),
        ("int (*identify)(", "state-owner-identify-callback"),
        ("mt6797_dvfsp_state_owner_identity_check", "state-owner-identity-check"),
        ("!ops->identify", "state-owner-identity-required"),
        ("handoff->state_owner_identity", "state-owner-identity-retained"),
        ("mt6797_dvfsp_handoff_state_owner_identity", "state-owner-identity-api"),
        ("does not implement either backend", "state-owner-identity-no-backend"),
    ):
        require(state_identity_patch, needle, label)
    for needle, label in (
        ("MT6797_DVFSP_STATE_BACKEND_ABI", "state-backend-abi"),
        ("MT6797_DVFSP_STATE_BACKEND_CPU_PLL_CLUSTERS", "state-backend-cpu-clusters"),
        ("MT6797_DVFSP_STATE_BACKEND_BIG_CLUSTER_CLUSTERS", "state-backend-big-cluster"),
        ("struct mt6797_dvfsp_state_backend_snapshot", "state-backend-snapshot"),
        ("struct mt6797_dvfsp_state_backend_ops", "state-backend-ops"),
        ("struct mt6797_dvfsp_protected_state_owner", "protected-owner-struct"),
        ("mt6797_dvfsp_state_backend_check", "state-backend-check"),
        ("mt6797_dvfsp_protected_state_owner_collect", "protected-owner-collect"),
        ("cpu_snapshot->generation != big_snapshot->generation", "state-backend-generation-match"),
        ("cpu_snapshot->cluster_mask & big_snapshot->cluster_mask", "state-backend-disjoint-clusters"),
        ("mt6797_dvfsp_protected_state_owner_release_pair", "state-backend-paired-release"),
        ("mt6797_dvfsp_protected_state_owner_register", "protected-owner-register"),
        ("mt6797_dvfsp_protected_state_owner_unregister", "protected-owner-unregister"),
        ("No caller registers this owner", "protected-owner-default-off"),
    ):
        require(state_backend_patch, needle, label)

    for needle, label in (
        ("MT6797_DVFSP_CLOCK_BACKEND_ABI", "clock-readback-abi"),
        ("MT6797_DVFSP_SEMAPHORE_RETRIES", "clock-readback-bound"),
        ("MT6797_DVFSP_SEMAPHORE_HELD", "clock-readback-semaphore"),
        ("mt6797_dvfsp_clock_mark_fault", "clock-readback-sticky-fault"),
        ("status = \"disabled\"", "clock-readback-node-disabled"),
        ("register a DVFSP state owner or clock provider", "clock-readback-no-owner"),
    ):
        require(clock_readback_patch, needle, label)

    for needle, label in (
        ("MT6797_BIGIDVFS_BACKEND_ABI", "bigidvfs-readback-abi"),
        ("MT6797_BIGIDVFS_FID_READ", "bigidvfs-readback-fid"),
        ("MT6797_BIGIDVFS_PLL_PCW", "bigidvfs-readback-pcw"),
        ("MT6797_BIGIDVFS_PLL_ENABLE_POSDIV", "bigidvfs-readback-posdiv"),
        ("MT6797_BIGIDVFS_SRAM_SELECTOR", "bigidvfs-readback-sram"),
        ("MT6797_BIGIDVFS_CONTROL", "bigidvfs-readback-control"),
        ("mt6797_bigidvfs_address_allowed", "bigidvfs-readback-whitelist"),
        ("result.a0 >> 32", "bigidvfs-readback-return-check"),
        ("mt6797_bigidvfs_mark_fault", "bigidvfs-readback-sticky-fault"),
        ("status = \"disabled\"", "bigidvfs-readback-node-disabled"),
        ("never calls a secure write", "bigidvfs-readback-no-write"),
    ):
        require(bigidvfs_readback_patch, needle, label)
    if "0xc200035e" in bigidvfs_readback_patch or "FID_WRITE" in bigidvfs_readback_patch:
        raise AssertionError("BigiDVFS readback transport contains a secure write identifier")
    for needle, label in (
        ("transition_handle", "transition-handle-field"),
        ("!hold->transition_handle", "transition-hold-required"),
        ("!identity->transition_handle", "identity-transition-required"),
        ("!snapshot->transition_handle", "backend-transition-required"),
        ("!owner->transition_handle", "owner-transition-required"),
        ("cpu_snapshot->transition_handle != owner->transition_handle", "cpu-transition-match"),
        ("big_snapshot->transition_handle != owner->transition_handle", "big-transition-match"),
        ("identity->transition_handle = owner->transition_handle", "identity-transition-echo"),
        ("cpu_hold.transition_handle != owner->transition_handle", "cpu-hold-transition"),
        ("big_hold.transition_handle != owner->transition_handle", "big-hold-transition"),
        ("hold->transition_handle = owner->transition_handle", "hold-transition-echo"),
    ):
        require(transition_owner_patch, needle, label)
    for needle, label in (
        ("MT6797_DVFSP_STATE_PROVENANCE_ABI", "provenance-abi"),
        ("MT6797_DVFSP_STATE_PROVENANCE_SOURCE_ALL", "provenance-source-mask"),
        ("MT6797_DVFSP_STATE_PROVENANCE_EFUSE_VARIANT", "provenance-efuse"),
        ("MT6797_DVFSP_STATE_PROVENANCE_EEM_PTP", "provenance-eem-ptp"),
        ("MT6797_DVFSP_STATE_PROVENANCE_PPM_LIMIT", "provenance-ppm"),
        ("MT6797_DVFSP_STATE_PROVENANCE_LIVE_VPROC", "provenance-vproc"),
        ("MT6797_DVFSP_STATE_PROVENANCE_LIVE_VSRAM", "provenance-vsram"),
        ("MT6797_DVFSP_STATE_PROVENANCE_CLOCK_OWNER", "provenance-clock-owner"),
        ("MT6797_DVFSP_STATE_PROVENANCE_RAIL_OWNER", "provenance-rail-owner"),
        ("struct mt6797_dvfsp_state_provenance", "provenance-struct"),
        ("calibration_handle", "provenance-calibration-handle"),
        ("table_epoch", "provenance-table-epoch"),
        ("mt6797_dvfsp_state_provenance_check", "provenance-check"),
        ("!provenance->table_epoch || !provenance->calibration_handle", "provenance-required"),
        ("mt6797_dvfsp_state_provenance_equal", "provenance-equality"),
        ("!mt6797_dvfsp_state_provenance_equal(&cpu_snapshot->provenance", "provenance-backend-match"),
        ("identity->provenance = owner->provenance", "provenance-identity-echo"),
    ):
        require(provenance_patch, needle, label)
    for needle, label in (
        ("MT6797_DVFSP_STATE_CALIBRATION_ABI", "calibration-owner-abi"),
        ("struct mt6797_dvfsp_state_calibration_hold", "calibration-hold"),
        ("struct mt6797_dvfsp_state_calibration_ops", "calibration-ops"),
        ("calibration_ops->snapshot", "calibration-snapshot"),
        ("calibration_ops->validate", "calibration-validate"),
        ("calibration_ops->hold", "calibration-hold-callback"),
        ("calibration_ops->release", "calibration-release-callback"),
        ("calibration_ops->invalidate", "calibration-invalidate"),
        ("calibration_ops->abi", "calibration-abi-check"),
        ("cpu_snapshot->provenance", "calibration-backend-match"),
        ("snapshot->provenance = provenance", "calibration-snapshot-echo"),
        ("hold->provenance = fresh.provenance", "calibration-hold-echo"),
        ("!mt6797_dvfsp_state_provenance_equal(&hold->provenance", "calibration-hold-check"),
        ("provider is registered by default", "calibration-default-off"),
    ):
        require(calibration_lifecycle_patch, needle, label)
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
        ("claim=COMPILE_ONLY_PROTECTED_STATE_OWNER_IDENTITY", "identity-build-claim"),
        ("repository_commit=5e94f04a7be68a20c45b27e0743ac88da42fb4a4", "identity-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "identity-build-origin"),
        ("build_backend=buildbox", "identity-build-backend"),
        ("buildbox_status=validated", "identity-build-status"),
        ("patch_count=184", "identity-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-995a08e97932", "identity-build-artifact"),
        ("dtb_count=119", "identity-build-dtb-count"),
        ("sha256sums=passed", "identity-build-checksums"),
        ("package_fetch=success;validated_package_only", "identity-build-fetch"),
        ("state_owner_identity=0195;default_off;exact_mcumixed_dvfsp_and_bigidvfs;registered_owner=0;no_provider;no_mmio", "identity-build-gate"),
        ("hardware_write=none", "identity-build-no-write"),
        ("device_action=none", "identity-build-no-device"),
        ("boot_candidate=false", "identity-build-not-candidate"),
    ):
        require(identity_build_result, needle, label)

    for needle, label in (
        ("claim=COMPILE_ONLY_PROTECTED_STATE_BACKEND_COMPOSITION", "backend-build-claim"),
        ("repository_commit=06f0a87a6d9c9f71bf2f7ac5907f8f01241dd522", "backend-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "backend-build-origin"),
        ("build_backend=buildbox", "backend-build-backend"),
        ("buildbox_status=validated", "backend-build-status"),
        ("patch_count=185", "backend-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-88e6a33574c5", "backend-build-artifact"),
        ("dtb_count=119", "backend-build-dtb-count"),
        ("sha256sums=passed", "backend-build-checksums"),
        ("package_fetch=success;validated_package_only", "backend-build-fetch"),
        ("state_backend_composition=0196;default_off;cpu_pll_mcumixed_dvfsp;big_cluster_bigidvfs_smccc;exact_disjoint_cluster_masks;generation_and_owner_handle_checked", "backend-build-composition"),
        ("registered_owner=0", "backend-build-owner-unregistered"),
        ("provider=none", "backend-build-no-provider"),
        ("mmio=none", "backend-build-no-mmio"),
        ("secure_call=none", "backend-build-no-secure-call"),
        ("hardware_write=none", "backend-build-no-write"),
        ("device_action=none", "backend-build-no-device"),
        ("boot_candidate=false", "backend-build-not-candidate"),
    ):
        require(state_backend_build_result, needle, label)

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

    for needle, label in (
        ("claim=PROTECTED_OWNER_PROTOCOL_REVALIDATED", "protocol-claim"),
        ("source_commit=8cfe6596a503612e3332d9c26e292a19525a7f07", "protocol-source"),
        ("bigi_fid_enable=0xc20003b0;args=idvfs_ctrl,vproc_mv_x100,vsram_mv_x100", "protocol-bigi-enable"),
        ("bigi_fid_pll_set_frequency=0xc20003b8;args=frequency_mhz", "protocol-bigi-pll"),
        ("bigi_fid_sram_ldo_set=0xc20003bf;args=vsram_mv_x100", "protocol-bigi-sram"),
        ("bigi_fid_read=0xc200035f;args=secure_register_address", "protocol-bigi-read"),
        ("bigi_fid_write=0xc200035e;args=secure_register_address,value", "protocol-bigi-write"),
        ("mcumixed_base=0x1001a000;length=0x1000", "protocol-mcumixed"),
        ("semaphore_register=cspm_base_plus_0x440;hardware_semaphore=3_M0", "protocol-semaphore"),
        ("acquire=write_1;read_bit0;retry_every_10us;200_iterations;timeout=2000us", "protocol-acquire"),
        ("serialization=local_irq_save;kernel_spinlock;release_before_irq_restore", "protocol-serialization"),
        ("shared_owners=kernel;SPM;ATF", "protocol-shared-owners"),
        ("authoritative_state=missing;OPP;frequency;voltage;VSRAM;ceiling;floor;cluster_membership;clock_and_rail_state", "protocol-state-gap"),
        ("decision=DO_NOT_REGISTER_WRITABLE_OWNER;KEEP_PROVIDER_AND_CPU8_CPU9_ADMISSION_BLOCKED", "protocol-decision"),
        ("status=PASS_PROTOCOL_IDENTITIES_OWNER_IMPLEMENTATION_BLOCKED", "protocol-status"),
    ):
        require(protocol_result, needle, label)

    for needle, label in (
        ("claim=PUBLIC_DVFS_STATE_OWNER_REVALIDATED", "dvfs-state-claim"),
        ("source_commit=8cfe6596a503612e3332d9c26e292a19525a7f07", "dvfs-state-source"),
        ("state_function=__set_cpuhvfs_init_sta", "dvfs-state-function"),
        ("state_fields=opp;freq;volt;vsram;ceiling;floor;is_on", "dvfs-state-fields"),
        ("transition_lock=cpufreq_mutex;mutex_lock;is_in_cpufreq=1", "dvfs-transition-lock"),
        ("transition_scope=_mt_cpufreq_set;voltage_up;frequency_and_CCI;voltage_down;opp_index_publication", "dvfs-transition-scope"),
        ("state_table_inputs=efuse_date_code;efuse_function_code;EEM_PTP_mutable_voltage_tables;PPM_limits", "dvfs-calibration-inputs"),
        ("mainline_cpufreq_owner=absent;Linux_7.1.3_has_no_MT6797_specific_driver", "dvfs-mainline-gap"),
        ("static_table_policy=reject;source_has_calibration_and_mutable_PPM_limits", "dvfs-static-table-rejection"),
        ("decision=KEEP_0196_OWNER_UNREGISTERED;KEEP_PROVIDER_AND_CPU8_CPU9_ADMISSION_BLOCKED", "dvfs-decision"),
        ("status=PASS_HISTORICAL_STATE_OWNER_MAINLINE_GAP_OPEN", "dvfs-status"),
    ):
        require(dvfs_state_result, needle, label)

    for needle, label in (
        ("claim=COMPILE_ONLY_PROTECTED_READBACK_TRANSPORTS", "readback-build-claim"),
        ("repository_commit=43b596a4940572d309a53055502a596fef13e7d8", "readback-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "readback-build-origin"),
        ("build_backend=buildbox", "readback-build-backend"),
        ("buildbox_status=validated", "readback-build-status"),
        ("patch_count=187", "readback-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-c34aa0be-11afba8d", "readback-build-artifact"),
        ("dtb_count=119", "readback-build-dtb-count"),
        ("sha256sums=passed", "readback-build-checksums"),
        ("package_fetch=success;validated_package_only", "readback-build-fetch"),
        ("clock_transport=0197;default_off;mcumixed_cspm;bounded_semaphore_readback", "readback-clock"),
        ("bigidvfs_transport=0198;default_off;smc_0xc200035f;four_address_whitelist;read_only", "readback-bigidvfs"),
        ("nodes=dvfsp-clock-backend:disabled;dvfsp-bigidvfs-backend:disabled", "readback-nodes"),
        ("owner=unregistered", "readback-owner"),
        ("secure_write=none", "readback-no-write"),
        ("hardware_write=none", "readback-hardware-no-write"),
        ("device_action=none", "readback-no-device"),
        ("boot_candidate=false", "readback-not-candidate"),
    ):
        require(readback_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_PROTECTED_TRANSITION_OWNER_CONTRACT", "transition-build-claim"),
        ("repository_commit=8f0aadfec73b7f36ad4c5bf613ffbfd6b27a35df", "transition-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "transition-build-origin"),
        ("build_backend=buildbox", "transition-build-backend"),
        ("buildbox_status=validated", "transition-build-status"),
        ("patch_count=188", "transition-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-650b9b01-11afba8d", "transition-build-artifact"),
        ("dtb_count=119", "transition-build-dtb-count"),
        ("sha256sums=passed", "transition-build-checksums"),
        ("package_fetch=success;validated_package_only", "transition-build-fetch"),
        ("transition_contract=0199;shared_transition_handle;generation_bound;both_protected_backends;all_holds;default_off", "transition-build-contract"),
        ("owner=unregistered", "transition-build-owner-unregistered"),
        ("provider=none", "transition-build-no-provider"),
        ("secure_write=none", "transition-build-no-secure-write"),
        ("hardware_write=none", "transition-build-no-write"),
        ("device_action=none", "transition-build-no-device"),
        ("boot_candidate=false", "transition-build-not-candidate"),
    ):
        require(transition_owner_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_CALIBRATED_STATE_PROVENANCE", "provenance-build-claim"),
        ("repository_commit=4cecc04bdcf52a4f150b1355ac4cf84a5330f331", "provenance-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "provenance-build-origin"),
        ("build_backend=buildbox", "provenance-build-backend"),
        ("buildbox_status=validated", "provenance-build-status"),
        ("patch_count=189", "provenance-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-2a9f732e-11afba8d", "provenance-build-artifact"),
        ("dtb_count=119", "provenance-build-dtb-count"),
        ("sha256sums=passed", "provenance-build-checksums"),
        ("package_fetch=success;validated_package_only", "provenance-build-fetch"),
        ("calibration_contract=0200;all_required_sources;mutable_table_epoch;calibration_handle;backend_provenance_match;default_off", "provenance-build-contract"),
        ("required_sources=efuse_variant;EEM_PTP;PPM_limit;live_VPROC;live_VSRAM;clock_owner;rail_owner", "provenance-build-sources"),
        ("owner=unregistered", "provenance-build-owner-unregistered"),
        ("provider=none", "provenance-build-no-provider"),
        ("secure_write=none", "provenance-build-no-secure-write"),
        ("hardware_write=none", "provenance-build-no-write"),
        ("device_action=none", "provenance-build-no-device"),
        ("boot_candidate=false", "provenance-build-not-candidate"),
    ):
        require(provenance_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_CALIBRATION_LIFECYCLE_ADMISSION_BOUNDARY", "calibration-lifecycle-build-claim"),
        ("repository_commit=f984738e2c73222c4d96e69a844591e825b7a3f6", "calibration-lifecycle-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "calibration-lifecycle-build-origin"),
        ("build_backend=buildbox", "calibration-lifecycle-build-backend"),
        ("buildbox_status=validated", "calibration-lifecycle-build-status"),
        ("patch_count=190", "calibration-lifecycle-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-3a9ff77d-11afba8d", "calibration-lifecycle-build-artifact"),
        ("dtb_count=119", "calibration-lifecycle-build-dtb-count"),
        ("sha256sums=passed", "calibration-lifecycle-build-checksums"),
        ("package_fetch=success;validated_package_only", "calibration-lifecycle-build-fetch"),
        ("calibration_contract=0200;required_provenance;mutable_table_epoch;calibration_handle;backend_match;default_off", "calibration-lifecycle-build-contract"),
        ("calibration_lifecycle_contract=0201;snapshot_validate_hold_release_invalidate;exact_provenance_generation_transition_owner_echo", "calibration-lifecycle-build-lifecycle"),
        ("owner=unregistered", "calibration-lifecycle-build-owner-unregistered"),
        ("provider=none", "calibration-lifecycle-build-no-provider"),
        ("secure_write=none", "calibration-lifecycle-build-no-secure-write"),
        ("hardware_write=none", "calibration-lifecycle-build-no-write"),
        ("device_action=none", "calibration-lifecycle-build-no-device"),
        ("boot_candidate=false", "calibration-lifecycle-build-not-candidate"),
    ):
        require(calibration_lifecycle_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_PROTECTED_OWNER_TRANSITION_LOCK_BOUNDARY", "transition-lock-build-claim"),
        ("repository_commit=d85cffe8f48d145df67b6d4eacfbb4f08abf603d", "transition-lock-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "transition-lock-build-origin"),
        ("build_backend=buildbox", "transition-lock-build-backend"),
        ("buildbox_status=validated", "transition-lock-build-status"),
        ("patch_count=191", "transition-lock-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-285eddaa-11afba8d", "transition-lock-build-artifact"),
        ("dtb_count=119", "transition-lock-build-dtb-count"),
        ("sha256sums=passed", "transition-lock-build-checksums"),
        ("package_fetch=success;validated_package_only", "transition-lock-build-fetch"),
        ("calibration_contract=0200;required_provenance;mutable_table_epoch;calibration_handle;backend_match;default_off", "transition-lock-build-calibration"),
        ("calibration_lifecycle_contract=0201;snapshot_validate_hold_release_invalidate;exact_provenance_generation_transition_owner_echo", "transition-lock-build-lifecycle"),
        ("transition_lock_contract=0202;external_lock_unlock;composite_snapshot_validate_hold_release;failed_cpu_hold_rollback;default_off", "transition-lock-build-contract"),
        ("owner=unregistered", "transition-lock-build-owner-unregistered"),
        ("provider=none", "transition-lock-build-no-provider"),
        ("secure_write=none", "transition-lock-build-no-secure-write"),
        ("hardware_write=none", "transition-lock-build-no-write"),
        ("device_action=none", "transition-lock-build-no-device"),
        ("boot_candidate=false", "transition-lock-build-not-candidate"),
    ):
        require(transition_lock_build_result, needle, label)
    for needle, label in (
        ("repeat_run_repository_commit=6c3cb4fad5a4895f6a69d7913089553b6751e34c", "readback-repeat-commit"),
        ("repeat_run_buildbox_job=6c3cb4fad5a4895f6a69d7913089553b6751e34c-dvfsp-protected-readback-m0", "readback-repeat-job"),
        ("repeat_run_status=validated", "readback-repeat-status"),
        ("repeat_run_generated_utc=2026-08-06T19:41:20Z", "readback-repeat-time"),
        ("repeat_run_patch_count=187", "readback-repeat-patch-count"),
        ("repeat_run_artifact=linux-7.1.3-gemini-dvfsp-protected-readback-c34aa0be-11afba8d", "readback-repeat-artifact"),
        ("repeat_run_dtb_count=119", "readback-repeat-dtb-count"),
        ("repeat_run_sha256sums=passed", "readback-repeat-checksums"),
        ("repeat_run_package_fetch=success;validated_package_only", "readback-repeat-fetch"),
        ("repeat_run_hardware_write=none", "readback-repeat-no-write"),
        ("repeat_run_device_action=none", "readback-repeat-no-device"),
        ("repeat_run_boot_candidate=false", "readback-repeat-not-candidate"),
    ):
        require(readback_build_result, needle, label)

    if names.index("0174-soc-mediatek-add-I2C6-DVFSP-transfer-lease.patch") >= names.index("0175-soc-mediatek-define-I2C6-firmware-lease-contract.patch"):
        raise AssertionError("firmware lease contract is not after Linux transfer lease")
    if names.index("0191-arm64-arm-P32-publication-from-on-issued-phase.patch") >= names.index("0192-soc-mediatek-define-MT6797-state-owner-contract.patch"):
        raise AssertionError("state-owner contract is not after the current handoff series")
    if names.index("0192-soc-mediatek-define-MT6797-state-owner-contract.patch") >= names.index("0193-soc-mediatek-add-MT6797-state-owner-transition-hold.patch"):
        raise AssertionError("state-owner transition hold is not after the state-owner contract")
    if names.index("0193-soc-mediatek-add-MT6797-state-owner-transition-hold.patch") >= names.index("0194-soc-mediatek-add-bounded-MT6797-PCM-admission.patch"):
        raise AssertionError("PCM adapter shell is not after the transition hold")
    if names.index("0194-soc-mediatek-add-bounded-MT6797-PCM-admission.patch") >= names.index("0195-soc-mediatek-require-protected-state-owner-identity.patch"):
        raise AssertionError("protected state-owner identity is not after the PCM adapter shell")
    if names.index("0195-soc-mediatek-require-protected-state-owner-identity.patch") >= names.index("0196-soc-mediatek-compose-protected-state-backends.patch"):
        raise AssertionError("protected state-backend composition is not after the owner identity gate")
    if names.index("0196-soc-mediatek-compose-protected-state-backends.patch") >= names.index("0197-soc-mediatek-add-disabled-MT6797-protected-clock-readback.patch"):
        raise AssertionError("clock readback transport is not after protected composition")
    if names.index("0197-soc-mediatek-add-disabled-MT6797-protected-clock-readback.patch") >= names.index("0198-soc-mediatek-add-disabled-MT6797-BigiDVFS-readback.patch"):
        raise AssertionError("BigiDVFS readback transport is not after clock readback")
    if names.index("0198-soc-mediatek-add-disabled-MT6797-BigiDVFS-readback.patch") >= names.index("0199-soc-mediatek-bind-protected-state-to-transition-owner.patch"):
        raise AssertionError("transition-owner contract is not after BigiDVFS readback")
    if names.index("0199-soc-mediatek-bind-protected-state-to-transition-owner.patch") >= names.index("0200-soc-mediatek-require-calibrated-state-provenance.patch"):
        raise AssertionError("calibrated provenance contract is not after transition-owner contract")
    if names.index("0200-soc-mediatek-require-calibrated-state-provenance.patch") >= names.index("0201-soc-mediatek-bind-calibration-lifecycle-to-state-owner.patch"):
        raise AssertionError("calibration lifecycle is not after calibrated provenance contract")
    if names.index("0201-soc-mediatek-bind-calibration-lifecycle-to-state-owner.patch") >= names.index("0202-soc-mediatek-bind-protected-owner-to-transition-lock.patch"):
        raise AssertionError("transition lock is not after calibration lifecycle")

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
        if forbidden in state_identity_patch:
            raise AssertionError(f"unexpected state-owner identity hardware operation: {forbidden}")
        if forbidden in state_backend_patch:
            raise AssertionError(f"unexpected protected state-backend hardware operation: {forbidden}")
        if forbidden in transition_owner_patch:
            raise AssertionError(f"unexpected transition-owner hardware operation: {forbidden}")
        if forbidden in provenance_patch:
            raise AssertionError(f"unexpected provenance hardware operation: {forbidden}")
        if forbidden in calibration_lifecycle_patch:
            raise AssertionError(f"unexpected calibration lifecycle hardware operation: {forbidden}")
        if forbidden in transition_lock_patch:
            raise AssertionError(f"unexpected transition-lock hardware operation: {forbidden}")

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
    print("state_owner_identity=0195;default_off;exact_mcumixed_dvfsp_and_bigidvfs;registered_owner=0;no_provider;no_mmio")
    print("state_owner_identity_buildbox=validated;compile_only;registered_owner=0;no_provider;no_mmio;boot_candidate=false")
    print("state_backend_composition=0196;default_off;exact_disjoint_cpu_pll_and_big_cluster_masks;generation_and_owner_handle_checked;registered_owner=0;no_provider;no_mmio")
    print("state_backend_composition_buildbox=validated;compile_only;registered_owner=0;no_provider;no_mmio;boot_candidate=false")
    print("protected_readback=0197+0198;compile_only;both_nodes_disabled;clock_semaphore_and_bigidvfs_reg_read_only;registered_owner=0;no_provider;no_secure_write;boot_candidate=false")
    print("protected_transition_owner=0199;shared_transition_handle;generation_bound;both_protected_backends;all_holds;registered_owner=0;no_provider;no_secure_write;boot_candidate=false")
    print("calibrated_state_provenance=0200;all_required_sources;mutable_table_epoch;calibration_handle;backend_provenance_match;registered_owner=0;no_provider;no_secure_write;boot_candidate=false")
    print("calibration_lifecycle=0201;provenance_snapshot_validate_hold_release;backend_echo_required;registered_owner=0;no_provider;no_mmio;boot_candidate=false")
    print("transition_lock=0202;external_lock_unlock;composite_snapshot_validate_hold_release;registered_owner=0;no_provider;no_mmio;boot_candidate=false")
    print("pcm_adapter_contract=source-only;bounded-admission-model;callback-registration-gated")
    print("clock_owner_inventory=generic_ccf_only;protected_owner_absent;A72_observer_read_only")
    print("pcm_start_contract=defined;residency_and_start_required_before_callback_registration")
    print("startup_state_owner=unproven;mainline=absent")
    print("historical_owner_source=identified;public_gemian_hybrid")
    print("protected_owner_protocol=identified;BigiDVFS_FIDs_and_MCUMIXED_semaphore;authoritative_state_owner_missing")
    print("mainline_owner=unimplemented;provider=blocked")
    print("image_variant=unproven;firmware_redistribution=unproven")
    print("status=PASS_STATIC")


if __name__ == "__main__":
    main()
