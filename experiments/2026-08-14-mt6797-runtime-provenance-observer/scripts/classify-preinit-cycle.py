#!/usr/bin/env python3
"""Classify retained pre-init markers and an optional direct-USB sample."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import re
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
RUNTIME_VALIDATOR = SCRIPT_DIR / "validate-preinit-runtime.py"
RUNTIME_VALIDATOR_SHA256 = (
    "dcce5ea4d0eca7ad87474d673453463c1cadc298498c6915b5fb3b288510de90"
)
MARKER = "GEMINI_DVFSP_PROVENANCE_PREINIT_RECOVERY_20260815"
DIAGNOSTIC_MARKER = "GEMINI_DVFSP_PROVENANCE_DIAGNOSTIC_20260815"
EXPECTED_CANDIDATE_KERNEL = "3.18.79-gemini-provenance-preinit+"
EXPECTED_CANDIDATE = "99414cdecc4e031b12b93114b355fb3d44366d6e7b5092cb4f5f9132755d61c7"
EXPECTED_RECOVERY_KERNEL = "3.18.41+"
EARLY_BEGIN = "__GEMINI_PROVENANCE_EARLY_BEGIN__"
EARLY_END = "__GEMINI_PROVENANCE_EARLY_END__"


class Classification(Exception):
    def __init__(
        self,
        result: str,
        reason: str,
        code: int,
        localization: str = "not-established",
    ) -> None:
        super().__init__(reason)
        self.result = result
        self.reason = reason
        self.code = code
        self.localization = localization


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if digest(RUNTIME_VALIDATOR) != RUNTIME_VALIDATOR_SHA256:
    raise SystemExit("error: pinned pre-init runtime validator changed")
spec = importlib.util.spec_from_file_location(
    "preinit_cycle_runtime", RUNTIME_VALIDATOR
)
if spec is None or spec.loader is None:
    raise SystemExit("error: cannot load pinned pre-init runtime validator")
runtime_validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime_validator)


def records(path: Path) -> dict[str, str]:
    if not path.is_file() or path.is_symlink():
        raise Classification("service-failure", f"unsafe-capture-file:{path.name}", 4)
    result: dict[str, str] = {}
    for line in path.read_text(errors="strict").splitlines():
        match = re.fullmatch(r"([A-Za-z0-9_+./:-]+)=([^\n]*)", line)
        if match is None:
            continue
        key, value = match.groups()
        if key in result:
            raise Classification("rejected-attribution", f"duplicate-key:{key}", 5)
        result[key] = value
    return result


def console_text(capture: Path) -> str:
    pstore = capture / "pstore"
    if not pstore.is_dir() or pstore.is_symlink():
        raise Classification("service-failure", "pstore-directory-missing-or-unsafe", 4)
    entries = list(pstore.iterdir())
    if any(not entry.is_file() or entry.is_symlink() for entry in entries):
        raise Classification("rejected-attribution", "unsafe-pstore-entry", 5)
    consoles = sorted(
        (entry for entry in entries if entry.name.startswith("console-ramoops")),
        key=lambda entry: entry.name,
    )
    if not consoles:
        raise Classification("service-failure", "console-ramoops-absent", 4)
    return "\n".join(
        entry.read_bytes().decode("utf-8", errors="replace") for entry in consoles
    )


def marker_lines(text: str, token: str) -> list[str]:
    return [line for line in text.splitlines() if MARKER in line and token in line]


def require_tokens(line: str, tokens: tuple[str, ...], label: str) -> None:
    missing = [token for token in tokens if token not in line]
    if missing:
        raise Classification(
            "rejected-safety",
            f"{label}-contract-mismatch:{','.join(missing)}",
            5,
            "late-init-reached" if label == "checkpoint" else "recovery-worker-reached",
        )


def validate_cycle(cycle: dict[str, str], metadata: dict[str, str]) -> str:
    for key, expected in {
        "boot_id_changed": "yes",
        "capture_kernel": EXPECTED_RECOVERY_KERNEL,
        "capture_arch": "aarch64",
        "expected_kernel": EXPECTED_RECOVERY_KERNEL,
    }.items():
        if cycle.get(key) != expected:
            raise Classification("rejected-attribution", f"cycle-mismatch:{key}", 5)
    if cycle.get("wait_for_cycle") == "yes":
        return "collector-observed-disconnect-reconnect"
    if cycle.get("cycle_evidence") != "owner-observed-automatic-restart":
        raise Classification("rejected-attribution", "cycle-mismatch:cycle_evidence", 5)
    if cycle.get("automatic_restart_observed") != "yes":
        raise Classification(
            "rejected-attribution", "cycle-mismatch:automatic_restart_observed", 5
        )
    initial = cycle.get("initial_boot_id_sha256", "")
    final = cycle.get("final_boot_id_sha256", "")
    if not re.fullmatch(r"[0-9a-f]{64}", initial) or not re.fullmatch(
        r"[0-9a-f]{64}", final
    ):
        raise Classification("rejected-attribution", "cycle-boot-id-hash-malformed", 5)
    if initial == final:
        raise Classification("rejected-attribution", "cycle-boot-id-unchanged", 5)
    if metadata.get("boot_id_sha256") != final:
        raise Classification(
            "rejected-attribution", "cycle-recovery-boot-id-mismatch", 5
        )
    if cycle.get("installed_full_sha256") != EXPECTED_CANDIDATE:
        raise Classification("rejected-attribution", "cycle-candidate-mismatch", 5)
    return "owner-observed-restart-with-changed-boot-id"


def retained_runtime(text: str) -> tuple[str, str]:
    runtime = runtime_validator.runtime
    payloads: list[str] = []
    prefix = f"{DIAGNOSTIC_MARKER} "
    for line in text.splitlines():
        if prefix in line:
            payloads.append(line.split(prefix, 1)[1])
    if EARLY_BEGIN not in payloads and EARLY_END not in payloads:
        return "not-captured", "retained-early-sample-absent"
    try:
        body = runtime.unique_region(payloads, EARLY_BEGIN, EARLY_END)
        outer_lines: list[str] = []
        in_snapshot = False
        for line in body:
            if re.fullmatch(r"__GEMINI_PROVENANCE_EARLY_SNAPSHOT_[12]_BEGIN__", line):
                in_snapshot = True
            elif re.fullmatch(r"__GEMINI_PROVENANCE_EARLY_SNAPSHOT_[12]_END__", line):
                in_snapshot = False
            elif not in_snapshot:
                outer_lines.append(line)
        outer = runtime.parse_records(outer_lines)
        for key, expected in {
            "marker": DIAGNOSTIC_MARKER,
            "kernel_release": EXPECTED_CANDIDATE_KERNEL,
            "architecture": "aarch64",
            "debugfs": "debugfs-mounted-read-only",
            "state_path": "/sys/kernel/debug/gemini_dvfsp_provenance/state",
            "state_access": "readable",
            "state_mode": "444",
            "device_partition_reads": "none",
            "device_storage_writes": "none",
            "dvfsp_hardware_write": "none",
            "reboot_request": "none",
        }.items():
            if outer.get(key) != expected:
                raise runtime.Classification(
                    "rejected-attribution", f"retained-identity-mismatch:{key}", 5
                )
        first = runtime.parse_records(
            runtime.unique_region(
                body,
                "__GEMINI_PROVENANCE_EARLY_SNAPSHOT_1_BEGIN__",
                "__GEMINI_PROVENANCE_EARLY_SNAPSHOT_1_END__",
            ),
            runtime.SNAPSHOT_KEYS,
        )
        second = runtime.parse_records(
            runtime.unique_region(
                body,
                "__GEMINI_PROVENANCE_EARLY_SNAPSHOT_2_BEGIN__",
                "__GEMINI_PROVENANCE_EARLY_SNAPSHOT_2_END__",
            ),
            runtime.SNAPSHOT_KEYS,
        )
        if set(first) != runtime.SNAPSHOT_KEYS or set(second) != runtime.SNAPSHOT_KEYS:
            raise runtime.Classification(
                "rejected-attribution", "retained-snapshot-inventory-mismatch", 5
            )
        for snapshot in (first, second):
            for key, expected in {
                "owner_handle": "0",
                "transition_handle": "0",
                "coherent_transition_owner": "0",
                "provider": "none",
                "hardware_write": "none",
                "cpu8_cpu9_admission": "closed",
            }.items():
                if snapshot.get(key) != expected:
                    raise runtime.Classification(
                        "rejected-safety", f"retained-nonclaim-violated:{key}", 5
                    )
            if snapshot.get("abi") != "1":
                raise runtime.Classification(
                    "rejected-attribution", "retained-observer-abi-mismatch", 5
                )
            if snapshot.get("state") == "fault":
                raise runtime.Classification(
                    "rejected-safety", "retained-observer-reported-fault", 5
                )
        if first != second:
            raise runtime.Classification(
                "inconclusive", "retained-two-snapshots-not-stable", 3
            )
        incomplete: list[str] = []
        if first["state"] != "available" or first["observation_complete"] != "1":
            incomplete.append("retained-observer-not-complete")
        for key in (
            "variant_id",
            "observer_generation",
            "table_epoch",
            "calibration_handle",
        ):
            if runtime.unsigned(first, key) == 0:
                incomplete.append(f"retained-zero-{key}")
        if runtime.unsigned(first, "ppm_expected_cluster_count") != 3:
            incomplete.append("retained-unexpected-cluster-count")
        if first["ppm_cluster_mask"] != "0x00000007":
            incomplete.append("retained-incomplete-ppm-mask")
        if (
            first["eem_required_bank_mask"] != "0x0000003b"
            or first["eem_calibration_bank_mask"] != "0x0000003b"
        ):
            incomplete.append("retained-incomplete-eem-mask")
        if runtime.unsigned(first, "table_commit_count") < 3:
            incomplete.append("retained-insufficient-table-commits")
        if runtime.unsigned(first, "calibration_bank_publish_count") < 5:
            incomplete.append("retained-insufficient-bank-publications")
        if runtime.unsigned(first, "calibration_publish_count") < 1:
            incomplete.append("retained-missing-calibration-publication")
        runtime.unsigned(first, "calibration_invalidate_count")
        if incomplete:
            raise runtime.Classification("inconclusive", ",".join(incomplete), 3)
    except runtime.Classification as outcome:
        return outcome.result, outcome.reason
    return "success", "stable-complete-retained-read-only-lifecycle-publication"


def classify(
    capture: Path,
    runtime_capture: Path | None = None,
    cycle_record: Path | None = None,
) -> dict[str, str]:
    if not capture.is_dir() or capture.is_symlink():
        raise Classification("service-failure", "capture-directory-missing-or-unsafe", 4)
    cycle = records(cycle_record if cycle_record is not None else capture / "cycle.txt")
    metadata = records(capture / "metadata.txt")
    cycle_attribution = validate_cycle(cycle, metadata)
    for key, expected in {
        "kernel": EXPECTED_RECOVERY_KERNEL,
        "architecture": "aarch64",
        "pstore_directory": "present",
    }.items():
        if metadata.get(key) != expected:
            raise Classification("rejected-attribution", f"recovery-mismatch:{key}", 5)

    text = console_text(capture)
    checkpoints = marker_lines(text, "checkpoint=pre-init")
    executions = marker_lines(text, "recovery=executing")
    if len(checkpoints) > 1 or len(executions) > 1:
        raise Classification("rejected-attribution", "duplicate-preinit-marker", 5)
    if not checkpoints and not executions:
        raise Classification("service-failure", "preinit-marker-absent", 4)
    if executions and not checkpoints:
        raise Classification(
            "rejected-attribution",
            "recovery-execution-without-checkpoint",
            5,
            "recovery-worker-reached",
        )
    require_tokens(
        checkpoints[0],
        (
            "recovery=armed",
            "deadline_seconds=120",
            "pstore_console=required",
            "storage_access=none",
            "dvfsp_hardware_write=none",
            "cpu8_cpu9_admission=closed",
        ),
        "checkpoint",
    )
    if not executions:
        raise Classification(
            "inconclusive",
            "preinit-checkpoint-without-recovery-execution",
            3,
            "late-init-reached",
        )
    require_tokens(
        executions[0],
        (
            "reset=emergency-restart",
            "storage_access=none",
            "dvfsp_hardware_write=none",
            "cpu8_cpu9_admission=closed",
        ),
        "execution",
    )
    checkpoint_offset = text.find(checkpoints[0])
    execution_offset = text.find(executions[0])
    if checkpoint_offset < 0 or execution_offset <= checkpoint_offset:
        raise Classification("rejected-attribution", "preinit-marker-order-invalid", 5)

    kernel_tokens = set(
        re.findall(r"3\.18\.79-gemini-provenance-[A-Za-z0-9+._-]+", text)
    )
    if kernel_tokens and EXPECTED_CANDIDATE_KERNEL not in kernel_tokens:
        raise Classification("rejected-attribution", "candidate-kernel-identity-mismatch", 5)
    retained_result, retained_reason = retained_runtime(text)
    direct_result = "not-captured"
    direct_reason = "direct-rndis-sample-absent"
    publication = "stable-complete" if retained_result == "success" else "not-observed"
    result = "success-preinit-recovery"
    reason = "retained-checkpoint-and-execution-with-recovery-cycle"
    if retained_result == "success":
        result = "success-runtime-publication"
        reason = "retained-recovery-and-stable-complete-retained-publication"
    elif retained_result == "inconclusive":
        publication = "inconclusive"
    elif retained_result in {"rejected-attribution", "rejected-safety"}:
        raise Classification(retained_result, retained_reason, 5, "recovery-worker-reached")
    if runtime_capture is not None:
        if not runtime_capture.is_file() or runtime_capture.is_symlink():
            raise Classification("service-failure", "runtime-capture-missing-or-unsafe", 4)
        try:
            direct_result, direct_reason = runtime_validator.classify(runtime_capture)
        except runtime_validator.Classification as outcome:
            direct_result, direct_reason = outcome.result, outcome.reason
            if direct_result in {"rejected-attribution", "rejected-safety"}:
                raise Classification(direct_result, direct_reason, outcome.code,
                                     "recovery-worker-reached")
        if direct_result == "success":
            result = "success-runtime-publication"
            if retained_result != "success":
                reason = "retained-recovery-and-stable-complete-direct-publication"
            publication = "stable-complete"
        elif direct_result == "inconclusive" and retained_result != "success":
            publication = "inconclusive"
        elif retained_result not in {"success", "inconclusive"}:
            publication = "not-observed"
    return {
        "runtime_classification": result,
        "runtime_reason": reason,
        "kernel_hang_localization": "recovery-worker-reached",
        "preinit_checkpoint": "observed",
        "recovery_execution": "observed",
        "automatic_restart": "attributed",
        "restart_attribution": cycle_attribution,
        "candidate_kernel_identity": (
            "release-and-marker" if EXPECTED_CANDIDATE_KERNEL in kernel_tokens
            else "exact-marker"
        ),
        "retained_runtime_classification": retained_result,
        "retained_runtime_reason": retained_reason,
        "direct_runtime_classification": direct_result,
        "direct_runtime_reason": direct_reason,
        "runtime_publication": publication,
        "cpu8_cpu9_admission": "closed",
        "claim_scope": "preinit-localization-and-vendor-lifecycle-publication-only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pstore-capture", type=Path, required=True)
    parser.add_argument("--runtime-capture", type=Path)
    parser.add_argument("--cycle-record", type=Path)
    args = parser.parse_args()
    try:
        result = classify(args.pstore_capture, args.runtime_capture, args.cycle_record)
        code = 0
    except Classification as outcome:
        result = {
            "runtime_classification": outcome.result,
            "runtime_reason": outcome.reason,
            "kernel_hang_localization": outcome.localization,
            "preinit_checkpoint": (
                "observed" if outcome.localization != "not-established" else "not-observed"
            ),
            "recovery_execution": (
                "observed" if outcome.localization == "recovery-worker-reached" else "not-observed"
            ),
            "automatic_restart": "not-attributed",
            "direct_runtime_classification": "not-evaluated",
            "runtime_publication": "not-observed",
            "cpu8_cpu9_admission": "closed",
            "claim_scope": "preinit-localization-and-vendor-lifecycle-publication-only",
        }
        code = outcome.code
    for key, value in result.items():
        print(f"{key}={value}")
    return code


if __name__ == "__main__":
    sys.exit(main())
