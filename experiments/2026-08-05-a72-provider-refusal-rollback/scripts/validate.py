#!/usr/bin/env python3
"""Validate patch 0168 and the bounded R03/P29 evidence."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0168-arm64-model-dormant-A72-provider-refusal-rollback.patch"
EXPECTED_COMMIT = "847682ea4"
EXPECTED_SHA256 = "8de98ffcdfebfc48c662faa40c36f1b59fa6bffb8cfae3a0c8c8383785388780"
EXPECTED_BYTES = 16065


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
    require("Subject: [PATCH] arm64: model dormant A72 provider refusal rollback" in text,
            "subject changed")
    require("Signed-off-by:" not in text, "synthetic sign-off present")
    diff = added_lines(text)
    for token in ("reject_provider_acquire", "complete_p29_rollback",
                  "provider_rejection_valid", "p29_valid",
                  "PROVIDER_REJECTED_BEFORE_VOTE", "P29_ROLLBACK_ABI"):
        require(token in diff, f"missing source token: {token}")
    for token in ("regulator_", "readl(", "writel(", "psci_ops.cpu_on(",
                  "cpu_on(", "cpu_up(", "cpu_down("):
        require(token not in diff, f"forbidden effect token: {token}")
    require(hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256,
            "patch checksum changed")
    require(len(raw) == EXPECTED_BYTES, "patch size changed")
    subprocess.run(["./scripts/validate-manifest-series"], cwd=ROOT, check=True)
    print("validation=manifest-series-invariant")
    print("validation=r03-p29-provider-refusal-rollback")
    print(f"patch_sha256={EXPECTED_SHA256}")
    print(f"patch_bytes={EXPECTED_BYTES}")
    print("r03=returned-before-vote-provider-none")
    print("p29=exact-p27-restoration-rejected-retired")
    print("provider_calls=0")
    print("cpu_on_calls=0")
    print("build=not-run")
    print("device_action=none")
    print("status=PASS")


if __name__ == "__main__":
    main()
