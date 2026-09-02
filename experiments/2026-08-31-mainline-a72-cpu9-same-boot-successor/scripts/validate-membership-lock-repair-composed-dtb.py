#!/usr/bin/env python3
"""Validate the CPU9 membership-begin lock-repair provenance composition."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SOURCE_SHA256 = "141bfc8aa11c353a6efd505d4b13f50245749e34dcd495e885ce0da48cfeee35"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-cpu-on-progress-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU_ON progress composed-DT validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("9d90a0f8c38f1a5ae090eacef8663fa383ec6e8eaaa46d21665c84e111a1a56d",
     "18660eadcbd3477f9710162c1ddf6820d53e613f95ca2255d44948e4ec5eb718", 1),
    ("a29ae6a68eacc95e07c34469473cc169cd75eb709500b733ddaaaf7bf859684c",
     "f07f76e6a5ec29fa6807299271c0e2028ad6becb6628b11dec39215185a771da", 1),
    ("0ff1de298acf885c4952d452f8fcef2cb8d18375befe7efa963d09f079612afa",
     "a36dfc2c2cad2a300dd89b3cd4dd8662fe86152c6c2740467d95d149c6a1d279", 1),
    ("cpu9-cpu-on-progress-composed-dtb-independent",
     "cpu9-membership-lock-repair-composed-dtb-independent", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe membership-lock DT validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_membership_lock_repair_dtb_validator",
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
    print("validation=cpu9-membership-lock-repair-composed-dtb-independent")
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
