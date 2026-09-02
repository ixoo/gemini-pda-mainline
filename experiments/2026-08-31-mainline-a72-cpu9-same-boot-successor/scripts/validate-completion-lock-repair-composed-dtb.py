#!/usr/bin/env python3
"""Validate the CPU9 completion-path lock-repair provenance composition."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SOURCE_SHA256 = "9aa6257dc8a6b2558458c8bf34a4df811d012ea4a75d4327df57d7be75dc023a"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-membership-lock-repair-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source membership lock-repair composed-DT validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("18660eadcbd3477f9710162c1ddf6820d53e613f95ca2255d44948e4ec5eb718",
     "9212c8b03df973362307902573980ec27071f89ef3728ed44064f6319a9edf37", 1),
    ("f07f76e6a5ec29fa6807299271c0e2028ad6becb6628b11dec39215185a771da",
     "5fe8c059961f3d2bfc6e8461a9b8148e610821701f9cfac81eff2425c0ee39f6", 1),
    ("a36dfc2c2cad2a300dd89b3cd4dd8662fe86152c6c2740467d95d149c6a1d279",
     "2ef5aeb10f45d3a74f8cf6a2e8e8c2e2497842624a7150eb7a72f8bf322cb2d9", 1),
    ("cpu9-membership-lock-repair-composed-dtb-independent",
     "cpu9-completion-lock-repair-composed-dtb-independent", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe completion-lock DT validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_completion_lock_repair_dtb_validator",
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
    print("validation=cpu9-completion-lock-repair-composed-dtb-independent")
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
