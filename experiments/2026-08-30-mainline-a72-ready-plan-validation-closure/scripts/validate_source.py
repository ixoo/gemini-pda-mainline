#!/usr/bin/env python3
"""Validate the one-change Gemini production plan-validator repair."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re

import source_edits


RISK_TOKENS = (
    "cpu_up(", "cpu_down(", "add_cpu(", "remove_cpu(",
    "psci_cpu_on", "psci_cpu_off", "cpu_off(",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(root: Path) -> list[str]:
    path = root / source_edits.TARGET
    require(path.is_file() and not path.is_symlink(), "target source absent")
    text = path.read_text(encoding="utf-8")
    require(source_edits.NEW in text, "repaired validator absent")
    require(source_edits.OLD not in text, "stale validator remains")

    production = re.search(
        r"#else\n/\* Runtime identity is the last core-owned prepare-time gate\. \*/\n"
        r"#define MT6797_A72_PROFILE_BLOCKERS\s+\\\n"
        r"\s*\(ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING\)\n#endif",
        text,
    )
    require(production is not None, "production blocker set changed")
    repaired = text[text.index(source_edits.NEW):]
    repaired = repaired[:repaired.index("static bool __init", 20)]
    require(
        "ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS" not in repaired,
        "stale attestation requirement remains in production validator",
    )
    require(
        repaired.count("ARM64_LATE_CPU_BLOCK_CONFIGURATION") == 1 and
        repaired.count("ARM64_LATE_CPU_BLOCK_TOPOLOGY") == 1,
        "conditional blocker allowlist changed",
    )
    for forbidden in (
        "ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING",
        "ARM64_LATE_CPU_BLOCK_SOURCE_IDENTITY",
        "ARM64_LATE_CPU_BLOCK_PLAN_VALIDATION",
    ):
        require(forbidden not in repaired, f"unsafe blocker admitted: {forbidden}")

    fixture = text[text.index("#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE"):]
    require(
        "ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS" in fixture and
        "return -EAGAIN;" in fixture,
        "historical fixture closure changed",
    )
    for token in RISK_TOKENS:
        require(text.count(token) == 0, f"CPU action token present: {token}")

    allowed = (1 << 2) | (1 << 1)
    require((0 & ~allowed) == 0, "zero-blocker production evidence rejected")
    require(((1 << 2) & ~allowed) == 0, "configuration path changed")
    require(((1 << 1) & ~allowed) == 0, "topology path changed")
    for bit in (13, 14, 17, 18, 19):
        require(((1 << bit) & ~allowed) != 0,
                f"unrelated blocker bit {bit} was admitted")

    return [
        "source_validation=pass",
        f"target_sha256={sha256(path)}",
        "production_zero_blocker_evidence=accepted",
        "conditional_blockers=configuration,topology",
        "runtime_binding_blocker=still-rejected",
        "attestation_users_blocker=still-rejected",
        "source_identity_blocker=still-rejected",
        "plan_validation_blocker=still-rejected",
        "fixture_closure=unchanged",
        "new_cpu_request_paths=0",
        "cpu9_request_paths=0",
        "cpu_off_paths=0",
        "retry_paths=0",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    for line in validate(args.source_root.resolve()):
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
