#!/usr/bin/env python3
"""Independently validate the CPU9 CPUHP lock-repair container."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "39c9cdffc652837499e080ad2f8fed7ea5f5ad4353e4b45af4e41f8732f2b7e2"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-progress-raw-lane-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source progress raw-lane candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("KERNEL_SIZE = 4_886_748", "KERNEL_SIZE = 4_886_820", 1),
    ("f071de2dabc93e561a9712ba2e85f2b3843d84ee84d4b3483b2cbfc5f2b98702",
     "7bcae20e630ecbf673bb95e8184249a885b657c2af25386758e266f1b1d13fd9", 1),
    ("CPU9 progress raw-lane repair candidate",
     "CPU9 CPUHP lock-repair candidate", 1),
    ("243ddc6e7a6a3e32cc0a86f98c3a3f7c2f33632acb2c2563f3a4e58b48d729a0",
     "56986d08e0c0b58bd495cb2c815d59939fffbd062b12afb01ea3d7efa6ea863b", 1),
    ("1cf367e021351f8a26643d827866786a879a8d6a3e68d8143cfce40bd1db52f7",
     "0904c5a293fea22f6993cb25ab8d775ed539d57c8fac7a7a6c50b67e2916f293", 1),
    ("3a8d9e5ae2a235124de9dba5c3b8091dfefc4d20d5557b595846f5d4b247fa13",
     "2fab89ab992935a0be7b8e8a52b800a5d85ace56d6cf92115dc6930a64fc7d09", 1),
    ("a3079f57f151eb8f75740413d3bdef99ffba397e31a03cc24ed677e598f08872",
     "8c07e2d69a3c08259b2fc7b9e463752898a75ceeca2879a1a65ff16ca5277b1c", 1),
    ("fc0b45188882166184a0db429cb486392fdc607af28dab09eccc212943f5783b",
     "aef34db5009b0b4b6fc69eb62a7f8385b7f975abbd67967243910504bf14f672", 1),
    ("bd7fb619765d11c1fa4bd8bb3622041fdab29c2c8a0be06ef85b1fe28282179a",
     "410a16d3de16ee8d7f4f7bc0e5262f9d77f440e5bf95a108c79ceb40e0055200", 1),
    ("099757f497ee4e94ce5518c1d2c3974a2952df307bf82fb692f24cd949e5f422",
     "2769dba806def496822adc6b65ab6634dcc4be53e4394224b96534d6add05429", 1),
    ("5bf048358148598de3d90b7af47ec01110666c5a",
     "45cb7c792a4a80b2ac9680eee5aba7f7ef08ae51", 1),
    ("83 cb 90 52 d5 c3 3b 1a 73 f be 64 b4 1d 99 ed 35 21 f8 6 f2 61 97 d8 80 e5 c4 db 68 1d 7b 5",
     "d4 ca aa 4 8f f4 57 27 76 56 e9 8f b4 f 42 cd 46 e8 a3 ca cd b3 cc f0 2f 4f 2f ee b7 61 d6 fc", 1),
    ("validation=a72-cpu9-progress-raw-lane-independent",
     "validation=a72-cpu9-cpuhp-lock-repair-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPUHP lock-repair candidate validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_cpuhp_lock_repair_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
