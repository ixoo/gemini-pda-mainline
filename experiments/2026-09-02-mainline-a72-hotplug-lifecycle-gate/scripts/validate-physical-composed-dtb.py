#!/usr/bin/env python3
"""Validate the CPU9 physical-hotplug provenance composition."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SOURCE_SHA256 = "747b5f56659313eab89c43df924cd60ea95026e4b5e3e4ef025193d6c9473a9c"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-completion-lock-repair-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source completion-lock composed-DT validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("9212c8b03df973362307902573980ec27071f89ef3728ed44064f6319a9edf37",
     "24f2caac69f196dc316e627224f67a1fa5f0c26d4ef68e6f84461ba5492d7096", 1),
    ("5fe8c059961f3d2bfc6e8461a9b8148e610821701f9cfac81eff2425c0ee39f6",
     "9d7c84593e44683f943f1f64e2d811da825f32dfc56f4169b97843897cfc6a53", 1),
    ("2ef5aeb10f45d3a74f8cf6a2e8e8c2e2497842624a7150eb7a72f8bf322cb2d9",
     "99415ca8c13fd6f30b34b805214ebbbbc1230951fae0c943c7cbaf6c1603439d", 1),
    ("cpu9-completion-lock-repair-composed-dtb-independent",
     "cpu9-physical-hotplug-composed-dtb-independent", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe physical-hotplug DT validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_physical_hotplug_dtb_validator",
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
    print("validation=cpu9-physical-hotplug-composed-dtb-independent")
    print("dt_delta=one-exact-package-provenance-leaf")
    print("serviceability_nodes=preserved")
    print("controller_nodes=1")
    print("binder_nodes=1")
    print("candidate_cpu8_request_paths=1")
    print("candidate_cpu9_request_paths=1")
    print("physical_cpu_requests_during_validation=0")
    print("boot_candidate=pending-container-validation")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
