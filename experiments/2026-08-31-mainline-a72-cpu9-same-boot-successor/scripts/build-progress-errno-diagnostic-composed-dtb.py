#!/usr/bin/env python3
"""Source-pin the CPU9 composer to the progress errno diagnostic package."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "43549c7b98ca8e75d55a27524bf03bec681b5a49667e00b16c6a78ac8211d798"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/build-mapping-fix-composed-dtb.py"
)
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source mapping-fix CPU9 composed-DT builder changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("b8000eb5311a9a196347462825494a0203c687f6622e7a684388a13009114e98",
     "2ea7133059acf95aabfd061d37dd051304effb3e093d7206436af2daa756d274", 1),
    ("5478d710596b3ece4d222ab9ed8f0cd04bb74ed09cadf86f0e6be6a73d08a089",
     "7cf98f7cb6487b88f0dc85f2816f9f64075066b0f4ab41b862b34bac55520498", 1),
    ("f999758ed62380e339725b78f930660828bfe5a80cd6d33d2719755d57a8510d",
     "f54e94498b91c8216142d245f2652b7f480534e1fc2c6a05e1477d455790e312", 1),
    ("cpu9-mapping-fix-composed-dtb",
     "cpu9-progress-errno-diagnostic-composed-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe progress errno CPU9 DT derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {
    "__file__": str(SCRIPT),
    "__name__": "cpu9_progress_errno_diagnostic_dtb_builder",
}
exec(compile(text, str(SOURCE), "exec"), namespace)
raise SystemExit(namespace["main"]())
