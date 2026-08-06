#!/usr/bin/env python3
"""Validate patch 0167 and its bounded R01/R02 evidence."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0167-arm64-model-dormant-A72-provider-acquire.patch"
EXPECTED_COMMIT = "7201af73e"
EXPECTED_SHA256 = "79cf88744122528cde95304c34f6daa00100b7ed5b6e49ee8cb3df0f30cfe410"
EXPECTED_BYTES = 14403


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def added_lines(text: str) -> str:
    return "\n".join(line[1:] for line in text.splitlines()
                       if line.startswith("+") and not line.startswith("+++"))


def main() -> None:
    raw = PATCH.read_bytes()
    text = raw.decode()
    require(text.startswith(f"From {EXPECTED_COMMIT}"), "prepared commit changed")
    require("Subject: [PATCH] arm64: model dormant A72 provider acquire" in text,
            "subject changed")
    require("Build, device, and submission remain absent." in text,
            "archive disclaimer missing")
    require("Signed-off-by:" not in text, "synthetic sign-off present")
    diff = added_lines(text)
    for token in ("begin_provider_acquire", "confirm_provider_acquire",
                  "PROVIDER_ACQUIRE_INFLIGHT", "PROVIDER_HELD",
                  "provider_acquire_valid", "held_identity",
                  "PROVIDER_ORIGIN_M01", "PROVIDER_ACQUIRE_SETTLE_US"):
        require(token in diff, f"missing source token: {token}")
    for token in ("regulator_", "readl(", "writel(", "psci_ops.cpu_on(",
                  "cpu_on(", "cpu_up(", "cpu_down("):
        require(token not in diff, f"forbidden effect token: {token}")
    require(hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256,
            "patch checksum changed")
    require(len(raw) == EXPECTED_BYTES, "patch size changed")
    subprocess.run(["./scripts/validate-manifest-series"], cwd=ROOT, check=True)
    print("validation=r01-r02-provider-ledger")
    print(f"patch_sha256={EXPECTED_SHA256}")
    print(f"patch_bytes={EXPECTED_BYTES}")
    print("r01=acquire-inflight")
    print("r02=durable-held-proof")
    print("provider_calls=0")
    print("cpu_on_calls=0")
    print("build=not-run")
    print("device_action=none")
    print("status=PASS")


if __name__ == "__main__":
    main()
