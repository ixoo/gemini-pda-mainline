#!/usr/bin/env python3
"""Unit-test the exact retained-header parser KTAP classifier."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("classify-kunit.py")
SPEC = importlib.util.spec_from_file_location("classify_kunit", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("cannot load classifier")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def fixture() -> str:
    cases = "\n".join(
        f"[    0.1] ok {index} {case}"
        for index, case in enumerate(MODULE.EXPECTED_CASES, start=1)
    )
    return f"""Linux version 7.1.3-gemini-mtk-ram-console-parser-kunit (test)
[    0.1] KTAP version 1
[    0.1] 1..1
[    0.1]     # Subtest: {MODULE.SUITE}
[    0.1]     KTAP version 1
[    0.1]     1..8
{cases}
[    0.1] # {MODULE.SUITE}: pass:8 fail:0 skip:0 total:8
[    0.1] # Totals: pass:8 fail:0 skip:0 total:8
[    0.1] ok 1 {MODULE.SUITE}
[    0.2] Kernel panic - not syncing: VFS: Unable to mount root fs on unknown-block(0,0)
[    0.3] ---[ end Kernel panic - not syncing: VFS: Unable to mount root fs ]---
"""


def require_reject(raw: str, label: str) -> None:
    try:
        MODULE.classify_runtime(
            raw, "7.1.3-gemini-mtk-ram-console-parser-kunit", 124)
    except MODULE.ClassificationError:
        return
    raise SystemExit(f"classifier accepted {label}")


def main() -> None:
    raw = fixture()
    MODULE.classify_runtime(
        raw, "7.1.3-gemini-mtk-ram-console-parser-kunit", 124)
    require_reject(raw.replace("ok 3", "not ok 3", 1), "failed case")
    require_reject(raw.replace("1..8", "1..9", 1), "changed plan")
    require_reject(raw.replace(MODULE.EXPECTED_CASES[0], "foreign_test", 1),
                   "foreign case")
    require_reject(raw.replace("Kernel panic - not syncing", "panic removed", 1),
                   "missing terminal panic")
    print("classifier_tests=pass")
    print("accepted_fixture=1")
    print("rejected_mutations=4")


if __name__ == "__main__":
    main()
