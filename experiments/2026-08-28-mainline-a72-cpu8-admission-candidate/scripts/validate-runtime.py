#!/usr/bin/env python3
"""Classify one exact live CPU8 admission capture."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import re


SCRIPT_DIR = Path(__file__).resolve().parent
LEDGER_VALIDATOR = SCRIPT_DIR / "validate-transition-ledger.py"
LEDGER_VALIDATOR_SHA256 = "cefe3d19ad05c4facbdff7725667c33105d5d714c9d6b32d5ba993d5fccd9e85"
BEGIN = "__A72_ADMISSION_RUNTIME_BEGIN__"
END = "__A72_ADMISSION_RUNTIME_END__"
MARKERS_BEGIN = "__A72_ADMISSION_MARKERS_BEGIN__"
MARKERS_END = "__A72_ADMISSION_MARKERS_END__"
CANDIDATE = "fde53dca1dcbc36297897dbcd6086488d117bf45714833858e17987cb6579dd0"
RELEASE = "7.1.3-gemini-a72-admission"
ADMISSION = re.compile(
    r"GEMINI_A72_ADMISSION_V1 state=terminal ret=(-?\d+) "
    r"consumed=1 requests=(\d+)/0/0 retries=0"
)


class Classification(Exception):
    def __init__(self, result: str, reason: str) -> None:
        super().__init__(reason)
        self.result = result
        self.reason = reason


def reject(result: str, reason: str) -> None:
    raise Classification(result, reason)


def load_ledger_module() -> object:
    digest = hashlib.sha256(LEDGER_VALIDATOR.read_bytes()).hexdigest()
    if digest != LEDGER_VALIDATOR_SHA256:
        raise AssertionError("transition-ledger validator changed")
    spec = importlib.util.spec_from_file_location("transition_ledger_validator", LEDGER_VALIDATOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LEDGER = load_ledger_module()


def scalar_values(text: str) -> tuple[dict[str, str], str]:
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        reject("rejected-attribution", "non-unique-runtime-section")
    start = text.index(BEGIN) + len(BEGIN)
    finish = text.index(END, start)
    section = text[start:finish].replace("\r", "")
    if section.count(MARKERS_BEGIN) != 1 or section.count(MARKERS_END) != 1:
        reject("rejected-attribution", "non-unique-marker-section")
    marker_start = section.index(MARKERS_BEGIN) + len(MARKERS_BEGIN)
    marker_finish = section.index(MARKERS_END, marker_start)
    markers = section[marker_start:marker_finish]
    scalar_text = section[:section.index(MARKERS_BEGIN)] + section[
        marker_finish + len(MARKERS_END):
    ]
    values: dict[str, str] = {}
    for raw in scalar_text.splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key) or key in values:
            reject("rejected-attribution", "malformed-or-duplicate-key")
        values[key] = value
    return values, markers


def classify_text(text: str) -> tuple[str, str, dict[str, str | int]]:
    values, markers = scalar_values(text)
    expected = {
        "installed_full_sha256": CANDIDATE,
        "kernel_release": RELEASE,
        "architecture": "aarch64",
        "model": "MT6797X",
        "compatible": "planet,gemini-pda,mediatek,mt6797,",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "maxcpus8_tokens": "1",
        "udc_devices": "1",
        "block_mounts": "0",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "driver_binding_changes": "none",
        "userspace_regulator_request": "none",
        "userspace_clock_request": "none",
        "userspace_secure_call_request": "none",
        "userspace_cpu_request": "none",
        "reboot_request": "none",
    }
    safety = {
        "cpu_online", "cpu_offline", "maxcpus8_tokens", "block_mounts",
        "device_partition_reads", "device_storage_writes",
        "userspace_regulator_request", "userspace_clock_request",
        "userspace_secure_call_request", "userspace_cpu_request", "reboot_request",
    }
    for key, required in expected.items():
        if values.get(key) != required:
            reject("rejected-safety" if key in safety else "rejected-attribution",
                   f"{key}-mismatch")
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
                        values.get("boot_id", "")):
        reject("rejected-attribution", "malformed-boot-id")
    if not re.fullmatch(r"\d+(?:\.\d+)?", values.get("uptime_seconds", "")):
        reject("rejected-attribution", "malformed-uptime")
    if not re.fullmatch(r"\d+", values.get("pstore_files", "")):
        reject("rejected-attribution", "malformed-pstore-count")
    ledger_hex = values.get("transition_ledger_hex", "")
    if not re.fullmatch(r"[0-9a-f]{168}", ledger_hex):
        reject("rejected-ledger", "malformed-transition-ledger-hex")
    try:
        ledger_state, latest, copy = LEDGER.classify(bytes.fromhex(ledger_hex))
    except ValueError:
        reject("rejected-ledger", "invalid-transition-ledger")

    matches = ADMISSION.findall(markers)
    if len(matches) != 1:
        reject("rejected-attribution", "non-unique-admission-terminal")
    ret, requests = (int(value) for value in matches[0])
    details: dict[str, str | int] = {
        "admission_ret": ret,
        "cpu8_requests": requests,
        "ledger_state": ledger_state,
        "ledger_copy": copy if copy is not None else "none",
        "ledger_generation": latest["generation"] if latest is not None else "none",
        "ledger_phase": latest["phase"] if latest is not None else "none",
        "ledger_stage": latest["stage"] if latest is not None else "none",
        "ledger_terminal": latest["terminal"] if latest is not None else "none",
        "cpu_online": values.get("cpu_online", "missing"),
        "cpu_offline": values.get("cpu_offline", "missing"),
    }
    if (ret != 0 and requests == 0 and values.get("cpu_online") == "0-7" and
            values.get("cpu_offline") == "8-9"):
        details["ledger_attribution"] = "not-current-zero-request"
        return "serviceable-pre-request-rejection", "exact-zero-request-terminal", details
    if ledger_state != "committed-valid" or latest is None or copy is None:
        reject("rejected-ledger", "requested-transition-ledger-not-committed")
    if (ret == 0 and requests == 1 and values.get("cpu_online") == "0-8" and
            values.get("cpu_offline") == "9" and latest["phase"] == 3 and
            latest["stage"] == 9 and latest["terminal"] == 5):
        return "serviceable-cpu8-online-proof", "exact-one-shot-success", details
    if (ret != 0 and requests == 1 and values.get("cpu_online") == "0-7" and
            values.get("cpu_offline") == "8-9" and latest["phase"] == 3 and
            latest["terminal"] in (1, 2, 3, 4)):
        return "serviceable-cpu8-transition-failure", "exact-retained-terminal-stage", details
    reject("rejected-decision", "unsupported-runtime-combination")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result, reason, details = classify_text(
            args.capture.read_text(encoding="utf-8", errors="replace")
        )
    except Classification as error:
        result, reason, details = error.result, error.reason, {}
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    for key, value in details.items():
        print(f"{key}={value}")
    print("cpu9_request=none")
    print("retry_path=none")
    print("cpu_off_path=none")
    print("native_reboot_requested=no")
    return 0 if result.startswith("serviceable-") else 3


if __name__ == "__main__":
    raise SystemExit(main())
