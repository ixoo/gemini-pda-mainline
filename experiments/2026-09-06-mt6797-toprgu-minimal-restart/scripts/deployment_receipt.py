#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independently classify one TOPRGU boot2 deployment receipt."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import runpy

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
BASELINE = REPO / "experiments/2026-09-05-owner-away-experiment-preparation/baseline/scripts/deployment_receipt.py"
BASELINE_SHA256 = "a2dc643ddedf5c9c93ede43598208cafd17242fccbb45db6ddaf078f30ae6f23"
V4 = REPO / "experiments/2026-09-04-mt6797-thermal-snapshot/scripts/v4_deployment_receipt.py"
V4_SHA256 = "2ef4fc09a11207e2f43cce9c1d328905b636d618c72f3ab76325ef766201c5b7"
EXPERIMENT = "2026-09-06-mt6797-toprgu-minimal-restart"
SHA = re.compile(r"[0-9a-f]{64}")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def values(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in raw.splitlines():
        key, separator, value = line.partition("=")
        require(bool(separator) and bool(key) and key not in result and value == value.strip(),
                "malformed or duplicate deployment receipt field")
        result[key] = value
    return result


def receipt(raw: str, candidate: str, candidate_manifest: str,
            expected_predecessor: str) -> str:
    require(all(SHA.fullmatch(item) is not None for item in
                (candidate, candidate_manifest, expected_predecessor)),
            "deployment receipt binding format")
    require(digest(BASELINE) == BASELINE_SHA256 and digest(V4) == V4_SHA256,
            "reviewed deployment receipt source changed")
    fields = values(raw)
    require(fields.get("experiment") == EXPERIMENT,
            "wrong TOPRGU deployment experiment")
    require(fields.get("candidate_manifest_sha256") == candidate_manifest,
            "candidate manifest receipt binding changed")
    require(fields.get("predecessor_sha256") == expected_predecessor or
            fields.get("result") == "skipped-already-matching",
            "deployment predecessor differs from admitted checksum")
    translated = []
    for line in raw.splitlines():
        if line == "experiment=" + EXPERIMENT:
            translated.append("experiment=2026-09-04-mt6797-thermal-snapshot")
        elif not line.startswith("candidate_manifest_sha256="):
            translated.append(line)
    module = runpy.run_path(str(V4))
    return module["receipt"]("\n".join(translated), candidate)


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
