#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently classify one passive-CONSYS boot2 deployment receipt."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import runpy

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PARENT = REPO / "experiments/2026-09-06-mt6797-toprgu-minimal-restart/scripts/deployment_receipt.py"
PARENT_SHA256 = "794c221c42bf9cd127c84f978529b17ac571033a96621179d11c34e2ffaa9a05"
EXPERIMENT = "2026-09-06-mt6797-consys-passive-boot"
PARENT_EXPERIMENT = "2026-09-06-mt6797-toprgu-minimal-restart"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def receipt(raw: str, candidate: str, candidate_manifest: str,
            expected_predecessor: str) -> str:
    require(digest(PARENT) == PARENT_SHA256,
            "reviewed parent deployment receipt source changed")
    own = "experiment=" + EXPERIMENT
    parent = "experiment=" + PARENT_EXPERIMENT
    require(raw.splitlines().count(own) == 1 and parent not in raw.splitlines(),
            "wrong passive deployment experiment")
    translated = raw.replace(own, parent, 1)
    module = runpy.run_path(str(PARENT))
    return module["receipt"](translated, candidate, candidate_manifest,
                             expected_predecessor)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--candidate-manifest-sha256", required=True)
    parser.add_argument("--expected-predecessor-sha256", required=True)
    args = parser.parse_args()
    path = args.receipt
    require(path.is_file() and not path.is_symlink(), "unsafe deployment receipt")
    boot_id = receipt(path.read_text(encoding="ascii"), args.candidate_sha256,
                      args.candidate_manifest_sha256,
                      args.expected_predecessor_sha256)
    print("deployment_receipt=pass")
    print("deployment_boot_id=" + boot_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
