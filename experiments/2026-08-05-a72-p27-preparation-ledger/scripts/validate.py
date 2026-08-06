#!/usr/bin/env python3
"""Validate patch 0166 and its bounded P27 evidence."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0166-arm64-record-dormant-A72-P27-preparation.patch"
EXPECTED_COMMIT = "16d7eb1ec"
EXPECTED_SHA256 = "af0b038c21538fe0df14d23f4e6d41c244a6668e5f7db44d3a9767ed7abb82b7"
EXPECTED_BYTES = 13225


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
    require("Subject: [PATCH] arm64: record dormant A72 P27 preparation" in text,
            "subject changed")
    require("Build, device, and submission remain absent." in text,
            "archive disclaimer missing")
    require("Signed-off-by:" not in text, "synthetic sign-off present")
    diff = added_lines(text)
    for token in ("begin_p27_preparation", "complete_p27_preparation",
                  "MT6797_A72_P27_EFFECT_MASK", "P27_STAGE_INFLIGHT",
                  "P27_STAGE_COMPLETE", "P27_MP2_RESET_RELEASED",
                  "P27_BPLL_ORDER_READ", "P27_PWRAP_ASSERTED"):
        require(token in diff, f"missing source token: {token}")
    for token in ("regulator_", "readl(", "writel(", "psci_ops.cpu_on(",
                  "cpu_on(", "cpu_up(", "cpu_down("):
        require(token not in diff, f"forbidden effect token: {token}")
    require(hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256,
            "patch checksum changed")
    require(len(raw) == EXPECTED_BYTES, "patch size changed")
    subprocess.run(["./scripts/validate-manifest-series"], cwd=ROOT, check=True)
    print("validation=p27-preparation-ledger")
    print(f"patch_sha256={EXPECTED_SHA256}")
    print(f"patch_bytes={EXPECTED_BYTES}")
    print("p27=cpu8-only")
    print("provider_calls=0")
    print("cpu_on_calls=0")
    print("build=not-run")
    print("device_action=none")
    print("status=PASS")


if __name__ == "__main__":
    main()
