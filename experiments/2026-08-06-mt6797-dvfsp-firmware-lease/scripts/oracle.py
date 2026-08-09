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
CALIBRATED_TABLE_PATCH = ROOT / "patches/v7.1.3/0203-soc-mediatek-require-calibrated-table-state.patch"
EEM_READBACK_PATCH = ROOT / "patches/v7.1.3/0204-thermal-mediatek-add-locked-MT6797-EEM-readback.patch"
EEM_CALIBRATION_PATCH = ROOT / "patches/v7.1.3/0205-soc-mediatek-derive-calibrated-table-from-EEM-readback.patch"
CLOCK_STATE_PATCH = ROOT / "patches/v7.1.3/0206-soc-mediatek-decode-protected-clock-readback.patch"
RUNTIME_PATCH = ROOT / "patches/v7.1.3/0207-soc-mediatek-bind-runtime-invalidation-events.patch"
RUNTIME_BINDING_PATCH = ROOT / "patches/v7.1.3/0208-soc-mediatek-register-runtime-notifier-binding.patch"
STATE_SNAPSHOT_PATCH = ROOT / "patches/v7.1.3/0209-soc-mediatek-assemble-protected-state-snapshot.patch"
STATE_SOURCE_PATCH = ROOT / "patches/v7.1.3/0210-soc-mediatek-add-protected-state-source-adapter.patch"
STATE_SOURCE_BACKENDS_PATCH = ROOT / "patches/v7.1.3/0211-soc-mediatek-wire-protected-readbacks-to-state-source.patch"
PTP_HANDOFF_PATCH = ROOT / "patches/v7.1.3/0212-nvmem-mediatek-expose-MT6797-PTP-handoff-source.patch"
PTP_STATE_PATCH = ROOT / "patches/v7.1.3/0213-soc-mediatek-decode-MT6797-PTP-handoff-state.patch"
PTP_CALIBRATION_PATCH = ROOT / "patches/v7.1.3/0214-soc-mediatek-bind-PTP-state-to-calibration-builder.patch"
STATE_OWNER_SOURCE_PATCH = ROOT / "patches/v7.1.3/0215-soc-mediatek-add-calibrated-state-owner-source-binding.patch"
STATE_OWNER_ARBITRATION_PATCH = ROOT / "patches/v7.1.3/0216-soc-mediatek-bind-state-owner-source-to-transition-generation.patch"
STATE_OWNER_ARBITRATION_FAULT_PATCH = ROOT / "patches/v7.1.3/0217-soc-mediatek-latch-transition-arbitration-faults.patch"
STATE_OWNER_REGISTRATION_PATCH = ROOT / "patches/v7.1.3/0218-soc-mediatek-register-arbitrated-state-owner.patch"
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
CALIBRATED_TABLE_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/calibrated-table-state-buildbox-20260806.txt"
EEM_READBACK_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/eem-readback-buildbox-20260806.txt"
EEM_CALIBRATION_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/eem-calibration-builder-buildbox-20260806.txt"
CLOCK_STATE_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/clock-state-decoder-buildbox-20260806.txt"
RUNTIME_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/runtime-invalidation-buildbox-20260806.txt"
RUNTIME_BINDING_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/runtime-binding-buildbox-20260806.txt"
STATE_SNAPSHOT_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/state-snapshot-buildbox-20260806.txt"
STATE_SOURCE_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/state-source-adapter-buildbox-20260809.txt"
STATE_SOURCE_BACKENDS_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/state-source-backend-bridge-buildbox-20260809.txt"
PTP_HANDOFF_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/state-source-ptp-handoff-buildbox-20260809.txt"
PTP_STATE_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/state-source-ptp-decode-buildbox-20260809.txt"
PTP_CALIBRATION_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/state-source-ptp-calibration-buildbox-20260809.txt"
STATE_OWNER_SOURCE_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/state-owner-source-buildbox-20260809.txt"
STATE_OWNER_ARBITRATION_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/state-owner-arbitration-buildbox-20260809.txt"
STATE_OWNER_ARBITRATION_FAULT_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/state-owner-arbitration-fault-buildbox-20260809.txt"
LIVE_DVFS_SOURCE_RESULT = Path(__file__).resolve().parents[1] / "results/live-dvfs-owner-source-probe-20260809.txt"
STATE_OWNER_REGISTRATION_BUILD_RESULT = Path(__file__).resolve().parents[1] / "results/state-owner-registration-buildbox-20260809.txt"


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
    calibrated_table_patch = CALIBRATED_TABLE_PATCH.read_text()
    eem_readback_patch = EEM_READBACK_PATCH.read_text()
    eem_calibration_patch = EEM_CALIBRATION_PATCH.read_text()
    clock_state_patch = CLOCK_STATE_PATCH.read_text()
    runtime_patch = RUNTIME_PATCH.read_text()
    runtime_binding_patch = RUNTIME_BINDING_PATCH.read_text()
    state_snapshot_patch = STATE_SNAPSHOT_PATCH.read_text()
    state_source_patch = STATE_SOURCE_PATCH.read_text()
    state_source_backends_patch = STATE_SOURCE_BACKENDS_PATCH.read_text()
    ptp_handoff_patch = PTP_HANDOFF_PATCH.read_text()
    ptp_state_patch = PTP_STATE_PATCH.read_text()
    ptp_calibration_patch = PTP_CALIBRATION_PATCH.read_text()
    state_owner_source_patch = STATE_OWNER_SOURCE_PATCH.read_text()
    state_owner_arbitration_patch = STATE_OWNER_ARBITRATION_PATCH.read_text()
    state_owner_arbitration_fault_patch = STATE_OWNER_ARBITRATION_FAULT_PATCH.read_text()
    state_owner_registration_patch = STATE_OWNER_REGISTRATION_PATCH.read_text()
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
    calibrated_table_build_result = CALIBRATED_TABLE_BUILD_RESULT.read_text()
    eem_readback_build_result = EEM_READBACK_BUILD_RESULT.read_text()
    eem_calibration_build_result = EEM_CALIBRATION_BUILD_RESULT.read_text()
    clock_state_build_result = CLOCK_STATE_BUILD_RESULT.read_text()
    runtime_build_result = RUNTIME_BUILD_RESULT.read_text()
    runtime_binding_build_result = RUNTIME_BINDING_BUILD_RESULT.read_text()
    state_snapshot_build_result = STATE_SNAPSHOT_BUILD_RESULT.read_text()
    state_source_build_result = STATE_SOURCE_BUILD_RESULT.read_text()
    state_source_backends_build_result = STATE_SOURCE_BACKENDS_BUILD_RESULT.read_text()
    ptp_handoff_build_result = PTP_HANDOFF_BUILD_RESULT.read_text()
    ptp_state_build_result = PTP_STATE_BUILD_RESULT.read_text()
    ptp_calibration_build_result = PTP_CALIBRATION_BUILD_RESULT.read_text()
    state_owner_source_build_result = STATE_OWNER_SOURCE_BUILD_RESULT.read_text()
    state_owner_arbitration_build_result = STATE_OWNER_ARBITRATION_BUILD_RESULT.read_text()
    state_owner_arbitration_fault_build_result = STATE_OWNER_ARBITRATION_FAULT_BUILD_RESULT.read_text()
    live_dvfs_source_result = LIVE_DVFS_SOURCE_RESULT.read_text()
    state_owner_registration_build_result = STATE_OWNER_REGISTRATION_BUILD_RESULT.read_text()
    source = patch[patch.index("diff --git"):]
    state_owner_source = state_owner_patch[state_owner_patch.index("diff --git"):]
    eem_calibration_source = eem_calibration_patch[eem_calibration_patch.index("diff --git"):]
    clock_state_source = clock_state_patch[clock_state_patch.index("diff --git"):]
    runtime_source = runtime_patch[runtime_patch.index("diff --git"):]
    runtime_binding_source = runtime_binding_patch[runtime_binding_patch.index("diff --git"):]
    state_snapshot_source = state_snapshot_patch[state_snapshot_patch.index("diff --git"):]
    state_source_source = state_source_patch[state_source_patch.index("diff --git"):]
    state_source_backends_source = state_source_backends_patch[state_source_backends_patch.index("diff --git"):]
    ptp_handoff_source = ptp_handoff_patch[ptp_handoff_patch.index("diff --git"):]
    ptp_state_source = ptp_state_patch[ptp_state_patch.index("diff --git"):]
    ptp_calibration_source = ptp_calibration_patch[ptp_calibration_patch.index("diff --git"):]
    state_owner_source_source = state_owner_source_patch[state_owner_source_patch.index("diff --git"):]
    state_owner_arbitration_source = state_owner_arbitration_patch[state_owner_arbitration_patch.index("diff --git"):]
    state_owner_arbitration_fault_source = state_owner_arbitration_fault_patch[state_owner_arbitration_fault_patch.index("diff --git"):]
    state_owner_registration_source = state_owner_registration_patch[state_owner_registration_patch.index("diff --git"):]
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
        ("MT6797_DVFSP_CALIBRATION_STATE_ABI", "calibrated-state-abi"),
        ("MT6797_DVFSP_CALIBRATION_STATE_PHASE_MON", "calibrated-state-mon-phase"),
        ("MT6797_DVFSP_CALIBRATION_STATE_BANK_ALL", "calibrated-state-bank-mask"),
        ("MT6797_DVFSP_CALIBRATION_TABLE_MAX", "calibrated-state-table-bound"),
        ("struct mt6797_dvfsp_calibration_table_entry", "calibrated-state-table-entry"),
        ("struct mt6797_dvfsp_calibration_state", "calibrated-state-struct"),
        ("snapshot_state", "calibrated-state-callback"),
        ("mt6797_dvfsp_calibration_state_check", "calibrated-state-check"),
        ("entry->frequency_khz <= previous_frequency", "calibrated-state-frequency-order"),
        ("entry->vsram_uv - entry->vproc_uv < 10000", "calibrated-state-rail-delta-min"),
        ("entry->vsram_uv - entry->vproc_uv > 30000", "calibrated-state-rail-delta-max"),
        ("entry->vsram_uv < 1000000", "calibrated-state-vsram-floor"),
        ("entry->vsram_uv > 1200000", "calibrated-state-vsram-ceiling"),
        ("thermal_generation", "calibrated-state-thermal-generation"),
        ("clock_owner_generation", "calibrated-state-clock-generation"),
        ("rail_owner_generation", "calibrated-state-rail-generation"),
        ("owner->calibration_ops->snapshot_state", "calibrated-state-owner-admission"),
        ("default owner remains", "calibrated-state-default-off"),
    ):
        require(calibrated_table_patch, needle, label)
    for needle, label in (
        ("MT6797_EEM_READBACK_ABI", "eem-readback-abi"),
        ("MT6797_EEM_READBACK_ANCHORS\t8", "eem-readback-anchor-count"),
        ("MT6797_EEM_READBACK_BANK_COUNT\t4", "eem-readback-bank-count"),
        ("MT6797_EEM_READBACK_BANK_BIG\t0", "eem-readback-big-bank"),
        ("MT6797_EEM_READBACK_BANK_L\t\t3", "eem-readback-l-bank"),
        ("MT6797_EEM_READBACK_BANK_2L\t4", "eem-readback-2l-bank"),
        ("MT6797_EEM_READBACK_BANK_CCI\t5", "eem-readback-cci-bank"),
        ("MT6797_EEM_FREQPCT30\t\t0x218", "eem-readback-freqpct30"),
        ("MT6797_EEM_FREQPCT74\t\t0x21c", "eem-readback-freqpct74"),
        ("MT6797_EEM_VOP30\t\t0x248", "eem-readback-vop30"),
        ("MT6797_EEM_VOP74\t\t0x24c", "eem-readback-vop74"),
        ("MT6797_EEM_EEMEN\t\t0x238", "eem-readback-eemen"),
        ("MT6797_EEMCORESEL_MASK\t\tGENMASK(2, 0)", "eem-readback-selector-mask"),
        ("mt6797_thermal_eem_readback", "eem-readback-api"),
        ("mutex_lock(&mt->lock)", "eem-readback-lock"),
        ("mutex_unlock(&mt->lock)", "eem-readback-unlock"),
        ("readback->selector_before", "eem-readback-selector-before"),
        ("readback->selector_after", "eem-readback-selector-after"),
        ("restored_selector != selector", "eem-readback-selector-restore-check"),
        ("platform_set_drvdata(pdev, mt)", "eem-readback-thermal-owner"),
        ("This is a readback boundary, not a calibrated DVFSP provider", "eem-readback-default-off"),
    ):
        require(eem_readback_patch, needle, label)
    eem_added = "\n".join(
        line[1:] for line in eem_readback_patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    if eem_added.count("writel(") != 2:
        raise AssertionError("EEM readback must have exactly selector write and restore")
    for selector_write in (
        "writel(value, mt->thermal_base + PTPCORESEL);",
        "writel(selector, mt->thermal_base + PTPCORESEL);",
    ):
        require(eem_added, selector_write, "eem-readback-selector-write")
    for forbidden in ("regulator_", "clk_", "i2c_transfer", "psci_ops", "cpu_up(",
                      "devm_ioremap", "INIT01", "INIT02", "MON"):
        if forbidden in eem_added:
            raise AssertionError(f"unexpected EEM readback operation: {forbidden}")
    for needle, label in (
        ("MT6797_EEM_CALIBRATION_ABI", "eem-calibration-abi"),
        ("MT6797_EEM_CALIBRATION_ROWS", "eem-calibration-row-count"),
        ("MT6797_EEM_CALIBRATION_MON_ENABLE", "eem-calibration-mon-enable"),
        ("MT6797_EEM_CALIBRATION_MON_STATUS_MASK", "eem-calibration-status-mask"),
        ("MT6797_EEM_CALIBRATION_TEMP_OFFSET_UV", "eem-calibration-temperature-offset"),
        ("MT6797_EEM_CALIBRATION_VSRAM_MIN_UV", "eem-calibration-vsram-floor"),
        ("MT6797_EEM_CALIBRATION_VSRAM_MAX_UV", "eem-calibration-vsram-ceiling"),
        ("struct mt6797_eem_calibration_input", "eem-calibration-input"),
        ("frequency_pct", "eem-calibration-frequency-percent"),
        ("frequency_khz", "eem-calibration-frequency-khz"),
        ("record_vproc_uv", "eem-calibration-recorded-cap"),
        ("vsram_uv", "eem-calibration-vsram"),
        ("ppm_limit_khz", "eem-calibration-ppm-limit"),
        ("thermal_generation", "eem-calibration-thermal-generation"),
        ("clock_owner_generation", "eem-calibration-clock-generation"),
        ("rail_owner_generation", "eem-calibration-rail-generation"),
        ("mt6797_eem_calibration_provenance_check", "eem-calibration-provenance"),
        ("mt6797_eem_calibration_interpolate", "eem-calibration-interpolation"),
        ("div_s64", "eem-calibration-signed-interpolation"),
        ("MT6797_EEM_CALIBRATION_BIG_BASE_UV", "eem-calibration-big-units"),
        ("MT6797_EEM_CALIBRATION_EEM_BASE_UV", "eem-calibration-normal-units"),
        ("bank->vop", "eem-calibration-vop-source"),
        ("MT6797_EEM_READBACK_BANK_BIG", "eem-calibration-big-bank"),
        ("MT6797_EEM_READBACK_BANK_CCI", "eem-calibration-cci-bank"),
        ("input->readback->selector_before != input->readback->selector_after", "eem-calibration-selector-check"),
        ("state->phase = MT6797_DVFSP_CALIBRATION_STATE_PHASE_MON", "eem-calibration-mon-phase"),
        ("cluster->table_count = MT6797_EEM_CALIBRATION_ROWS", "eem-calibration-table-count"),
        ("EXPORT_SYMBOL_GPL(mt6797_eem_calibration_build)", "eem-calibration-export"),
        ("No default table", "eem-calibration-default-off"),
    ):
        require(eem_calibration_patch, needle, label)
    for needle, label in (
        ("MT6797_DVFSP_CLOCK_STATE_ABI", "clock-state-abi"),
        ("MT6797_DVFSP_CLOCK_STATE_PARENT_MHZ", "clock-state-parent"),
        ("MT6797_DVFSP_CLOCK_STATE_PCW_MASK", "clock-state-pcw"),
        ("MT6797_DVFSP_CLOCK_STATE_POSDIV_MASK", "clock-state-posdiv"),
        ("MT6797_DVFSP_CLOCK_STATE_PLL_CHANGE", "clock-state-inflight"),
        ("MT6797_DVFSP_CLOCK_STATE_CLUSTER_COUNT", "clock-state-clusters"),
        ("struct mt6797_dvfsp_clock_state_cluster", "clock-state-cluster"),
        ("clock_sample_generation", "clock-state-clock-generation"),
        ("big_sample_generation", "clock-state-big-generation"),
        ("mt6797_dvfsp_clock_divider_decode", "clock-state-divider"),
        ("mt6797_dvfsp_clock_frequency_decode", "clock-state-frequency"),
        ("((u64)pll_pcw * MT6797_DVFSP_CLOCK_STATE_PARENT_MHZ) >> 14", "clock-state-vendor-formula"),
        ("frequency *= 1000", "clock-state-khz-conversion"),
        ("FIELD_GET", "clock-state-field-decode"),
        ("pll_ll[1]", "clock-state-ll-readback"),
        ("pll_l[1]", "clock-state-l-readback"),
        ("pll_cci[1]", "clock-state-cci-readback"),
        ("big->pll_enable_posdiv", "clock-state-b-readback"),
        ("EXPORT_SYMBOL_GPL(mt6797_dvfsp_clock_state_decode)", "clock-state-export"),
    ):
        require(clock_state_patch, needle, label)
    for needle, label in (
        ("MT6797_DVFSP_RUNTIME_ABI", "runtime-abi"),
        ("MT6797_DVFSP_RUNTIME_EVENT_COUNT", "runtime-event-count"),
        ("enum mt6797_dvfsp_runtime_event_type", "runtime-event-type"),
        ("CPU_ONLINE", "runtime-cpu-online"),
        ("CPU_DOWN_PREPARE", "runtime-cpu-down-prepare"),
        ("CPU_DOWN_FAILED", "runtime-cpu-down-failed"),
        ("PM_SUSPEND_PREPARE", "runtime-pm-suspend-prepare"),
        ("PM_POST_SUSPEND", "runtime-pm-post-suspend"),
        ("struct mt6797_dvfsp_runtime_event", "runtime-event-struct"),
        ("struct mt6797_dvfsp_runtime_ledger", "runtime-ledger-struct"),
        ("mt6797_dvfsp_runtime_event_apply", "runtime-event-apply"),
        ("mt6797_dvfsp_runtime_reason", "runtime-reason-map"),
        ("mt6797_dvfsp_runtime_event_check", "runtime-event-check"),
        ("last_sequence", "runtime-sequence"),
        ("invalidated_generation", "runtime-generation"),
        ("mt6797_dvfsp_handoff_state_invalidate", "runtime-invalidate"),
        ("-EALREADY", "runtime-replay-rejection"),
        ("EXPORT_SYMBOL_GPL(mt6797_dvfsp_runtime_event_apply)", "runtime-export"),
    ):
        require(runtime_patch, needle, label)
    for needle, label in (
        ("MT6797_DVFSP_RUNTIME_BINDING_ABI", "runtime-binding-abi"),
        ("MT6797_DVFSP_RUNTIME_CPU_NONE", "runtime-binding-cpu-sentinel"),
        ("struct mt6797_dvfsp_runtime_source_ops", "runtime-binding-source-ops"),
        ("struct mt6797_dvfsp_runtime_binding", "runtime-binding-struct"),
        ("mt6797_dvfsp_runtime_binding_init", "runtime-binding-init"),
        ("mt6797_dvfsp_runtime_binding_register", "runtime-binding-register"),
        ("mt6797_dvfsp_runtime_binding_unregister", "runtime-binding-unregister"),
        ("cpuhp_setup_state_nocalls", "runtime-binding-cpuhp-register"),
        ("cpuhp_remove_state_nocalls", "runtime-binding-cpuhp-remove"),
        ("CPUHP_AP_ONLINE_DYN", "runtime-binding-cpuhp-state"),
        ("register_pm_notifier", "runtime-binding-pm-register"),
        ("unregister_pm_notifier", "runtime-binding-pm-remove"),
        ("mt6797_dvfsp_handoff_state_owner_identity", "runtime-binding-owner-required"),
        ("down_pending", "runtime-binding-down-pending"),
        ("cpu_online(cpu)", "runtime-binding-down-failed-discriminator"),
        ("notifier_from_errno", "runtime-binding-fail-closed-notifier"),
        ("state->active = false", "runtime-binding-disarm"),
        ("No caller registers this binding", "runtime-binding-default-off"),
    ):
        require(runtime_binding_patch, needle, label)
    for needle, label in (
        ("MT6797_DVFSP_STATE_SNAPSHOT_ABI", "state-snapshot-abi"),
        ("struct mt6797_dvfsp_state_snapshot_input", "state-snapshot-input"),
        ("mt6797_dvfsp_state_snapshot_assemble", "state-snapshot-assemble"),
        ("MT6797_DVFSP_STATE_OWNER_ABI", "state-snapshot-owner-output"),
        ("MT6797_DVFSP_STATE_FIELD_ALL", "state-snapshot-complete-fields"),
        ("MT6797_DVFSP_STATE_CLUSTER_MASK", "state-snapshot-all-clusters"),
        ("clock->frequency_khz != input->frequency_khz[cluster]", "state-snapshot-clock-match"),
        ("mt6797_dvfsp_snapshot_table_match", "state-snapshot-table-match"),
        ("MT6797_DVFSP_CALIBRATION_STATE_PHASE_MON", "state-snapshot-mon-phase"),
        ("MT6797_DVFSP_CALIBRATION_STATE_BANK_ALL", "state-snapshot-bank-mask"),
        ("no default or board guess", "state-snapshot-no-guesses"),
        ("does not read hardware", "state-snapshot-no-hardware"),
    ):
        require(state_snapshot_patch, needle, label)
    for needle, label in (
        ("MT6797_DVFSP_STATE_SOURCE_ABI", "state-source-abi"),
        ("struct mt6797_dvfsp_state_source_live", "state-source-live-fields"),
        ("struct mt6797_dvfsp_state_source_ops", "state-source-ops"),
        ("read_clock", "state-source-clock-read"),
        ("read_big", "state-source-big-read"),
        ("read_eem", "state-source-eem-read"),
        ("fill_calibration", "state-source-calibration-fill"),
        ("fill_live", "state-source-live-fill"),
        ("mt6797_dvfsp_clock_state_decode", "state-source-clock-decode"),
        ("mt6797_eem_calibration_build", "state-source-calibration-build"),
        ("mt6797_dvfsp_state_snapshot_assemble", "state-source-snapshot-assemble"),
        ("caller owns and holds the transition lock", "state-source-lock-contract"),
        ("No callback is registered here", "state-source-default-off"),
    ):
        require(state_source_patch, needle, label)
    for needle, label in (
        ("struct mt6797_dvfsp_state_source_devices", "state-source-devices"),
        ("clock_backend", "state-source-clock-device"),
        ("bigidvfs_backend", "state-source-big-device"),
        ("thermal", "state-source-thermal-device"),
        ("mt6797_dvfsp_state_source_backend_read_clock", "state-source-clock-bridge"),
        ("mt6797_dvfsp_state_source_backend_read_big", "state-source-big-bridge"),
        ("mt6797_dvfsp_state_source_backend_read_eem", "state-source-eem-bridge"),
        ("mt6797_dvfsp_state_source_backend_ops_init", "state-source-ops-init"),
        ("fill_calibration and fill_live", "state-source-required-owner-callbacks"),
        ("CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND", "state-source-clock-config"),
        ("CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND", "state-source-big-config"),
        ("CONFIG_MTK_SOC_THERMAL", "state-source-thermal-config"),
        ("return -ENODEV", "state-source-bridge-fail-closed"),
        ("retains no device", "state-source-no-retained-device"),
        ("no platform driver", "state-source-no-driver"),
    ):
        require(state_source_backends_patch, needle, label)
    for needle, label in (
        ("MT6797_PTP_FIRST_PAYLOAD_WORD", "ptp-provider-first-word"),
        ("MT6797_PTP_WORDS", "ptp-provider-word-count"),
        ("ptp-calibration-data", "ptp-provider-cell"),
        ("MT6797_DVFSP_PTP_HANDOFF_ABI", "ptp-handoff-abi"),
        ("MT6797_DVFSP_PTP_HANDOFF_WORDS", "ptp-handoff-word-count"),
        ("struct mt6797_dvfsp_ptp_handoff", "ptp-handoff-struct"),
        ("read_ptp", "ptp-source-callback"),
        ("calibration_source", "ptp-source-device"),
        ("nvmem_cell_read", "ptp-nvmem-read"),
        ("nvmem_cell_put", "ptp-nvmem-release"),
        ("CONFIG_NVMEM_MTK_ATAG_DEVINFO", "ptp-provider-config"),
        ("MT6797_DVFSP_STATE_SOURCE_ABI\t\t2", "ptp-source-abi-bump"),
        ("No platform driver is registered", "ptp-default-off"),
    ):
        require(ptp_handoff_patch, needle, label)
    for needle, label in (
        ("MT6797_DVFSP_PTP_STATE_ABI", "ptp-state-abi"),
        ("MT6797_DVFSP_PTP_BANK_MASK_ALL", "ptp-state-all-banks"),
        ("MT6797_DVFSP_PTP_BANK_BIG", "ptp-state-big-bank"),
        ("MT6797_DVFSP_PTP_BANK_L", "ptp-state-l-bank"),
        ("MT6797_DVFSP_PTP_BANK_2L", "ptp-state-2l-bank"),
        ("MT6797_DVFSP_PTP_BANK_CCI", "ptp-state-cci-bank"),
        ("struct mt6797_dvfsp_ptp_bank_state", "ptp-state-bank"),
        ("init_enable", "ptp-state-init"),
        ("mon_enable", "ptp-state-mon"),
        ("dvfs_level", "ptp-state-dvfs-level"),
        ("bin_spec", "ptp-state-bin"),
        ("mt6797_dvfsp_ptp_decode", "ptp-state-decoder"),
        ("handoff->m_hw_res[1]", "ptp-state-big-source"),
        ("handoff->m_hw_res[7]", "ptp-state-l-source"),
        ("handoff->m_hw_res[9]", "ptp-state-2l-cci-source"),
        ("return -EAGAIN", "ptp-state-disabled-fail-closed"),
        ("!provenance->variant_id", "ptp-state-variant-required"),
        ("provider registration", "ptp-state-no-provider"),
        ("no MMIO", "ptp-state-no-mmio"),
    ):
        require(ptp_state_patch, needle, label)
    for needle, label in (
        ("mt6797_eem_calibration_ptp_state_check", "ptp-calibration-state-check"),
        ("const struct mt6797_dvfsp_ptp_state *ptp_state", "ptp-calibration-state-input"),
        ("expected_banks", "ptp-calibration-bank-map"),
        ("bank->init_enable != 1", "ptp-calibration-init-required"),
        ("bank->mon_enable != 1", "ptp-calibration-mon-required"),
        ("bank->dvfs_level > 3", "ptp-calibration-dvfs-range"),
        ("bank->bin_spec > 7", "ptp-calibration-bin-range"),
        ("!input->ptp_state", "ptp-calibration-input-required"),
        ("calibration_input.ptp_state = &ptp_state", "ptp-calibration-adapter-binding"),
        ("provider\nregistration", "ptp-calibration-no-provider"),
        ("CPU8/CPU9 admission", "ptp-calibration-no-cpu-admission"),
    ):
        require(ptp_calibration_patch, needle, label)
    for needle, label in (
        ("MT6797_DVFSP_STATE_OWNER_SOURCE_ABI", "owner-source-abi"),
        ("struct mt6797_dvfsp_state_owner_source_identity", "owner-source-identity"),
        ("read_identity", "owner-source-identity-callback"),
        ("fill_calibration", "owner-source-calibration-callback"),
        ("fill_live", "owner-source-live-callback"),
        ("invalidate", "owner-source-invalidation-callback"),
        ("MT6797_DVFSP_STATE_PROVENANCE_SOURCE_ALL", "owner-source-full-provenance"),
        ("input->provenance.abi", "owner-source-reject-callback-provenance"),
        ("live->owner_handle != owner->owner_handle", "owner-source-owner-handle"),
        ("live->transition_handle != owner->transition_handle", "owner-source-transition-handle"),
        ("mt6797_dvfsp_state_source_snapshot", "owner-source-complete-snapshot"),
        ("mutex_lock_interruptible", "owner-source-transition-lock"),
        ("mt6797_dvfsp_ptp_decode", "owner-source-ptp-identity"),
        ("mt6797_dvfsp_state_owner_source_owner_ops_init", "owner-source-dormant-ops"),
        ("does not register the owner", "owner-source-no-registration"),
    ):
        require(state_owner_source_patch, needle, label)
    for needle, label in (
        ("MT6797_DVFSP_STATE_OWNER_ARBITRATION_ABI", "owner-arbitration-abi"),
        ("struct mt6797_dvfsp_state_owner_arbitration_ops", "owner-arbitration-ops"),
        ("int (*lock)(void *context)", "owner-arbitration-lock"),
        ("void (*unlock)(void *context)", "owner-arbitration-unlock"),
        ("read_generation", "owner-arbitration-generation"),
        ("mt6797_dvfsp_arbitration_begin", "owner-arbitration-begin"),
        ("mt6797_dvfsp_arbitration_end", "owner-arbitration-end"),
        ("after != generation", "owner-arbitration-change-reject"),
        ("*generation < arbitration->last_generation", "owner-arbitration-rollback-reject"),
        ("mt6797_dvfsp_state_owner_arbitration_owner_ops_init", "owner-arbitration-dormant-ops"),
        ("no handoff owner is registered", "owner-arbitration-no-registration"),
    ):
        require(state_owner_arbitration_patch, needle, label)
    for needle, label in (
        ("bool faulted", "owner-arbitration-fault-latch"),
        ("mt6797_dvfsp_arbitration_fault", "owner-arbitration-fault-helper"),
        ("mt6797_dvfsp_state_owner_source_invalidate", "owner-arbitration-source-invalidate"),
        ("MT6797_DVFSP_STATE_INVALID_CLOCK_TRANSITION", "owner-arbitration-fault-reason"),
        ("arbitration->faulted = true", "owner-arbitration-explicit-fault"),
    ):
        require(state_owner_arbitration_fault_patch, needle, label)
    for needle, label in (
        ("mt6797_dvfsp_state_owner_arbitration_register", "owner-registration-register-api"),
        ("mt6797_dvfsp_state_owner_arbitration_unregister", "owner-registration-unregister-api"),
        ("struct mt6797_dvfsp_state_owner_ops owner_ops", "owner-registration-owned-ops"),
        ("struct mt6797_dvfsp_handoff *handoff", "owner-registration-handoff"),
        ("bool registered", "owner-registration-state"),
        ("mt6797_dvfsp_handoff_state_owner_register", "owner-registration-handoff-register"),
        ("mt6797_dvfsp_handoff_state_owner_unregister", "owner-registration-handoff-unregister"),
        ("mt6797_dvfsp_state_owner_arbitration_hold_cb", "owner-registration-hold-callback"),
        ("mt6797_dvfsp_state_owner_arbitration_release_cb", "owner-registration-release-callback"),
        ("no caller invokes it in the default profile", "owner-registration-default-off"),
        ("Registration still fails closed", "owner-registration-fail-closed"),
    ):
        require(state_owner_registration_patch, needle, label)
    bridge_added = "\n".join(
        line[1:] for line in state_source_backends_patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for forbidden in ("readl(", "writel(", "regulator_", "clk_prepare",
                      "clk_set", "arm_smccc", "platform_driver", "module_platform_driver",
                      "cpu_up("):
        if forbidden in bridge_added:
            raise AssertionError(f"unexpected state-source bridge operation: {forbidden}")
    for forbidden in ("readl(", "writel(", "regulator_", "clk_",
                      "i2c_transfer", "arm_smccc", "platform_driver",
                      "module_platform_driver", "cpu_up(", "secure_write"):
        if forbidden in state_owner_source_source:
            raise AssertionError(f"unexpected calibrated owner operation: {forbidden}")
        if forbidden in state_owner_arbitration_source:
            raise AssertionError(f"unexpected state-owner arbitration operation: {forbidden}")
        if forbidden in state_owner_arbitration_fault_source:
            raise AssertionError(f"unexpected state-owner arbitration fault operation: {forbidden}")
        if forbidden in state_owner_registration_source:
            raise AssertionError(f"unexpected state-owner registration operation: {forbidden}")
    calibration_builder_added = "\n".join(
        line[1:] for line in eem_calibration_patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for forbidden in ("readl(", "writel(", "regulator_", "clk_", "i2c_transfer",
                      "arm_smccc", "cpu_up(", "platform_driver", "INIT01", "INIT02"):
        if forbidden in calibration_builder_added:
            raise AssertionError(f"unexpected EEM calibration operation: {forbidden}")
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
        ("claim=COMPILE_ONLY_CALIBRATED_TABLE_STATE_ADMISSION", "calibrated-table-build-claim"),
        ("repository_commit=652d1648fa0fa527e1014975df140f1a5b1058f5", "calibrated-table-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "calibrated-table-build-origin"),
        ("build_backend=buildbox", "calibrated-table-build-backend"),
        ("buildbox_status=validated", "calibrated-table-build-status"),
        ("patch_count=192", "calibrated-table-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-c452a51f-11afba8d", "calibrated-table-build-artifact"),
        ("dtb_count=119", "calibrated-table-build-dtb-count"),
        ("sha256sums=passed", "calibrated-table-build-checksums"),
        ("package_fetch=success;validated_package_only", "calibrated-table-build-fetch"),
        ("calibrated_table_contract=0203;MON_phase;BIG_L_2L_CCI_banks;frequency_voltage_vsram_ppm_rows;thermal_clock_rail_generations;default_off", "calibrated-table-build-contract"),
        ("owner=unregistered", "calibrated-table-build-owner-unregistered"),
        ("provider=none", "calibrated-table-build-no-provider"),
        ("secure_write=none", "calibrated-table-build-no-secure-write"),
        ("hardware_write=none", "calibrated-table-build-no-write"),
        ("device_action=none", "calibrated-table-build-no-device"),
        ("boot_candidate=false", "calibrated-table-build-not-candidate"),
    ):
        require(calibrated_table_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_MT6797_EEM_READBACK_BOUNDARY", "eem-readback-build-claim"),
        ("repository_commit=20ad8b66b9ad0408abc29889a1da5f04bf24c0f3", "eem-readback-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "eem-readback-build-origin"),
        ("build_backend=buildbox", "eem-readback-build-backend"),
        ("buildbox_status=validated", "eem-readback-build-status"),
        ("patch_count=193", "eem-readback-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-f1a0fdb8-b6696a3c", "eem-readback-build-artifact"),
        ("dtb_count=119", "eem-readback-build-dtb-count"),
        ("sha256sums=passed", "eem-readback-build-checksums"),
        ("package_fetch=success;validated_package_only", "eem-readback-build-fetch"),
        ("eem_readback_contract=0204;thermal_owner_lock;selector_write_restore;BIG_L_2L_CCI;offsets_0x218_0x21c_0x248_0x24c;status_only;default_off", "eem-readback-build-contract"),
        ("owner=unregistered", "eem-readback-build-owner-unregistered"),
        ("provider=none", "eem-readback-build-no-provider"),
        ("secure_write=none", "eem-readback-build-no-secure-write"),
        ("hardware_write=none", "eem-readback-build-no-write"),
        ("device_action=none", "eem-readback-build-no-device"),
        ("boot_candidate=false", "eem-readback-build-not-candidate"),
    ):
        require(eem_readback_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_MT6797_EEM_CALIBRATION_TABLE_BUILDER", "eem-calibration-build-claim"),
        ("repository_commit=df2c410d594ad19c32cc8b3d090fd0fe18bdc13d", "eem-calibration-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "eem-calibration-build-origin"),
        ("build_backend=buildbox", "eem-calibration-build-backend"),
        ("buildbox_status=validated", "eem-calibration-build-status"),
        ("patch_count=194", "eem-calibration-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-2cf5e38e-b6696a3c", "eem-calibration-build-artifact"),
        ("dtb_count=119", "eem-calibration-build-dtb-count"),
        ("sha256sums=passed", "eem-calibration-build-checksums"),
        ("package_fetch=success;validated_package_only", "eem-calibration-build-fetch"),
        ("eem_calibration_contract=0205;raw-readback-anchor-match;BIG-and-normal-unit-conversion;16-row-interpolation;temperature-offset;VMIN-VMAX-and-record-cap;VSRAM-delta;full-provenance;default-off", "eem-calibration-build-contract"),
        ("owner=unregistered", "eem-calibration-build-owner-unregistered"),
        ("provider=none", "eem-calibration-build-no-provider"),
        ("hardware_write=none", "eem-calibration-build-no-write"),
        ("device_action=none", "eem-calibration-build-no-device"),
        ("boot_candidate=false", "eem-calibration-build-not-candidate"),
    ):
        require(eem_calibration_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_MT6797_PROTECTED_CLOCK_STATE_DECODER", "clock-state-build-claim"),
        ("repository_commit=4d5d8da9d363582d6307478f224d65d9bb6744d4", "clock-state-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "clock-state-build-origin"),
        ("build_backend=buildbox", "clock-state-build-backend"),
        ("buildbox_status=validated", "clock-state-build-status"),
        ("patch_count=195", "clock-state-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-041daf5c-b6696a3c", "clock-state-build-artifact"),
        ("dtb_count=119", "clock-state-build-dtb-count"),
        ("sha256sums=passed", "clock-state-build-checksums"),
        ("package_fetch=success;validated_package_only", "clock-state-build-fetch"),
        ("clock_state_contract=0206;raw_ll_l_b_cci_readbacks;vendor_26mhz_formula;pcw_posdiv_and_divider_decode;generation_tagged;inflight_change_rejected;default_off", "clock-state-build-contract"),
        ("owner=unregistered", "clock-state-build-owner-unregistered"),
        ("provider=none", "clock-state-build-no-provider"),
        ("secure_write=none", "clock-state-build-no-secure-write"),
        ("hardware_write=none", "clock-state-build-no-write"),
        ("device_action=none", "clock-state-build-no-device"),
        ("boot_candidate=false", "clock-state-build-not-candidate"),
    ):
        require(clock_state_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_MT6797_DVFSP_RUNTIME_INVALIDATION_LEDGER", "runtime-build-claim"),
        ("repository_commit=870dcc1b92ff2f1462bade90fb75647350ea481f", "runtime-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "runtime-build-origin"),
        ("build_backend=buildbox", "runtime-build-backend"),
        ("buildbox_status=validated", "runtime-build-status"),
        ("patch_count=196", "runtime-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-f58a53ae-b6696a3c", "runtime-build-artifact"),
        ("dtb_count=119", "runtime-build-dtb-count"),
        ("sha256sums=passed", "runtime-build-checksums"),
        ("package_fetch=success;validated_package_only", "runtime-build-fetch"),
        ("runtime_invalidation_contract=0207;vendor_cpu_online_cpu_down_prepare_cpu_down_failed_pm_suspend_prepare_pm_post_suspend;clock_rail_pcm_fault_mapping;monotonic_sequence;generation_epoch;replay_rejected;default_off", "runtime-build-contract"),
        ("owner=unregistered", "runtime-build-owner-unregistered"),
        ("provider=none", "runtime-build-no-provider"),
        ("secure_write=none", "runtime-build-no-secure-write"),
        ("hardware_write=none", "runtime-build-no-write"),
        ("device_action=none", "runtime-build-no-device"),
        ("boot_candidate=false", "runtime-build-not-candidate"),
    ):
        require(runtime_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_MT6797_DVFSP_RUNTIME_NOTIFIER_BINDING", "runtime-binding-build-claim"),
        ("repository_commit=44f617d82eca1f61aac64eda7a142b97296ebbe3", "runtime-binding-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "runtime-binding-build-origin"),
        ("build_backend=buildbox", "runtime-binding-build-backend"),
        ("buildbox_status=validated", "runtime-binding-build-status"),
        ("patch_count=197", "runtime-binding-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-ff8a3bd0-b6696a3c", "runtime-binding-build-artifact"),
        ("dtb_count=119", "runtime-binding-build-dtb-count"),
        ("sha256sums=passed", "runtime-binding-build-checksums"),
        ("package_fetch=success;validated_package_only", "runtime-binding-build-fetch"),
        ("runtime_binding_contract=0208;requires_active_state_owner;cpuhp_online_down_prepare_down_failed;pm_suspend_resume_notifier;generation_tagged_source_callback;ledger_serialized;registration_atomic;disarm_before_unregistration;default_off", "runtime-binding-build-contract"),
        ("owner=unregistered", "runtime-binding-build-owner-unregistered"),
        ("runtime_binding_registered=0", "runtime-binding-build-not-registered"),
        ("provider=none", "runtime-binding-build-no-provider"),
        ("secure_write=none", "runtime-binding-build-no-secure-write"),
        ("hardware_write=none", "runtime-binding-build-no-write"),
        ("device_action=none", "runtime-binding-build-no-device"),
        ("boot_candidate=false", "runtime-binding-build-not-candidate"),
    ):
        require(runtime_binding_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_MT6797_PROTECTED_STATE_SNAPSHOT_ASSEMBLER", "state-snapshot-build-claim"),
        ("repository_commit=7b59354fb53b8f03d020852557deab2be6a023b4", "state-snapshot-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "state-snapshot-build-origin"),
        ("build_backend=buildbox", "state-snapshot-build-backend"),
        ("buildbox_status=validated", "state-snapshot-build-status"),
        ("patch_count=198", "state-snapshot-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-607464d7-b6696a3c", "state-snapshot-build-artifact"),
        ("dtb_count=119", "state-snapshot-build-dtb-count"),
        ("sha256sums=passed", "state-snapshot-build-checksums"),
        ("package_fetch=success;validated_package_only", "state-snapshot-build-fetch"),
        ("state_snapshot_contract=0209;all_four_clusters;clock_frequency_match;calibration_row_match;provenance_match;complete_live_fields;read_only;default_off", "state-snapshot-build-contract"),
        ("owner=unregistered", "state-snapshot-build-owner-unregistered"),
        ("provider=none", "state-snapshot-build-no-provider"),
        ("secure_write=none", "state-snapshot-build-no-secure-write"),
        ("hardware_write=none", "state-snapshot-build-no-write"),
        ("device_action=none", "state-snapshot-build-no-device"),
        ("boot_candidate=false", "state-snapshot-build-not-candidate"),
    ):
        require(state_snapshot_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_MT6797_DVFSP_PROTECTED_STATE_SOURCE_ADAPTER", "state-source-build-claim"),
        ("repository_commit=8b7434cc8b954f0029d5eae89706dfa6c7dd7972", "state-source-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "state-source-build-origin"),
        ("build_backend=buildbox", "state-source-build-backend"),
        ("buildbox_status=validated", "state-source-build-status"),
        ("patch_count=199", "state-source-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-60e6a23f-b6696a3c", "state-source-build-artifact"),
        ("dtb_count=119", "state-source-build-dtb-count"),
        ("sha256sums=passed", "state-source-build-checksums"),
        ("package_fetch=success;validated_package_only", "state-source-build-fetch"),
        ("state_source_contract=0210;clock_readback;bigidvfs_readback;eem_readback;calibration_builder;clock_decoder;live_fields;four_cluster_assembler;caller_held_transition_lock;fail_closed;default_off", "state-source-build-contract"),
        ("owner=unregistered", "state-source-build-owner-unregistered"),
        ("provider=none", "state-source-build-no-provider"),
        ("secure_write=none", "state-source-build-no-secure-write"),
        ("hardware_write=none", "state-source-build-no-write"),
        ("device_action=none", "state-source-build-no-device"),
        ("boot_candidate=false", "state-source-build-not-candidate"),
    ):
        require(state_source_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_MT6797_DVFSP_PROTECTED_READBACK_SOURCE_BRIDGE", "state-source-bridge-build-claim"),
        ("repository_commit=e962efb26821d79f7e55a29a64b0dbd8ba9b7217", "state-source-bridge-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "state-source-bridge-build-origin"),
        ("build_backend=buildbox", "state-source-bridge-build-backend"),
        ("buildbox_status=validated", "state-source-bridge-build-status"),
        ("patch_count=200", "state-source-bridge-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-a259275d-b6696a3c", "state-source-bridge-build-artifact"),
        ("dtb_count=119", "state-source-bridge-build-dtb-count"),
        ("sha256sums=passed", "state-source-bridge-build-checksums"),
        ("package_fetch=success;validated_package_only", "state-source-bridge-build-fetch"),
        ("bridge_contract=0211;caller_owned_device_tuple;clock_readback;bigidvfs_readback;eem_readback;missing_device_fail_closed;missing_backend_config_fail_closed;calibration_live_callbacks_required;no_registration", "state-source-bridge-build-contract"),
        ("owner=unregistered", "state-source-bridge-build-owner-unregistered"),
        ("provider=none", "state-source-bridge-build-no-provider"),
        ("hardware_write=none", "state-source-bridge-build-no-write"),
        ("device_action=none", "state-source-bridge-build-no-device"),
        ("boot_candidate=false", "state-source-bridge-build-not-candidate"),
    ):
        require(state_source_backends_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_MT6797_DVFSP_PTP_HANDOFF_SOURCE", "ptp-build-claim"),
        ("repository_commit=91a64e62b7aea423b204b31b79e42a4aecfe2515", "ptp-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "ptp-build-origin"),
        ("repository_dirty=false", "ptp-build-clean"),
        ("build_backend=buildbox", "ptp-build-backend"),
        ("buildbox_status=validated", "ptp-build-status"),
        ("buildbox_job=91a64e62b7aea423b204b31b79e42a4aecfe2515-dvfsp-protected-readback-m0", "ptp-build-job"),
        ("patch_count=201", "ptp-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-88ff60bc-b6696a3c", "ptp-build-artifact"),
        ("dtb_count=119", "ptp-build-dtb-count"),
        ("sha256sums=passed", "ptp-build-checksums"),
        ("package_fetch=success;validated_package_only", "ptp-build-fetch"),
        ("ptp_contract=0212;read_only_nvmem;19_word_m_hw_res;calibration_callback_input;target=mt6797_dvfsp_handoff;no_registration", "ptp-build-contract"),
        ("owner=unregistered", "ptp-build-owner-unregistered"),
        ("provider=none", "ptp-build-no-provider"),
        ("secure_write=none", "ptp-build-no-secure-write"),
        ("hardware_write=none", "ptp-build-no-write"),
        ("device_action=none", "ptp-build-no-device"),
        ("hardware_support_claim=NONE", "ptp-build-no-support-claim"),
        ("boot_candidate=false", "ptp-build-not-candidate"),
    ):
        require(ptp_handoff_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_MT6797_DVFSP_PTP_STATE_DECODER", "ptp-state-build-claim"),
        ("repository_commit=e335ba84da3edae756e7d713d68def30aaf8bfac", "ptp-state-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "ptp-state-build-origin"),
        ("repository_dirty=false", "ptp-state-build-clean"),
        ("build_backend=buildbox", "ptp-state-build-backend"),
        ("buildbox_status=validated", "ptp-state-build-status"),
        ("buildbox_job=e335ba84da3edae756e7d713d68def30aaf8bfac-dvfsp-protected-readback-m0", "ptp-state-build-job"),
        ("patch_count=202", "ptp-state-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-1d3fee21-b6696a3c", "ptp-state-build-artifact"),
        ("dtb_count=119", "ptp-state-build-dtb-count"),
        ("sha256sums=passed", "ptp-state-build-checksums"),
        ("package_fetch=success;validated_package_only", "ptp-state-build-fetch"),
        ("ptp_state_contract=0213;M_HW_RES1_7_9;BIG_L_2L_CCI;init_mon_required;dvfs_level;bin_spec;variant_id_required;pure;default_off", "ptp-state-build-contract"),
        ("owner=unregistered", "ptp-state-build-owner-unregistered"),
        ("provider=none", "ptp-state-build-no-provider"),
        ("secure_write=none", "ptp-state-build-no-secure-write"),
        ("hardware_write=none", "ptp-state-build-no-write"),
        ("device_action=none", "ptp-state-build-no-device"),
        ("hardware_support_claim=NONE", "ptp-state-build-no-support-claim"),
        ("boot_candidate=false", "ptp-state-build-not-candidate"),
        ("runtime_evidence=none", "ptp-state-build-no-runtime"),
    ):
        require(ptp_state_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_MT6797_DVFSP_PTP_CALIBRATION_BINDING", "ptp-calibration-build-claim"),
        ("repository_commit=be44cbc92e2a27967250f9bf44ce426ac0619fef", "ptp-calibration-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "ptp-calibration-build-origin"),
        ("repository_dirty=false", "ptp-calibration-build-clean"),
        ("build_backend=buildbox", "ptp-calibration-build-backend"),
        ("buildbox_status=validated", "ptp-calibration-build-status"),
        ("buildbox_job=be44cbc92e2a27967250f9bf44ce426ac0619fef-dvfsp-protected-readback-m0", "ptp-calibration-build-job"),
        ("patch_count=203", "ptp-calibration-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-bd70c6fb-b6696a3c", "ptp-calibration-build-artifact"),
        ("source_sha256=be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc", "ptp-calibration-build-source-hash"),
        ("patchset_sha256=bd70c6fb5c805e064c62f39bdbd059fb39b809233e8d1c57b4cad74637b534e7", "ptp-calibration-build-patchset-hash"),
        ("config_sha256=9561561944c875d1fadb5cee822fb9fa572a2e9cf82e4b8a45921e9a43828ef4", "ptp-calibration-build-config-hash"),
        ("image_gzip_sha256=ccaf4056cc522d4df11d9750d235dbf170916e90064ab8a993215e19a49c6fe4", "ptp-calibration-build-image-hash"),
        ("gemini_dtb_sha256=4ca3765d3ed1a39751c59387456de861091725321cdd5b7ec4cf715008a9d356", "ptp-calibration-build-dtb-hash"),
        ("dtb_count=119", "ptp-calibration-build-dtb-count"),
        ("sha256sums=passed", "ptp-calibration-build-checksums"),
        ("package_fetch=success;validated_package_only", "ptp-calibration-build-fetch"),
        ("ptp_calibration_contract=0214;ptp_state_required;BIG_L_2L_CCI;init_mon;dvfs_level;bin_spec;builder_enforced;default_off", "ptp-calibration-build-contract"),
        ("owner=unregistered", "ptp-calibration-build-owner-unregistered"),
        ("provider=none", "ptp-calibration-build-no-provider"),
        ("secure_write=none", "ptp-calibration-build-no-secure-write"),
        ("hardware_write=none", "ptp-calibration-build-no-write"),
        ("device_action=none", "ptp-calibration-build-no-device"),
        ("hardware_support_claim=NONE", "ptp-calibration-build-no-support-claim"),
        ("boot_candidate=false", "ptp-calibration-build-not-candidate"),
        ("runtime_evidence=none", "ptp-calibration-build-no-runtime"),
        ("device_boot=none", "ptp-calibration-build-no-boot"),
    ):
        require(ptp_calibration_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_MT6797_DVFSP_CALIBRATED_STATE_OWNER_SOURCE", "state-owner-source-build-claim"),
        ("repository_commit=180d5d7f3cd0f5402a0f2f3f98b027d4eb7de7d0", "state-owner-source-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "state-owner-source-build-origin"),
        ("repository_dirty=false", "state-owner-source-build-clean"),
        ("build_backend=buildbox", "state-owner-source-build-backend"),
        ("buildbox_status=validated", "state-owner-source-build-status"),
        ("buildbox_job=180d5d7f3cd0f5402a0f2f3f98b027d4eb7de7d0-dvfsp-protected-readback-m0", "state-owner-source-build-job"),
        ("patch_count=204", "state-owner-source-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-744b7285-b6696a3c", "state-owner-source-build-artifact"),
        ("source_sha256=be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc", "state-owner-source-build-source-hash"),
        ("patchset_sha256=744b72853fe87aca2dfec4aa50964ce1874401aff0334693a667e4f287ed7586", "state-owner-source-build-patchset-hash"),
        ("config_sha256=9561561944c875d1fadb5cee822fb9fa572a2e9cf82e4b8a45921e9a43828ef4", "state-owner-source-build-config-hash"),
        ("image_gzip_sha256=ccaf4056cc522d4df11d9750d235dbf170916e90064ab8a993215e19a49c6fe4", "state-owner-source-build-image-hash"),
        ("gemini_dtb_sha256=4ca3765d3ed1a39751c59387456de861091725321cdd5b7ec4cf715008a9d356", "state-owner-source-build-dtb-hash"),
        ("dtb_count=119", "state-owner-source-build-dtb-count"),
        ("sha256sums=passed", "state-owner-source-build-checksums"),
        ("package_fetch=success;validated_package_only", "state-owner-source-build-fetch"),
        ("owner_source_contract=0215;ptp_identity_required;full_provenance;calibration_rows;live_state;owner_handles;transition_mutex;dormant_registry_ops;default_off", "state-owner-source-build-contract"),
        ("owner=unregistered", "state-owner-source-build-owner-unregistered"),
        ("provider=none", "state-owner-source-build-no-provider"),
        ("secure_write=none", "state-owner-source-build-no-secure-write"),
        ("hardware_write=none", "state-owner-source-build-no-write"),
        ("device_action=none", "state-owner-source-build-no-device"),
        ("hardware_support_claim=NONE", "state-owner-source-build-no-support-claim"),
        ("boot_candidate=false", "state-owner-source-build-not-candidate"),
        ("runtime_evidence=none", "state-owner-source-build-no-runtime"),
        ("device_boot=none", "state-owner-source-build-no-boot"),
    ):
        require(state_owner_source_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_MT6797_DVFSP_STATE_OWNER_TRANSITION_ARBITRATION", "state-owner-arbitration-build-claim"),
        ("repository_commit=08085261af406e819c0eadb8c0e0b5e3db1bcbf3", "state-owner-arbitration-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "state-owner-arbitration-build-origin"),
        ("repository_dirty=false", "state-owner-arbitration-build-clean"),
        ("build_backend=buildbox", "state-owner-arbitration-build-backend"),
        ("buildbox_status=validated", "state-owner-arbitration-build-status"),
        ("buildbox_job=08085261af406e819c0eadb8c0e0b5e3db1bcbf3-dvfsp-protected-readback-m0", "state-owner-arbitration-build-job"),
        ("patch_count=205", "state-owner-arbitration-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-8a28b867-b6696a3c", "state-owner-arbitration-build-artifact"),
        ("source_sha256=be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc", "state-owner-arbitration-build-source-hash"),
        ("patchset_sha256=8a28b867f20d624be9fdc4e9bc7c96bad8a7436eb26844167e503cd614ea428f", "state-owner-arbitration-build-patchset-hash"),
        ("config_sha256=9561561944c875d1fadb5cee822fb9fa572a2e9cf82e4b8a45921e9a43828ef4", "state-owner-arbitration-build-config-hash"),
        ("image_gzip_sha256=ccaf4056cc522d4df11d9750d235dbf170916e90064ab8a993215e19a49c6fe4", "state-owner-arbitration-build-image-hash"),
        ("gemini_dtb_sha256=4ca3765d3ed1a39751c59387456de861091725321cdd5b7ec4cf715008a9d356", "state-owner-arbitration-build-dtb-hash"),
        ("dtb_count=119", "state-owner-arbitration-build-dtb-count"),
        ("sha256sums=passed", "state-owner-arbitration-build-checksums"),
        ("package_fetch=success;validated_package_only", "state-owner-arbitration-build-fetch"),
        ("owner_source_contract=0215;ptp_identity_required;full_provenance;calibration_rows;live_state;owner_handles;transition_mutex;dormant_registry_ops;default_off", "state-owner-arbitration-build-source-contract"),
        ("owner_arbitration_contract=0216;external_transition_lock;monotonic_generation;changed_generation_rejected;rollback_rejected;dormant_registry_ops;default_off", "state-owner-arbitration-build-contract"),
        ("owner=unregistered", "state-owner-arbitration-build-owner-unregistered"),
        ("provider=none", "state-owner-arbitration-build-no-provider"),
        ("secure_write=none", "state-owner-arbitration-build-no-secure-write"),
        ("hardware_write=none", "state-owner-arbitration-build-no-write"),
        ("device_action=none", "state-owner-arbitration-build-no-device"),
        ("hardware_support_claim=NONE", "state-owner-arbitration-build-no-support-claim"),
        ("boot_candidate=false", "state-owner-arbitration-build-not-candidate"),
        ("runtime_evidence=none", "state-owner-arbitration-build-no-runtime"),
        ("device_boot=none", "state-owner-arbitration-build-no-boot"),
    ):
        require(state_owner_arbitration_build_result, needle, label)
    for needle, label in (
        ("claim=COMPILE_ONLY_MT6797_DVFSP_STATE_OWNER_ARBITRATION_FAULT_LATCH", "state-owner-arbitration-fault-build-claim"),
        ("repository_commit=29ca7916439546ffaa834f8ffd67ee040576ae37", "state-owner-arbitration-fault-build-commit"),
        ("origin=https://github.com/ixoo/gemini-pda-mainline.git", "state-owner-arbitration-fault-build-origin"),
        ("repository_dirty=false", "state-owner-arbitration-fault-build-clean"),
        ("build_backend=buildbox", "state-owner-arbitration-fault-build-backend"),
        ("buildbox_status=validated", "state-owner-arbitration-fault-build-status"),
        ("buildbox_job=29ca7916439546ffaa834f8ffd67ee040576ae37-dvfsp-protected-readback-m0", "state-owner-arbitration-fault-build-job"),
        ("patch_count=206", "state-owner-arbitration-fault-build-patch-count"),
        ("artifact=linux-7.1.3-gemini-dvfsp-protected-readback-49af5073-b6696a3c", "state-owner-arbitration-fault-build-artifact"),
        ("source_sha256=be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc", "state-owner-arbitration-fault-build-source-hash"),
        ("patchset_sha256=49af50734e103316040a014500f2c06d893b0e4bbca50710039f96a445642f42", "state-owner-arbitration-fault-build-patchset-hash"),
        ("config_sha256=9561561944c875d1fadb5cee822fb9fa572a2e9cf82e4b8a45921e9a43828ef4", "state-owner-arbitration-fault-build-config-hash"),
        ("image_gzip_sha256=ccaf4056cc522d4df11d9750d235dbf170916e90064ab8a993215e19a49c6fe4", "state-owner-arbitration-fault-build-image-hash"),
        ("gemini_dtb_sha256=4ca3765d3ed1a39751c59387456de861091725321cdd5b7ec4cf715008a9d356", "state-owner-arbitration-fault-build-dtb-hash"),
        ("dtb_count=119", "state-owner-arbitration-fault-build-dtb-count"),
        ("sha256sums=passed", "state-owner-arbitration-fault-build-checksums"),
        ("package_fetch=success;validated_package_only", "state-owner-arbitration-fault-build-fetch"),
        ("fault_contract=0217;fault_latched;source_invalidated;reuse_rejected_until_reinit;clock_transition_reason", "state-owner-arbitration-fault-build-contract"),
        ("owner=unregistered", "state-owner-arbitration-fault-build-owner-unregistered"),
        ("provider=none", "state-owner-arbitration-fault-build-no-provider"),
        ("secure_write=none", "state-owner-arbitration-fault-build-no-secure-write"),
        ("hardware_write=none", "state-owner-arbitration-fault-build-no-write"),
        ("device_action=none", "state-owner-arbitration-fault-build-no-device"),
        ("hardware_support_claim=NONE", "state-owner-arbitration-fault-build-no-support-claim"),
        ("boot_candidate=false", "state-owner-arbitration-fault-build-not-candidate"),
        ("runtime_evidence=none", "state-owner-arbitration-fault-build-no-runtime"),
        ("device_boot=none", "state-owner-arbitration-fault-build-no-boot"),
    ):
        require(state_owner_arbitration_fault_build_result, needle, label)
    for needle, label in (
        ("claim=READ_ONLY_LIVE_DVFS_SOURCE_AVAILABILITY_AND_NONATOMICITY", "live-dvfs-probe-claim"),
        ("target=gemini;transport=ssh;os=Gemian;kernel=3.18.41+;device_action=none;hardware_write=none;backup=none", "live-dvfs-probe-target"),
        ("eem_endpoint=/proc/eem/eem_dump;readable=true;m_hw_res_words=19;init_modes=init1,init2;raw_payload=redacted", "live-dvfs-probe-eem"),
        ("ppm_endpoint=/proc/ppm/dump_cluster_{0,1,2}_dvfs_table;readable=true;entries_per_cluster=16;table_values=redacted", "live-dvfs-probe-ppm"),
        ("sample_spacing=one_second;read_order=oppidx_then_frequency_then_voltage;atomicity=not_proven", "live-dvfs-probe-spacing"),
        ("decision=runtime_opp_and_rail_state_is_mutable_and_proc_reads_are_not_a_coherent_snapshot", "live-dvfs-probe-decision"),
        ("required_owner_contract=single_transition_lock;generation_before_and_after;live_frequency_vproc_vsram_ppm_membership_from_one_owner", "live-dvfs-probe-owner-contract"),
        ("calibration_data=not_recorded;raw_eem_and_ppm_values=redacted", "live-dvfs-probe-redaction"),
        ("provider=none;cpu8_cpu9_admission=closed;boot_candidate=false", "live-dvfs-probe-no-admission"),
    ):
        require(live_dvfs_source_result, needle, label)
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
    if names.index("0202-soc-mediatek-bind-protected-owner-to-transition-lock.patch") >= names.index("0203-soc-mediatek-require-calibrated-table-state.patch"):
        raise AssertionError("calibrated table state is not after the transition lock")
    if names.index("0203-soc-mediatek-require-calibrated-table-state.patch") >= names.index("0204-thermal-mediatek-add-locked-MT6797-EEM-readback.patch"):
        raise AssertionError("EEM readback is not after calibrated table-state admission")
    if names.index("0204-thermal-mediatek-add-locked-MT6797-EEM-readback.patch") >= names.index("0205-soc-mediatek-derive-calibrated-table-from-EEM-readback.patch"):
        raise AssertionError("EEM calibration builder is not after EEM readback")
    if names.index("0205-soc-mediatek-derive-calibrated-table-from-EEM-readback.patch") >= names.index("0206-soc-mediatek-decode-protected-clock-readback.patch"):
        raise AssertionError("clock-state decoder is not after EEM calibration builder")
    if names.index("0206-soc-mediatek-decode-protected-clock-readback.patch") >= names.index("0207-soc-mediatek-bind-runtime-invalidation-events.patch"):
        raise AssertionError("runtime invalidation ledger is not after the clock-state decoder")
    if names.index("0207-soc-mediatek-bind-runtime-invalidation-events.patch") >= names.index("0208-soc-mediatek-register-runtime-notifier-binding.patch"):
        raise AssertionError("runtime notifier binding is not after the runtime invalidation ledger")
    if names.index("0208-soc-mediatek-register-runtime-notifier-binding.patch") >= names.index("0209-soc-mediatek-assemble-protected-state-snapshot.patch"):
        raise AssertionError("state snapshot assembler is not after the runtime notifier binding")
    if names.index("0209-soc-mediatek-assemble-protected-state-snapshot.patch") >= names.index("0210-soc-mediatek-add-protected-state-source-adapter.patch"):
        raise AssertionError("state source adapter is not after the snapshot assembler")
    if names.index("0210-soc-mediatek-add-protected-state-source-adapter.patch") >= names.index("0211-soc-mediatek-wire-protected-readbacks-to-state-source.patch"):
        raise AssertionError("state-source backend bridge is not after the state source adapter")
    if names.index("0211-soc-mediatek-wire-protected-readbacks-to-state-source.patch") >= names.index("0212-nvmem-mediatek-expose-MT6797-PTP-handoff-source.patch"):
        raise AssertionError("PTP handoff source is not after the state-source backend bridge")
    if names.index("0212-nvmem-mediatek-expose-MT6797-PTP-handoff-source.patch") >= names.index("0213-soc-mediatek-decode-MT6797-PTP-handoff-state.patch"):
        raise AssertionError("PTP state decoder is not after the PTP handoff source")
    if names.index("0213-soc-mediatek-decode-MT6797-PTP-handoff-state.patch") >= names.index("0214-soc-mediatek-bind-PTP-state-to-calibration-builder.patch"):
        raise AssertionError("PTP calibration binding is not after the PTP state decoder")
    if names.index("0214-soc-mediatek-bind-PTP-state-to-calibration-builder.patch") >= names.index("0215-soc-mediatek-add-calibrated-state-owner-source-binding.patch"):
        raise AssertionError("calibrated state-owner source binding is not after PTP calibration binding")
    if names.index("0215-soc-mediatek-add-calibrated-state-owner-source-binding.patch") >= names.index("0216-soc-mediatek-bind-state-owner-source-to-transition-generation.patch"):
        raise AssertionError("state-owner arbitration is not after calibrated state-owner source binding")
    if names.index("0216-soc-mediatek-bind-state-owner-source-to-transition-generation.patch") >= names.index("0217-soc-mediatek-latch-transition-arbitration-faults.patch"):
        raise AssertionError("state-owner arbitration fault latch is not after state-owner arbitration")
    if names.index("0217-soc-mediatek-latch-transition-arbitration-faults.patch") >= names.index("0218-soc-mediatek-register-arbitrated-state-owner.patch"):
        raise AssertionError("state-owner registration is not after the arbitration fault latch")

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
        if forbidden in calibrated_table_patch:
            raise AssertionError(f"unexpected calibrated-table hardware operation: {forbidden}")
        if forbidden in eem_calibration_source:
            raise AssertionError(f"unexpected EEM calibration hardware operation: {forbidden}")
        if forbidden in clock_state_source:
            raise AssertionError(f"unexpected clock-state hardware operation: {forbidden}")

    for forbidden in ("readl(", "writel(", "regulator_", "clk_", "arm_smccc",
                      "i2c_transfer", "platform_driver", "cpu_up(", "secure_write"):
        if forbidden in clock_state_source:
            raise AssertionError(f"unexpected clock-state operation: {forbidden}")
        if forbidden in state_snapshot_source:
            raise AssertionError(f"unexpected state-snapshot operation: {forbidden}")
        if forbidden in state_source_source:
            raise AssertionError(f"unexpected state-source operation: {forbidden}")
        if forbidden in state_source_backends_source:
            raise AssertionError(f"unexpected state-source bridge operation: {forbidden}")
        if forbidden in ptp_handoff_source:
            raise AssertionError(f"unexpected PTP handoff operation: {forbidden}")
        if forbidden in ptp_state_source:
            raise AssertionError(f"unexpected PTP state operation: {forbidden}")
        if forbidden in ptp_calibration_source:
            raise AssertionError(f"unexpected PTP calibration operation: {forbidden}")
    for forbidden in ("readl(", "writel(", "regulator_", "clk_", "arm_smccc",
                      "i2c_transfer", "platform_driver", "cpu_up(", "secure_write",
                      "register_cpu_notifier", "register_pm_notifier",
                      "notifier_call_chain"):
        if forbidden in runtime_source:
            raise AssertionError(f"unexpected runtime invalidation operation: {forbidden}")
    for forbidden in ("readl(", "writel(", "regulator_", "clk_", "arm_smccc",
                      "i2c_transfer", "platform_driver", "cpu_up(",
                      "psci_ops.cpu_on", "secure_write", "register_cpu_notifier(",
                      "unregister_cpu_notifier(", "notifier_call_chain"):
        if forbidden in runtime_binding_source:
            raise AssertionError(f"unexpected runtime binding operation: {forbidden}")
    for forbidden in ("readl(", "writel(", "regulator_", "clk_", "arm_smccc",
                      "i2c_transfer", "platform_driver", "cpu_up(",
                      "psci_ops.cpu_on", "secure_write"):
        if forbidden in state_snapshot_source:
            raise AssertionError(f"unexpected state-snapshot operation: {forbidden}")
        if forbidden in state_source_source:
            raise AssertionError(f"unexpected state-source operation: {forbidden}")

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
    print("calibrated_table_state=0203;MON_phase;BIG_L_2L_CCI_banks;frequency_voltage_vsram_ppm_rows;thermal_clock_rail_generations;registered_owner=0;no_provider;no_mmio;boot_candidate=false")
    print("eem_readback=0204;thermal_owner_lock;selector_write_restore;BIG_L_2L_CCI;offsets_0x218_0x21c_0x248_0x24c;raw_status_frequency_vop_anchors;registered_owner=0;no_provider;no_secure_write;hardware_write=none;device_action=none;boot_candidate=false")
    print("eem_calibration_builder=0205;raw_readback_anchor_match;BIG_normal_unit_conversion;16_row_interpolation;temperature_offset;record_cap;vsram_delta;full_provenance;registered_owner=0;no_provider;no_hardware_write;device_action=none;boot_candidate=false")
    print("clock_state_decoder=0206;raw_ll_l_b_cci_readbacks;vendor_26mhz_formula;pcw_posdiv_and_divider_decode;generation_tagged;inflight_change_rejected;registered_owner=0;no_provider;no_hardware_write;device_action=none;boot_candidate=false")
    print("runtime_invalidation=0207;vendor_cpu_online_cpu_down_prepare_cpu_down_failed_pm_suspend_prepare_pm_post_suspend;clock_rail_pcm_fault_mapping;monotonic_sequence;generation_epoch;replay_rejected;registered_owner=0;no_provider;no_hardware_write;device_action=none;boot_candidate=false")
    print("runtime_binding=0208;active_owner_required;cpuhp_online_down_prepare_down_failed;pm_suspend_resume_notifier;generation_tagged_source_callback;ledger_serialized;registration_atomic;disarm_before_unregistration;registered=0;no_provider;no_hardware_write;device_action=none;boot_candidate=false")
    print("state_snapshot_assembler=0209;all_four_clusters;clock_frequency_match;calibration_row_match;provenance_match;complete_live_fields;read_only;registered_owner=0;no_provider;no_hardware_write;device_action=none;boot_candidate=false")
    print("state_source_adapter=0210;clock_readback;bigidvfs_readback;eem_readback;calibration_builder;clock_decoder;live_fields;four_cluster_assembler;caller_held_transition_lock;fail_closed;registered_owner=0;no_provider;no_hardware_write;device_action=none;boot_candidate=false")
    print("state_source_backends=0211;caller_owned_device_tuple;clock_readback;bigidvfs_readback;eem_readback;calibration_live_callbacks_required;registered_owner=0;no_provider;no_hardware_write;device_action=none;boot_candidate=false")
    print("state_source_ptp_handoff=0212;read_only_nvmem;19_word_m_hw_res;calibration_callback_input;registered_owner=0;no_provider;no_hardware_write;device_action=none;boot_candidate=false")
    print("state_source_ptp_decode=0213;M_HW_RES1_7_9;BIG_L_2L_CCI;init_mon_required;dvfs_level;bin_spec;variant_id_required;pure;registered_owner=0;no_provider;no_hardware_write;device_action=none;boot_candidate=false")
    print("state_source_ptp_calibration=0214;ptp_state_required;bank_identity;init_mon;dvfs_level;bin_spec;builder_enforced;registered_owner=0;no_provider;no_hardware_write;device_action=none;boot_candidate=false")
    print("state_owner_source=0215;identity_callback;ptp_bound;calibration_rows;live_state;full_provenance;owner_handles;transition_mutex;dormant_registry_ops;registered_owner=0;no_provider;no_hardware_write;device_action=none;boot_candidate=false")
    print("state_owner_arbitration=0216;external_transition_lock;monotonic_generation;changed_generation_rejected;rollback_rejected;dormant_registry_ops;registered_owner=0;no_provider;no_hardware_write;device_action=none;boot_candidate=false")
    print("state_owner_arbitration_fault=0217;fault_latched;source_invalidated;reuse_rejected_until_reinit;clock_transition_reason;registered_owner=0;no_provider;no_hardware_write;device_action=none;boot_candidate=false")
    print("state_owner_registration=0218;owned_registry_callbacks;identity_checked;hold_release_bound;unregister_invalidates;default_off;registered_owner=0;provider=none;no_hardware_write;device_action=none;boot_candidate=false")
    print("live_dvfs_source_probe=20260809;eem_handoff_readable;ppm_tables_readable;opp_rail_state_mutable;proc_reads_nonatomic;raw_payload_redacted;owner_lock_and_generation_required;provider=none;cpu8_cpu9_admission=closed;boot_candidate=false")
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
