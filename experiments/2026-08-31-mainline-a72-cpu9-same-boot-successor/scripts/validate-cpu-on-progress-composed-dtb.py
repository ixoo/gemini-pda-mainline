#!/usr/bin/env python3
"""Validate the CPU9 CPU_ON progress provenance composition."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SOURCE_SHA256 = "770a8e0601427f30b2a90fefc70f5bd1f2dad841660d40a56faae53bd17a1d9d"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-cpuhp-lock-repair-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPUHP lock-repair composed-DT validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("9cadf8291992e47910dfca39618a6e508b896b7bd3db3d873a64b064b6ac7942",
     "9d90a0f8c38f1a5ae090eacef8663fa383ec6e8eaaa46d21665c84e111a1a56d", 1),
    ("9704d2e765740b0511d98986162acda351e6e122d7c056b4c133bd07dcdb1331",
     "a29ae6a68eacc95e07c34469473cc169cd75eb709500b733ddaaaf7bf859684c", 1),
    ("aef34db5009b0b4b6fc69eb62a7f8385b7f975abbd67967243910504bf14f672",
     "0ff1de298acf885c4952d452f8fcef2cb8d18375befe7efa963d09f079612afa", 1),
    ("cpu9-cpuhp-lock-repair-composed-dtb-independent",
     "cpu9-cpu-on-progress-composed-dtb-independent", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU_ON progress DT validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_cpu_on_progress_dtb_validator",
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
    print("validation=cpu9-cpu-on-progress-composed-dtb-independent")
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
