#!/usr/bin/env python3
"""Source-pin the CPU9 composer to the CPUHP lock-repair package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "5859240c6deedf086167ddafeb68d1dbfea5323657df4b2ac083aaef63eed730"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/build-progress-raw-lane-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source progress raw-lane composed-DT builder changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("772e15a26188bcd2ea9cd47b139bc669baa097c8e4861afd41f6a91bb93a76a9",
     "9cadf8291992e47910dfca39618a6e508b896b7bd3db3d873a64b064b6ac7942", 1),
    ("9097118ed2783eae2bfe76395d3b7bd44b0596ce5921ed2228974371cbf8d270",
     "9704d2e765740b0511d98986162acda351e6e122d7c056b4c133bd07dcdb1331", 1),
    ("fc0b45188882166184a0db429cb486392fdc607af28dab09eccc212943f5783b",
     "aef34db5009b0b4b6fc69eb62a7f8385b7f975abbd67967243910504bf14f672", 1),
    ("cpu9-progress-raw-lane-composed-dtb",
     "cpu9-cpuhp-lock-repair-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPUHP lock-repair DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_cpuhp_lock_repair_dtb_builder",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
