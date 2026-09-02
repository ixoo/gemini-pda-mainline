#!/usr/bin/env python3
"""Independently validate the CPU9 membership-begin lock-repair container."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "f1d8c73c954a64d33f405107d93e8f8e45c4172a0db92b2d71a21afcb80d54aa"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-progress-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU9 progress candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("CPU9 progress-ledger diagnostic candidate",
     "CPU9 membership-begin lock-repair candidate", 1),
    ("RAW_SIZE = 6_965_248", "RAW_SIZE = 6_969_344", 1),
    ("KERNEL_SIZE = 4_886_744", "KERNEL_SIZE = 4_891_462", 1),
    ("85d3b591cdee4635cf0e5b889011459a4cb7e48f4ddd3ac2df0c20720e1c8833",
     "44aacf58262a0c6f55462e168743f0ca7d7f92cabe9ca54c237998145a9fbfe6", 1),
    ("ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72",
     "65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c", 1),
    ("c4e84c90a9843b8d5a7beaf8ce6c7874d1d8e972f14fa91a4e837800ecd0b5f6",
     "027a161a4f355a4c27f0a4dd42ba9386c9ace6d89a55596f82305cf6e13364a1", 1),
    ("4c4f43328c6c824045d118510183b1d7f2fdacd92ddeaf4f6b75a59ad76cf9b8",
     "98565008f0bbe0757c7e680788863720c3d1c9971f59d5d3ccd59b6cf2a216ca", 1),
    ("08ccef4ff3514162d945e12f7ac273a90efa88f71c7cb1fc0417d16b6524b2fd",
     "a36dfc2c2cad2a300dd89b3cd4dd8662fe86152c6c2740467d95d149c6a1d279", 1),
    ("a657dd5c033d18b3d7638875e6603c6c9486fd9b13c2f9d9f4a9c60c82875534",
     "7d999ee089db280851329ca80550dbb5a2d39542852f0a3dcc9e31ccefe94597", 1),
    ("e262795a456a933a16b0658edb699bb3ea444e04bfa842488cf04d794f545a28",
     "a8d2bd604faec549ce17c746a4ac2b83c724e2579fdbd46c6c6e49cbe89ec552", 1),
    ("e398c2b9156c31f02cb126be40204608b17f9df8a44a0f2268e05545d40448e2",
     "19b225ca106c2e480bf604de37d18ceffdb04a37d67df139f508a86117033b76", 1),
    ("630350185c9126f2c96be7295216c5ff1ee08c83",
     "635e5bcf8f111ddf6356fc3091a3273128e97b74", 1),
    ("ed 3a 4b f0 85 10 bd d5 c1 7 c1 10 18 3b 1c e9 85 df c5 59 4c 8a fa e5 4b df fe 0 6f b5 66 6",
     "9f 80 b0 56 aa 87 bf 7b cc cb 49 c9 bc 56 6f c5 b6 23 5 b0 c3 bd cc f5 f1 d8 64 5d 6a f 41 0", 1),
    ("validation=a72-cpu9-progress-independent",
     "validation=a72-cpu9-membership-lock-repair-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe membership-lock candidate validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_membership_lock_repair_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
