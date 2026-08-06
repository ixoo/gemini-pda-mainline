#!/usr/bin/env python3
"""Re-audit the current A41/provider/A26/A14 admission blockers."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ADMISSION = ROOT / "experiments/2026-08-05-a72-membership-admission-contract/results/admission-lock-contract.tsv"
A41_PLAN = ROOT / "experiments/2026-08-05-a72-a41-immutable-plan/results/implementation.tsv"
A41_IDENTITY = ROOT / "experiments/2026-08-05-a72-a41-kernel-identity/results/implementation.tsv"
A41_OWNER = ROOT / "experiments/2026-08-05-a72-a41-runtime-evidence-owner/results/implementation.tsv"
A41_PROFILE = ROOT / "experiments/2026-08-05-a72-a41-capability-profile/README.md"
PROVIDER_ORACLE = ROOT / "experiments/2026-08-06-da921x-page-owner-audit/results/oracle.txt"
P32_RESULT = ROOT / "experiments/2026-08-06-a72-p32-r-review/results/p32r-buildbox-validation-20260806.txt"
A25_RESULT = ROOT / "experiments/2026-08-06-a72-a25-callback-review/results/a25-review-20260806.txt"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def tsv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as stream:
        return {row["id"]: row for row in csv.DictReader(stream, delimiter="\t")}


def key_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    with path.open() as stream:
        for line in stream:
            fields = line.rstrip("\n").split("\t")
            if len(fields) >= 2 and fields[0] != "key":
                values[fields[0]] = fields[1]
    return values


def require_text(path: Path, *tokens: str) -> str:
    text = path.read_text()
    for token in tokens:
        require(token in text, f"{path.name} missing {token!r}")
    return text


def main() -> int:
    admission = tsv(ADMISSION)
    for identifier in ("A14", "A25", "A26", "A37", "A39", "A40"):
        require(identifier in admission, f"missing admission row {identifier}")
        require(admission[identifier]["implementation_state"] == "contract-only-blocked",
                f"{identifier} changed out of the frozen blocked state")

    require_text(ADMISSION, "A14\tcpu-operations", "A26\tadmission")
    require("cpu_boot-returns-EAGAIN" in admission["A26"]["rule"], "A26 boot veto drifted")
    require("cpu-disable-veto-required" in admission["A14"]["failure"], "A14 disable veto drifted")
    require("P32" in admission["A26"]["rule"], "A26 no longer names P32")
    require("A37-auto-rollback-hazard" in admission["A25"]["rule"], "A25 rollback hazard missing")
    require("private-big_on" in admission["A40"]["rule"], "A40 private proof row drifted")

    a41_rows = [key_values(path) for path in (A41_PLAN, A41_IDENTITY, A41_OWNER)]
    for rows in a41_rows:
        require(rows.get("a41_complete") == "no", "an A41 source milestone claims completion")
        require(rows.get("build_authorized") == "no", "A41 build authorization changed")
        require(rows.get("device_action_authorized") == "no", "A41 device authorization changed")
    require_text(A41_PROFILE, "A41 complete | `no`", "-EAGAIN", "READY")

    provider = require_text(PROVIDER_ORACLE, "decision=BLOCK_WRITABLE_PROVIDER",
                            "hardware_action=none", "status=PASS_NEGATIVE_AUDIT")
    require("write-absent" in provider, "provider audit no longer proves write absence")

    p32 = require_text(P32_RESULT, "claim=P32R_DEDICATED_PROFILE_BUILDBOX_VALIDATED",
                       "status=PASS_DEDICATED_BUILDBOX_VALIDATED",
                       "CONFIG_ARM64_MT6797_A72_P32_ROLLBACK=y",
                       "device_boot_or_write=NOT_PERFORMED")
    a25 = require_text(A25_RESULT, "status=PASS_PARTIAL_A25", "same_boot_numeric_identity=OPEN_H13")
    require("PASS_DEDICATED_BUILDBOX_VALIDATED" in p32 and "PASS_PARTIAL_A25" in a25,
            "current source-only evidence is not passing")

    print("claim=PARTIAL_ADMISSION_GATE_REAUDIT")
    print("A14=BLOCKED_DISABLE_VETO")
    print("A25=PARTIAL_SOURCE_REVIEW_H13_OPEN")
    print("A26=BLOCKED_BOOT_VETO")
    print("A37=BLOCKED_P32_TERMINAL_GUARD_REVIEW")
    print("A39=BLOCKED_EARLY_SECONDARY_INVENTORY")
    print("A40=BLOCKED_PRIVATE_BRANCH_FRESHNESS")
    print("A41=INCOMPLETE_READY_UNREACHABLE")
    print("provider=BLOCK_WRITABLE_PROVIDER")
    print("cpu_on_cpu_off_device_action=CLOSED")
    print(f"admission_contract_sha256={hashlib.sha256(ADMISSION.read_bytes()).hexdigest()}")
    print("status=PASS_BLOCKERS_CONFIRMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
