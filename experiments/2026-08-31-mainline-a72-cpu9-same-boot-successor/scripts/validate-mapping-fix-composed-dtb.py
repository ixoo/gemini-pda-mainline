#!/usr/bin/env python3
"""Independently validate the CPU9 mapping-fix provenance composition."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SOURCE_SHA256 = "faa9e0f67dc5fc2e0370d7a9b1e3f619a7b88a5a79cbfa0bff354be06ae4e8b3"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-progress-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source progress CPU9 composed-DT validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("4ce1828020a672e90d0bcb3d14fe79dd16bb71eeaa05044a46daca096feaef83",
     "b8000eb5311a9a196347462825494a0203c687f6622e7a684388a13009114e98", 1),
    ("63acd089ce6ddbd649e9e06c16013879d6e0554a70c9d4dd2c8e8c27208003a1",
     "5478d710596b3ece4d222ab9ed8f0cd04bb74ed09cadf86f0e6be6a73d08a089", 1),
    ("08ccef4ff3514162d945e12f7ac273a90efa88f71c7cb1fc0417d16b6524b2fd",
     "f999758ed62380e339725b78f930660828bfe5a80cd6d33d2719755d57a8510d", 1),
    ("cpu9-progress-composed-dtb-independent",
     "cpu9-mapping-fix-composed-dtb-independent", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe mapping-fix CPU9 DT validation derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "cpu9_mapping_fix_dtb_validator"}
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
    print("validation=cpu9-mapping-fix-composed-dtb-independent")
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
