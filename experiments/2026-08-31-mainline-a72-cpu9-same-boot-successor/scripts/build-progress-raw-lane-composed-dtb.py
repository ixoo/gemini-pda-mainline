#!/usr/bin/env python3
"""Source-pin the CPU9 composer to the progress raw-lane repair package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "6b65c0296789f036959e9c71598cc77f49c0661e0040fd7d94e0cfa1e64bec22"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/build-progress-errno-diagnostic-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source progress errno CPU9 composed-DT builder changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("2ea7133059acf95aabfd061d37dd051304effb3e093d7206436af2daa756d274",
     "772e15a26188bcd2ea9cd47b139bc669baa097c8e4861afd41f6a91bb93a76a9", 1),
    ("7cf98f7cb6487b88f0dc85f2816f9f64075066b0f4ab41b862b34bac55520498",
     "9097118ed2783eae2bfe76395d3b7bd44b0596ce5921ed2228974371cbf8d270", 1),
    ("f54e94498b91c8216142d245f2652b7f480534e1fc2c6a05e1477d455790e312",
     "fc0b45188882166184a0db429cb486392fdc607af28dab09eccc212943f5783b", 1),
    ("cpu9-progress-errno-diagnostic-composed-dtb",
     "cpu9-progress-raw-lane-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe progress raw-lane CPU9 DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_progress_raw_lane_dtb_builder",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
