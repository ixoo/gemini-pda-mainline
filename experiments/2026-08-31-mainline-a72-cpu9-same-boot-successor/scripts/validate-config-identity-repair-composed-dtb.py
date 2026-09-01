#!/usr/bin/env python3
"""Independently validate the repaired CPU9 package provenance composition."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SOURCE_SHA256 = "386cf667e4947809ea5e34b778c0fff1d18a8f5e37eaa0fabcd197d9bc3913ea"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU9 composed-DT validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("347274878f91d872cef6e20892b79303bb035e1b56fea7743c86ce06a6ba6475",
     "afb849a4a5dc9011f5a24dad2ae22d2bae1bda1963fa2c7681e86377125c1712", 1),
    ("8bb4eeb23948610f0de04032e6610d9ecfb74a15eb5f8d6c5fa4d2718188cadb",
     "228f762c3beacad56cd8e2ec8e595fdf79927d5786c5e54b473c251e93376e5e", 1),
    ("603335e66ddff09b674ac26320db3cc88e0e55b066dd16310584187efcefae3b",
     "ca7e95162c9e222d47991f6580682354cbb445d994a954950455ca5e6b9c80c3", 1),
    ("cpu9-controller-composed-dtb-independent",
     "cpu9-config-identity-repair-composed-dtb-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe repaired CPU9 DT validation derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "cpu9_repair_dtb_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
validate = namespace["validate"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serviceability-dtb", type=Path, required=True)
    parser.add_argument("--package-dtb", type=Path, required=True)
    parser.add_argument("--record-json", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    validate(args.serviceability_dtb, args.package_dtb, args.record_json,
             args.candidate)
    print("validation=cpu9-config-identity-repair-composed-dtb-independent")
    print("dt_delta=one-exact-package-provenance-leaf")
    print("serviceability_nodes=preserved")
    print("controller_nodes=1")
    print("binder_nodes=1")
    print("candidate_cpu8_request_paths=1")
    print("candidate_cpu9_request_paths=1")
    print("cpu8_requests_during_validation=0")
    print("cpu9_requests_during_validation=0")
    print("boot_candidate=pending-container-validation")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
