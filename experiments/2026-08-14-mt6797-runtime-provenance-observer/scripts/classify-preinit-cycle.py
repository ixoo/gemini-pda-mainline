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
EXPECTED_CANDIDATE_KERNEL = "3.18.79-gemini-provenance-preinit+"
EXPECTED_RECOVERY_KERNEL = "3.18.41+"


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


def classify(capture: Path, runtime_capture: Path | None = None) -> dict[str, str]:
    if not capture.is_dir() or capture.is_symlink():
        raise Classification("service-failure", "capture-directory-missing-or-unsafe", 4)
    cycle = records(capture / "cycle.txt")
    metadata = records(capture / "metadata.txt")
    for key, expected in {
        "wait_for_cycle": "yes",
        "boot_id_changed": "yes",
        "capture_kernel": EXPECTED_RECOVERY_KERNEL,
        "capture_arch": "aarch64",
        "expected_kernel": EXPECTED_RECOVERY_KERNEL,
    }.items():
        if cycle.get(key) != expected:
            raise Classification("rejected-attribution", f"cycle-mismatch:{key}", 5)
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
    runtime_result = "not-captured"
    runtime_reason = "direct-rndis-sample-absent"
    publication = "not-observed"
    result = "success-preinit-recovery"
    reason = "retained-checkpoint-and-execution-with-recovery-cycle"
    if runtime_capture is not None:
        if not runtime_capture.is_file() or runtime_capture.is_symlink():
            raise Classification("service-failure", "runtime-capture-missing-or-unsafe", 4)
        try:
            runtime_result, runtime_reason = runtime_validator.classify(runtime_capture)
        except runtime_validator.Classification as outcome:
            runtime_result, runtime_reason = outcome.result, outcome.reason
            if runtime_result in {"rejected-attribution", "rejected-safety"}:
                raise Classification(runtime_result, runtime_reason, outcome.code,
                                     "recovery-worker-reached")
        if runtime_result == "success":
            result = "success-runtime-publication"
            reason = "retained-recovery-and-stable-complete-runtime-publication"
            publication = "stable-complete"
        elif runtime_result == "inconclusive":
            publication = "inconclusive"
        else:
            publication = "not-observed"
    return {
        "runtime_classification": result,
        "runtime_reason": reason,
        "kernel_hang_localization": "recovery-worker-reached",
        "preinit_checkpoint": "observed",
        "recovery_execution": "observed",
        "automatic_restart": "attributed",
        "candidate_kernel_identity": (
            "release-and-marker" if EXPECTED_CANDIDATE_KERNEL in kernel_tokens
            else "exact-marker"
        ),
        "direct_runtime_classification": runtime_result,
        "direct_runtime_reason": runtime_reason,
        "runtime_publication": publication,
        "cpu8_cpu9_admission": "closed",
        "claim_scope": "preinit-localization-and-vendor-lifecycle-publication-only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pstore-capture", type=Path, required=True)
    parser.add_argument("--runtime-capture", type=Path)
    args = parser.parse_args()
    try:
        result = classify(args.pstore_capture, args.runtime_capture)
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
