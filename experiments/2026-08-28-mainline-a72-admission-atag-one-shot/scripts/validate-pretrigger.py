#!/usr/bin/env python3
"""Source-pin the armed-frame validator and bind it to the ATAG live boot."""

from __future__ import annotations
import hashlib
from pathlib import Path

SOURCE_SHA256 = "3f4cb51ad1405df620f447b6210aac795a0664171711f8ca38ddaf05e9113531"
SCRIPT = Path(__file__).resolve(); ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-28-mainline-a72-admission-serviceable-one-shot/scripts/validate-pretrigger.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")
text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02", "fd611a4ca87fd1645e2fa75b3927d56e9e7eac89f3d84712e5555a3aab8f4cf0", 1),
    ("21bb6547-a5cd-494c-8900-d92884c0c6a5", "515b4618-5bf7-4125-9c08-38db55d6cc27", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe ATAG pre-trigger derivation: expected {count}, found {actual}")
    text = text.replace(old, new)
namespace = {"__file__": str(SCRIPT), "__name__": __name__}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({key: value for key, value in namespace.items() if key != "__builtins__"})
