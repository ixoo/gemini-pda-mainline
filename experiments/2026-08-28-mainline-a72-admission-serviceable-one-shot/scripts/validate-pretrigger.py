#!/usr/bin/env python3
"""Source-pin the armed-frame validator and bind it to the live boot."""

from __future__ import annotations

import hashlib
from pathlib import Path

SOURCE_SHA256 = "906a404932f64ec3795f666b9adda0167f49777f24c52178c20ca0aaea953715"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / "experiments/2026-08-28-mainline-a72-admission-live-trigger/scripts/validate-pretrigger.py"
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source pre-trigger validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    (
        "4e0f86885a16df2f8b0c1efb4dd2e67394938bad1ef720adabf70ff4635ec0ef",
        "f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02",
        1,
    ),
    (
        '        raise Classification("boot-id-malformed")\n'
        '    if re.fullmatch(r"\\d+(?:\\.\\d+)?", observed.get("uptime_seconds", "")) is None:',
        '        raise Classification("boot-id-malformed")\n'
        '    if boot_id != "21bb6547-a5cd-494c-8900-d92884c0c6a5":\n'
        '        raise Classification("boot-id-changed")\n'
        '    if re.fullmatch(r"\\d+(?:\\.\\d+)?", observed.get("uptime_seconds", "")) is None:',
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe pre-trigger derivation: expected {count}, found {actual}")
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": __name__}
exec(compile(text, str(SOURCE), "exec"), namespace)
globals().update({key: value for key, value in namespace.items() if key != "__builtins__"})
