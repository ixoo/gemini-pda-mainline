#!/usr/bin/env python3
"""Independently validate the CPU9 CPU_ON progress container."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "1dd161f26c11f25cb16eb72477db74d17363724bce95b1ba88b00aa4485c7176"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-cpuhp-lock-repair-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPUHP lock-repair candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("KERNEL_SIZE = 4_886_820", "KERNEL_SIZE = 4_886_889", 1),
    ("7bcae20e630ecbf673bb95e8184249a885b657c2af25386758e266f1b1d13fd9",
     "b04c46abe2b4d5f8e95245509a1ab8008f93d906807103f74afcdaa8ed98d1df", 1),
    ("CPU9 CPUHP lock-repair candidate",
     "CPU9 CPU_ON progress candidate", 1),
    ("56986d08e0c0b58bd495cb2c815d59939fffbd062b12afb01ea3d7efa6ea863b",
     "88cf13cb1098169347752662aa443a139f10070ffddd054e66145821ec3b129c", 1),
    ("0904c5a293fea22f6993cb25ab8d775ed539d57c8fac7a7a6c50b67e2916f293",
     "d4eca4accded2692418b5972f0a51df79a8be1a0fc52b52f755258da86eb87fe", 1),
    ("2fab89ab992935a0be7b8e8a52b800a5d85ace56d6cf92115dc6930a64fc7d09",
     "f1de48c4e3865f3093fcf0afdb288b03f8eb53214d0b1abb8b9091448523d368", 1),
    ("8c07e2d69a3c08259b2fc7b9e463752898a75ceeca2879a1a65ff16ca5277b1c",
     "37aa0585fb808889fe1a6290ddd63495594086a41d0889d6d7e6e94b7ff9bd6c", 1),
    ("aef34db5009b0b4b6fc69eb62a7f8385b7f975abbd67967243910504bf14f672",
     "0ff1de298acf885c4952d452f8fcef2cb8d18375befe7efa963d09f079612afa", 1),
    ("410a16d3de16ee8d7f4f7bc0e5262f9d77f440e5bf95a108c79ceb40e0055200",
     "e9c4533c236d437a78dd0803392acf098fce7141486b9564296a70e2405a3610", 1),
    ("2769dba806def496822adc6b65ab6634dcc4be53e4394224b96534d6add05429",
     "f84b7b40e0f8dc6bbfef1521103233506b9508307a473ae758067613b6bec436", 1),
    ("45cb7c792a4a80b2ac9680eee5aba7f7ef08ae51",
     "bf0fbcc4d599cc86b67ac313c61228f50cacc9f8", 1),
    ("d4 ca aa 4 8f f4 57 27 76 56 e9 8f b4 f 42 cd 46 e8 a3 ca cd b3 cc f0 2f 4f 2f ee b7 61 d6 fc",
     "39 40 4c f7 29 cb 85 7f 66 bf e0 c7 6e 2b eb 26 6b c4 bd 9b 9f f8 69 ef 44 ee c f2 7d ef b8 28", 1),
    ("validation=a72-cpu9-cpuhp-lock-repair-independent",
     "validation=a72-cpu9-cpu-on-progress-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU_ON progress candidate validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_cpu_on_progress_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
