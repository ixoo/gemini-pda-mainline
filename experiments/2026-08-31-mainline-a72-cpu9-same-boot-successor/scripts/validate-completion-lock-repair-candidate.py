#!/usr/bin/env python3
"""Independently validate the CPU9 completion-path lock-repair container."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "8ad6c03349b47fd7ee1a66f6e43e7bcd9020326f3be155ff40f7f1e25eb1ff22"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/validate-membership-lock-repair-candidate.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source membership lock-repair candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("CPU9 membership-begin lock-repair candidate",
     "CPU9 completion-path lock-repair candidate", 1),
    ("KERNEL_SIZE = 4_891_462", "KERNEL_SIZE = 4_891_540", 1),
    ("44aacf58262a0c6f55462e168743f0ca7d7f92cabe9ca54c237998145a9fbfe6",
     "eba0aa21a2a650a64c0a3ba2b3d416932294eae2d257eb0e9b83b50df2335872", 1),
    ("65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c",
     "370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e", 1),
    ("027a161a4f355a4c27f0a4dd42ba9386c9ace6d89a55596f82305cf6e13364a1",
     "ffb3beb0756f475391a69bb76a07def41906a12c5a4a92ccebd27255b4d7629d", 1),
    ("98565008f0bbe0757c7e680788863720c3d1c9971f59d5d3ccd59b6cf2a216ca",
     "a077171970adfca82959c7d8560aba55042e04faacf2ad06cd828cc535101d8a", 1),
    ("a36dfc2c2cad2a300dd89b3cd4dd8662fe86152c6c2740467d95d149c6a1d279",
     "2ef5aeb10f45d3a74f8cf6a2e8e8c2e2497842624a7150eb7a72f8bf322cb2d9", 1),
    ("7d999ee089db280851329ca80550dbb5a2d39542852f0a3dcc9e31ccefe94597",
     "dc48fdcad45c21684d076f1b9a1be78454c962bd21f6fbddcc448b73a8c0de34", 1),
    ("a8d2bd604faec549ce17c746a4ac2b83c724e2579fdbd46c6c6e49cbe89ec552",
     "29d47ed5d027d0787b583c196aff63e96d5a822b5137395dfc6607afefa33a2c", 1),
    ("19b225ca106c2e480bf604de37d18ceffdb04a37d67df139f508a86117033b76",
     "aae595e7884559d6f298a15c2a7f447c3b1b9c9f97d973ac8bc50169107bd128", 1),
    ("635e5bcf8f111ddf6356fc3091a3273128e97b74",
     "f554c691007e26e2b8fb234320f291f10a33fdf0", 1),
    ("9f 80 b0 56 aa 87 bf 7b cc cb 49 c9 bc 56 6f c5 b6 23 5 b0 c3 bd cc f5 f1 d8 64 5d 6a f 41 0",
     "38 61 52 0 ff 5c b4 b2 cb 41 f4 25 78 e3 e a1 aa ce 2f b0 2c d2 39 f0 e0 b9 fd 66 b7 e1 17 ad", 1),
    ("validation=a72-cpu9-membership-lock-repair-independent",
     "validation=a72-cpu9-completion-lock-repair-independent", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe completion-lock candidate validation derivation: "
            f"expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_completion_lock_repair_candidate_validator",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
