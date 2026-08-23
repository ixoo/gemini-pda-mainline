#!/usr/bin/env python3
"""Source-pin and independently extend the read-free clock candidate validator."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


SOURCE_SHA256 = "41c2ed17f8df3ee56d55da7e64b33888838d9322bdde226c8707e6ef14273695"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[2]
    source = (
        repo_root
        / "experiments/2026-08-23-mainline-clock-backend-first-dmesg-entry"
        / "scripts/test-candidate.py"
    )
    if not source.is_file() or source.is_symlink() or digest(source) != SOURCE_SHA256:
        raise SystemExit("source candidate validator is missing, unsafe, or changed")

    text = source.read_text(encoding="utf-8")
    replacements = (
        ("Independently validate the read-free first-dmesg clock-entry candidate.",
         "Independently validate the read-free clock/CSPM coexistence candidate.", 1),
        ("6_899_712", "6_897_664", 1),
        ("4_822_712", "4_820_612", 1),
        ("d8d98fccee89a77fd5a6bc1da3f55cb3d1366b60", "67e40d761f9e83063742a8e36ffb001c6fa3d38e", 1),
        ("da921x-clock-entry-first-dmesg", "da921x-clock-cspm-coexistence", 1),
        ("7.1.3-gemini-clock-entry-first-dmesg", "7.1.3-gemini-clock-cspm-coexist", 1),
        ("984acb29964a7e111da333d457d1bea48c6952cad2fd95c61b9bedf89d1d0c0e", "35dbdc28c22850d1d72ff15dc0f9f3db091256f8abe024c40ed7eb02316dbc0e", 1),
        ("fd5e77c8194834b5da39f397bea2d4873ad8372e2802c8b6ec640518407b430e", "c68756f4521e2cba57a112189a0bf27e8e086ab8feb82ac87ec4fd74eef86cc2", 1),
        ("0a19f77a527e15997430311358e5ae499271eb03573cf6785b2dffdaf52427a7", "0c6b20c57c0fe64f067b9fc1a216a372e1e6ef3ffb6f51e536196f3816490304", 1),
        ("df7f396405c06aca97b8ebe866bb86cd17459636a83affd8f35220d28c0af099", "15605e77e949d73753ab229d1a7ff695f13da6c494aa0a81e780f922f762d303", 1),
        ("7e3e5c81e128b4a5b565fe47d8186b19b7c663f59b3ed266d95ed02d9a6e30bd", "1f062bce27bc48e50ac96df2bcdf1a4c5eb2be99f7de7b6d46fa8832f1cd8104", 1),
        ("37a41e9dd67235e154f918e4f7db930dbbe8566448c6afd4f1a1de2e49b92f5e", "703ceb7815c4e443f4504000be2c032eb452ff5aa941bfb3da56d3225933e4c2", 1),
        ("7c1d5f69924a8280e36ff111b411c4fbecd32243e8d0da9e9f6f4b333a21e100", "8033f913a4cfd78c2fca9d901c5838285717e9929fc577ea369d7066423c2126", 1),
        ("251e792573bd9961d3f2b90563cff85d851c6502008d97e1ae502fbacda49b83", "dc09377159237c99ef779fbc24824df6c14b8258a9dd237cb7a113e9ed61e6f2", 1),
        ("40b7c663b835bcf4c48f4149f14aa416343e3e322ab78a0aa38448afff9455b4", "ae4010449e72ed4d02643616073e8d74f7cad25adb4afb5db69030d39eb324e7", 1),
        ("e19c8662b9e9f848bde83a9bd64e076b121c0bb6dcc43f9890404888e4b14243", "afdb8215a6035af7a4bb1b963dcc48c4c1cd94cd184cf3570708eb6392db2834", 1),
        ("gemini-mt6797-clock-entry-first-dmesg.boot.img", "gemini-mt6797-clock-cspm-coexistence.boot.img", 1),
        ("-gemini-clock-entry-first-dmesg", "-gemini-clock-cspm-coexist", 1),
        ("gemini-clock-entry-dtb-mutation.", "gemini-clock-cspm-dtb-mutation.", 1),
        ("gemini-clkfdm", "gemini-clkcspm", 1),
        ("mainline-clock-backend-first-dmesg-candidate", "mainline-clock-backend-cspm-coexistence-candidate", 1),
    )
    for old, new, count in replacements:
        actual = text.count(old)
        if actual != count:
            raise SystemExit(
                f"unsafe candidate validator derivation: expected {count}, found {actual}: {old}"
            )
        text = text.replace(old, new)

    old = '''    require(fdtget(dtb, CLOCK_BACKEND, "s", "status") == "okay",
            "clock backend is not enabled")
'''
    new = old + '''    require(fdtget(dtb, CLOCK_BACKEND, "s", "reg-names") == "mcumixed",
            "clock backend register owner changed")
    require(fdtget(dtb, CLOCK_BACKEND, "x", "reg") == "0 1001a000 0 1000",
            "clock backend resource changed")
    require(fdtget(dtb, CLOCK_BACKEND, "x", "access-controllers") == handoff,
            "clock backend handoff supplier changed")
'''
    if text.count(old) != 1:
        raise SystemExit("unsafe candidate validator derivation: clock DT gate changed")
    text = text.replace(old, new)

    old = '''    require(image.count(b"GEMINI_CLOCK_BACKEND_FIRST_DMESG_LIVE_V1") == 3,
            "live marker count changed")
'''
    new = old + '''    require(image.count(b"GEMINI_CLOCK_BACKEND_CSPM_COEXISTENCE_V1") == 1,
            "coexistence marker count changed")
'''
    if text.count(old) != 1:
        raise SystemExit("unsafe candidate validator derivation: Image marker gate changed")
    text = text.replace(old, new)

    old = '''        " T mt6797_dvfsp_clock_backend_read\\n",
'''
    new = old + '''        " T mt6797_dvfsp_cspm_execute\\n",
'''
    if text.count(old) != 1:
        raise SystemExit("unsafe candidate validator derivation: symbol gate changed")
    text = text.replace(old, new)

    old = '''        ["-ts", CLOCK_BACKEND, "status", "disabled"],
'''
    new = old + '''        ["-d", CLOCK_BACKEND, "access-controllers"],
        ["-ts", CLOCK_BACKEND, "reg-names", "mcumixed", "cspm"],
        ["-tx", CLOCK_BACKEND, "reg", "0", "1001a000", "0", "1000",
         "0", "11015000", "0", "1000"],
'''
    if text.count(old) != 1:
        raise SystemExit("unsafe candidate validator derivation: mutation gate changed")
    text = text.replace(old, new)

    old = '''        "boot_candidate=pending-independent-validation",
'''
    new = '''        "runtime_hypothesis=single-handoff-owned-cspm-restores-clock-i2c6-da921x-coexistence",
''' + old
    if text.count(old) != 1:
        raise SystemExit("unsafe candidate validator derivation: provenance gate changed")
    text = text.replace(old, new)

    with tempfile.TemporaryDirectory(prefix="gemini-clock-cspm-validator.") as raw:
        derived = Path(raw) / "test-candidate.py"
        derived.write_text(text, encoding="utf-8")
        completed = subprocess.run([sys.executable, str(derived), *sys.argv[1:]], check=False)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
