#!/usr/bin/env python3
"""Exercise the exact overwritten-ring analyzer and its fail-closed gates."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
ANALYZER_PATH = ROOT / "scripts" / "analyze-overwritten-ring.py"
CAPTURE_PATH = ROOT / "results" / "runtime-attempt-1-overwritten-ring-20260802.txt"
spec = importlib.util.spec_from_file_location("overwritten_analyzer", ANALYZER_PATH)
assert spec and spec.loader
analyzer = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = analyzer
spec.loader.exec_module(analyzer)


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise AssertionError(f"mutation target count changed for {old!r}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, replacement: str) -> str:
    changed, count = re.subn(pattern, replacement, text, count=1)
    if count != 1:
        raise AssertionError(f"mutation pattern count changed for {pattern!r}")
    return changed


def reject(label: str, text: str) -> None:
    try:
        analyzer.validate(text)
    except analyzer.ValidationError:
        return
    raise AssertionError(f"{label} mutation was accepted")


def main() -> int:
    payload = CAPTURE_PATH.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == analyzer.CAPTURE_SHA256
    text = payload.decode()
    result = analyzer.validate(text)
    assert result["complete_cpu8_up_transactions"] == "182,184,186,188,190"
    assert result["complete_cpu8_down_transactions"] == "181,183,185,187,189,191"
    assert result["cpu9_records"] == 0
    assert result["formal_disposition"] == (
        "inconclusive-overwritten-no-clean-initial-attribution"
    )
    assert result["pulse_permitted"] == "no"

    reject("CPU9 target", text.replace("target=8", "target=9", 1))
    reject("secure instability", text.replace("stable=1", "stable=0", 1))
    reject("DA9214 page restore", text.replace("page_after=0x80", "page_after=0x00", 1))
    reject(
        "mutation readback",
        text.replace("after=0x00010133", "after=0x00010132", 1),
    )
    reject(
        "clock status",
        text.replace("status=0 semaphore=0x000f", "status=-16 semaphore=0x000f", 1),
    )
    reject(
        "up lifecycle return",
        regex_once(
            text,
            r"(event=lifecycle phase=1 target=8[^\n]* result=)0",
            r"\g<1>-1",
        ),
    )
    reject("missing record", "\n".join(text.splitlines()[:-1]) + "\n")
    reject(
        "timestamp order",
        replace_once(text, "seq=3704 ns=144226885457", "seq=3704 ns=144226885999"),
    )
    reject(
        "VSEL distribution",
        regex_once(
            text,
            r"(event=da9214 phase=22 target=8[^\n]* vsel=)0x32",
            r"\g<1>0x3a",
        ),
    )

    print("PASS: exact overwritten-ring result and 9 fail-closed mutations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
