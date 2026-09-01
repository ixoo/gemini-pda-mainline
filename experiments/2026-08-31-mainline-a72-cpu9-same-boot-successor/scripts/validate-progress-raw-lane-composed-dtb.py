#!/usr/bin/env python3
"""Validate the CPU9 progress raw-lane repair provenance composition."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


SOURCE_SHA256 = "0e58b67f228ba3c1349cdbf36e1f88d4b239efffa8d3c784b2907d1b935d90b5"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-progress-errno-diagnostic-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source progress errno CPU9 composed-DT validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("2ea7133059acf95aabfd061d37dd051304effb3e093d7206436af2daa756d274",
     "772e15a26188bcd2ea9cd47b139bc669baa097c8e4861afd41f6a91bb93a76a9", 1),
    ("7cf98f7cb6487b88f0dc85f2816f9f64075066b0f4ab41b862b34bac55520498",
     "9097118ed2783eae2bfe76395d3b7bd44b0596ce5921ed2228974371cbf8d270", 1),
    ("f54e94498b91c8216142d245f2652b7f480534e1fc2c6a05e1477d455790e312",
     "fc0b45188882166184a0db429cb486392fdc607af28dab09eccc212943f5783b", 1),
    ("cpu9-progress-errno-diagnostic-composed-dtb-independent",
     "cpu9-progress-raw-lane-composed-dtb-independent", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe progress raw-lane CPU9 DT validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_progress_raw_lane_dtb_validator",
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
    print("validation=cpu9-progress-raw-lane-composed-dtb-independent")
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
