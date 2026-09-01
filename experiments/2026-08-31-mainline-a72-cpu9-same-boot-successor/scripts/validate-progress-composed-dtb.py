#!/usr/bin/env python3
"""Independently validate the CPU9 progress provenance composition."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SOURCE_SHA256 = "e4f9007fec90cdf9ccddd094f2d80ed0a9c37e8c365b20b47a3e85ef85b63073"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-config-identity-repair-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source repaired CPU9 composed-DT validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("afb849a4a5dc9011f5a24dad2ae22d2bae1bda1963fa2c7681e86377125c1712",
     "4ce1828020a672e90d0bcb3d14fe79dd16bb71eeaa05044a46daca096feaef83", 1),
    ("228f762c3beacad56cd8e2ec8e595fdf79927d5786c5e54b473c251e93376e5e",
     "63acd089ce6ddbd649e9e06c16013879d6e0554a70c9d4dd2c8e8c27208003a1", 1),
    ("ca7e95162c9e222d47991f6580682354cbb445d994a954950455ca5e6b9c80c3",
     "08ccef4ff3514162d945e12f7ac273a90efa88f71c7cb1fc0417d16b6524b2fd", 1),
    ("cpu9-config-identity-repair-composed-dtb-independent",
     "cpu9-progress-composed-dtb-independent", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe progress CPU9 DT validation derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "cpu9_progress_dtb_validator"}
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
    print("validation=cpu9-progress-composed-dtb-independent")
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
