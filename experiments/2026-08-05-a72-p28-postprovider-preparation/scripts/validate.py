#!/usr/bin/env python3
"""Validate patch 0169 and bounded P28 evidence."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0169-arm64-model-dormant-A72-postprovider-preparation.patch"
EXPECTED_COMMIT = "afdcd6c9f"
EXPECTED_SHA256 = "2361e3e308bb1cd19079fb5de8699acd544d269bcf93ec986f24a2780d3f7c92"
EXPECTED_BYTES = 17473


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
    require("Subject: [PATCH] arm64: model dormant A72 postprovider preparation" in text,
            "subject changed")
    require("Signed-off-by:" not in text, "synthetic sign-off present")
    diff = added_lines(text)
    for token in ("begin_p28_preparation", "complete_p28_preparation",
                  "P28_STAGE_INFLIGHT", "P28_EFFECT_MASK", "P28_SRAM_LDO_MV",
                  "postprovider_preparation"):
        require(token in diff, f"missing source token: {token}")
    for token in ("regulator_", "readl(", "writel(", "BigiDVFS",
                  "SEC_BIGIDVFS", "psci_ops.cpu_on(", "cpu_on(",
                  "cpu_up(", "cpu_down("):
        require(token not in diff, f"forbidden effect token: {token}")
    require(hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256,
            "patch checksum changed")
    require(len(raw) == EXPECTED_BYTES, "patch size changed")
    subprocess.run(["./scripts/validate-manifest-series"], cwd=ROOT, check=True)
    print("validation=manifest-series-invariant")
    print("validation=p28-postprovider-preparation")
    print(f"patch_sha256={EXPECTED_SHA256}")
    print(f"patch_bytes={EXPECTED_BYTES}")
    print("p28=held-provider-ordered-preparation-proof")
    print("provider_calls=0")
    print("cpu_on_calls=0")
    print("build=not-run")
    print("device_action=none")
    print("status=PASS")


if __name__ == "__main__":
    main()
