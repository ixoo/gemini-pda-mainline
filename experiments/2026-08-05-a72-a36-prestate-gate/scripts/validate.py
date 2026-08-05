#!/usr/bin/env python3
"""Validate patch 0164 and its bounded A36 evidence."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0164-arm64-validate-frozen-A72-A36-prestates.patch"
EXPECTED_COMMIT = "816311d70"
EXPECTED_SHA256 = "1312a266dec50e38a982609510b20001168448ab8ff160c41f57e99f3752d24d"
EXPECTED_BYTES = 24834


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def added_lines(text: str) -> str:
    return "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def main() -> None:
    raw = PATCH.read_bytes()
    text = raw.decode()
    require(text.startswith(f"From {EXPECTED_COMMIT}"), "prepared commit changed")
    require("Subject: [PATCH] arm64: validate frozen A72 A36 prestates" in text,
            "subject changed")
    require("P17/P18, build, device, and submission remain absent." in text,
            "archive disclaimer missing")
    require("Signed-off-by:" not in text, "synthetic sign-off present")
    diff = added_lines(text)
    required = (
        "struct mt6797_a72_a36_prestate",
        "mt6797_a72_membership_validate_up_prestate",
        "MT6797_A72_A36_SPM_218",
        "MT6797_A72_A36_SPM_290",
        "MT6797_A72_A36_DA921X_PAGE",
        "MT6797_A72_A36_BUCKB_VSEL",
        "__pa_symbol(secondary_entry)",
        "MT6797_A72_PHASE_REJECTED",
        "a72_owner.retired",
        "generation",
        "cookie",
    )
    for token in required:
        require(token in diff, f"missing source token: {token}")
    forbidden = (
        "readl(", "writel(", "readl_relaxed(", "writel_relaxed(",
        "psci_ops.cpu_on(", "cpu_on(",
    )
    for token in forbidden:
        require(token not in diff, f"forbidden effect token: {token}")
    require(hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256,
            "patch checksum changed")
    require(len(raw) == EXPECTED_BYTES, "patch size changed")
    subprocess.run(["./scripts/validate-manifest-series"], cwd=ROOT, check=True)
    print("validation=a36-prestate-gate")
    print(f"patch_sha256={EXPECTED_SHA256}")
    print(f"patch_bytes={EXPECTED_BYTES}")
    print("cpu8_prestate=exact")
    print("cpu9_prestate=exact")
    print("entry_pa=__pa_symbol(secondary_entry)")
    print("mismatch_edge=terminal-rejected-no-rearm")
    print("hardware_access=not-run")
    print("p17_p18=not-run")
    print("cpu_on_calls=0")
    print("build=not-run")
    print("device_action=none")
    print("status=PASS")


if __name__ == "__main__":
    main()
