#!/usr/bin/env python3
"""Classify one exact protected-readback observer netcat capture."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


BEGIN = "__PROTECTED_READBACK_RUNTIME_BEGIN__"
END = "__PROTECTED_READBACK_RUNTIME_END__"
DMESG_BEGIN = "__PROTECTED_READBACK_DMESG_BEGIN__"
DMESG_END = "__PROTECTED_READBACK_DMESG_END__"
CANDIDATE = "30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a"
RELEASE = "7.1.3-gemini-protected-readback-ro"
MODEL = "Planet Computers Gemini PDA (protected readback observer)"
TAG = "GEMINI_PROTECTED_READBACK_V1"
HEX = r"0x[0-9a-fA-F]{8}"
CLOCK = re.compile(
    rf"{TAG} clock ret=(-?\d+) abi=(\d+) generation=(\d+) "
    rf"muxsel=({HEX}) ckdiv=({HEX}) "
    rf"pll_ll=({HEX}),({HEX}),({HEX}) "
    rf"pll_l=({HEX}),({HEX}),({HEX}) "
    rf"pll_cci=({HEX}),({HEX}),({HEX}) "
    rf"cspm_swctrl=({HEX}),({HEX}),({HEX}) "
    rf"cspm_hwsta=({HEX}),({HEX}),({HEX}),({HEX})$"
)
BIGIDVFS = re.compile(
    rf"{TAG} bigidvfs ret=(-?\d+) abi=(\d+) generation=(\d+) "
    rf"pll_pcw=({HEX}) pll_enable_posdiv=({HEX}) "
    rf"sram_selector=({HEX}) control=({HEX})$"
)
COMPLETE = (
    f"{TAG} state=complete attempts=1 clock_calls=1 bigidvfs_calls=1 "
    "cpu_requests=0 owner_registration=0"
)


class Classification(Exception):
    def __init__(self, result: str, reason: str) -> None:
        super().__init__(reason)
        self.result = result
        self.reason = reason


def reject(result: str, reason: str) -> None:
    raise Classification(result, reason)


def section(text: str, begin: str, end: str) -> str:
    if text.count(begin) != 1 or text.count(end) != 1:
        reject("rejected-attribution", f"non-unique-{begin.strip('_').lower()}")
    start = text.index(begin) + len(begin)
    finish = text.index(end, start)
    if finish < start:
        reject("rejected-attribution", "reversed-section")
    return text[start:finish].replace("\r", "")


def key_values(text: str) -> dict[str, str]:
    dmesg_start = text.find(DMESG_BEGIN)
    dmesg_end = text.find(DMESG_END)
    if dmesg_start < 0 or dmesg_end < dmesg_start:
        reject("rejected-attribution", "missing-dmesg-section")
    metadata = text[:dmesg_start] + text[dmesg_end + len(DMESG_END) :]
    values: dict[str, str] = {}
    for raw in metadata.splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key) or key in values:
            reject("rejected-attribution", "malformed-or-duplicate-key")
        values[key] = value
    return values


def tagged_lines(dmesg: str, marker: str) -> list[str]:
    return [line[line.index(marker) :] for line in dmesg.splitlines() if marker in line]


def classify_text(text: str) -> tuple[str, str]:
    runtime = section(text, BEGIN, END)
    dmesg = section(runtime, DMESG_BEGIN, DMESG_END)
    values = key_values(runtime)
    expected = {
        "installed_full_sha256": CANDIDATE,
        "kernel_release": RELEASE,
        "architecture": "aarch64",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "model": MODEL,
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "driver_binding_changes": "none",
        "secure_write_request": "none",
        "owner_registration_request": "none",
        "cpu_admission_request": "none",
        "reboot_request": "none",
    }
    for key, required in expected.items():
        if values.get(key) != required:
            result = "rejected-safety" if key in {"cpu_online", "cpu_offline"} else "rejected-attribution"
            reject(result, f"{key}-mismatch")
    if not re.fullmatch(
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", values.get("boot_id", "")
    ):
        reject("rejected-attribution", "malformed-boot-id")
    if not re.fullmatch(r"\d+(?:\.\d+)?", values.get("uptime_seconds", "")):
        reject("rejected-attribution", "malformed-uptime")
    if "maxcpus=8" not in values.get("cmdline", "").split():
        reject("rejected-safety", "maxcpus-policy-missing")
    for key in ("clock_record_count", "bigidvfs_record_count", "completion_record_count"):
        if not re.fullmatch(r"\d+", values.get(key, "")):
            reject("rejected-attribution", f"malformed-{key}")

    clock_lines = tagged_lines(dmesg, f"{TAG} clock ")
    bigidvfs_lines = tagged_lines(dmesg, f"{TAG} bigidvfs ")
    complete_lines = tagged_lines(dmesg, f"{TAG} state=complete ")
    observed = {
        "clock_record_count": len(clock_lines),
        "bigidvfs_record_count": len(bigidvfs_lines),
        "completion_record_count": len(complete_lines),
    }
    for key, count in observed.items():
        if int(values[key]) != count:
            reject("rejected-attribution", f"{key}-disagrees")
        if count != 1:
            reject("rejected-attribution", f"{key}-not-one")
    all_tagged = tagged_lines(dmesg, TAG)
    if len(all_tagged) != 3:
        reject("rejected-attribution", "unexpected-tagged-record")

    clock = CLOCK.fullmatch(clock_lines[0])
    bigidvfs = BIGIDVFS.fullmatch(bigidvfs_lines[0])
    if not clock or not bigidvfs:
        reject("rejected-attribution", "malformed-transport-record")
    if complete_lines[0] != COMPLETE:
        reject("rejected-safety", "completion-contract-mismatch")
    clock_ret, clock_abi, clock_generation = map(int, clock.groups()[:3])
    big_ret, big_abi, big_generation = map(int, bigidvfs.groups()[:3])
    if clock_ret != 0 or big_ret != 0:
        reject("transport-failure", "protected-readback-returned-error")
    if (clock_abi, big_abi) != (1, 1):
        reject("rejected-attribution", "transport-abi-mismatch")
    if (clock_generation, big_generation) != (1, 1):
        reject("rejected-attribution", "transport-generation-not-one")
    return "success-protected-readback", "exact-one-shot-records"


def classify(path: Path) -> tuple[str, str]:
    try:
        return classify_text(path.read_text(encoding="utf-8", errors="replace"))
    except Classification as result:
        return result.result, result.reason


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    result, reason = classify(args.capture)
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"protected_readback={'accepted' if result == 'success-protected-readback' else 'not-accepted'}")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=one-shot-protected-readback-records-only")
    return 0 if result == "success-protected-readback" else 3


if __name__ == "__main__":
    raise SystemExit(main())
