#!/usr/bin/env python3
"""Validate patch 0165 and its bounded P17/P18 evidence."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0165-arm64-publish-dormant-A72-P17-P18-phases.patch"
EXPECTED_COMMIT = "07b50996f"
EXPECTED_SHA256 = "cf793cb0f5cc3b81d7f71eb44163a0fc2a3a1a2e10fc4f0569234897caf24dbb"
EXPECTED_BYTES = 14015


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
    require("Subject: [PATCH] arm64: publish dormant A72 P17 P18 phases" in text,
            "subject changed")
    require("Build, device, and submission remain absent." in text,
            "archive disclaimer missing")
    require("Signed-off-by:" not in text, "synthetic sign-off present")
    diff = added_lines(text)
    required = (
        "mt6797_a72_membership_publish_up",
        "p17_p18_published",
        "MT6797_A72_PHASE_ON_ISSUED",
        "MT6797_A72_PROVIDER_NONE",
        "MT6797_A72_PROVIDER_HELD",
        "provider_identity",
        "test_seed_available_cpu9",
    )
    for token in required:
        require(token in diff, f"missing source token: {token}")
    forbidden = (
        "regulator_", "readl(", "writel(", "psci_ops.cpu_on(",
        "cpu_on(", "cpu_up(", "cpu_down(",
    )
    for token in forbidden:
        require(token not in diff, f"forbidden effect token: {token}")
    require(hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256,
            "patch checksum changed")
    require(len(raw) == EXPECTED_BYTES, "patch size changed")
    subprocess.run(["./scripts/validate-manifest-series"], cwd=ROOT, check=True)
    print("validation=p17-p18-publication")
    print(f"patch_sha256={EXPECTED_SHA256}")
    print(f"patch_bytes={EXPECTED_BYTES}")
    print("p17_cpu8=provider-none")
    print("p18_cpu9=durable-provider-held")
    print("phase=ON_ISSUED")
    print("provider_calls=0")
    print("cpu_on_calls=0")
    print("build=not-run")
    print("device_action=none")
    print("status=PASS")


if __name__ == "__main__":
    main()
