#!/usr/bin/env python3
"""Validate the CPU9 progress errno diagnostic provenance composition."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SOURCE_SHA256 = "1791ef291b4ee32f34f12e1ad77ecf955ee584346318e5953630d38de94d90c3"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-mapping-fix-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source mapping-fix CPU9 composed-DT validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("b8000eb5311a9a196347462825494a0203c687f6622e7a684388a13009114e98",
     "2ea7133059acf95aabfd061d37dd051304effb3e093d7206436af2daa756d274", 1),
    ("5478d710596b3ece4d222ab9ed8f0cd04bb74ed09cadf86f0e6be6a73d08a089",
     "7cf98f7cb6487b88f0dc85f2816f9f64075066b0f4ab41b862b34bac55520498", 1),
    ("f999758ed62380e339725b78f930660828bfe5a80cd6d33d2719755d57a8510d",
     "f54e94498b91c8216142d245f2652b7f480534e1fc2c6a05e1477d455790e312", 1),
    ("cpu9-mapping-fix-composed-dtb-independent",
     "cpu9-progress-errno-diagnostic-composed-dtb-independent", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe progress errno CPU9 DT validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_progress_errno_diagnostic_dtb_validator",
}
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
    print("validation=cpu9-progress-errno-diagnostic-composed-dtb-independent")
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
