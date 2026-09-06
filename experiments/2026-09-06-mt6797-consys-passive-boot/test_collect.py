#!/usr/bin/env python3
"""Assert-free passive-record classifier refusal fixtures."""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("consys_collect", HERE / "collect.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("collector unavailable")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
BOOT = "01234567-89ab-cdef-0123-456789abcdef"
RECORD = ("mt6797-consys-passive: state=BOUND generation=1 client=wlan-passive "
          "power=0 reset=0 remap=0 protection=0 firmware=0 radio=0 dma=0")


def check(ok: bool, reason: str) -> None:
    if not ok:
        raise AssertionError(reason)


def capture(record: str = RECORD) -> bytes:
    return (f"release={M.EXPECTED_RELEASE}\narchitecture={M.EXPECTED_ARCH}\n"
            f"boot_id={BOOT}\ntransport=authenticated\nlogger_healthy=yes\n"
            f"log_begin\n{record}\n").encode("ascii")


def replace(raw: bytes, old: str, new: str) -> bytes:
    changed = raw.replace(old.encode("ascii"), new.encode("ascii"), 1)
    check(changed != raw, f"fixture token missing: {old}")
    return changed


def refuse(raw: bytes, text: str) -> None:
    try:
        M.classify(raw)
    except M.CollectionError as exc:
        check(text in str(exc), f"expected {text!r}, got {exc!r}")
    else:
        raise AssertionError(f"accepted mutation: {text}")


def main() -> int:
    check(M.EXPECTED_CANDIDATE ==
          "08fc061475b4bd6bc274bef6cb61c6e0a1cb8d786c5be197b79dba006bebb1c2" and
          M.EXPECTED_INPUT_ID ==
          "f77eb7ee3c8f4024124be09a2e81df489093b5298b821ca9dce04ac2c106d12c",
          "collector replacement candidate/input binding changed")
    result = M.classify(capture())
    check(result["state"] == "BOUND" and result["generation"] == 1 and
          all(value == 0 for value in result["effect_counters"].values()),
          "positive classifier result changed")
    cases = 1
    mutations = [
        ("release=" + M.EXPECTED_RELEASE, "release=wrong", "kernel identity"),
        ("architecture=" + M.EXPECTED_ARCH, "architecture=x86_64", "kernel identity"),
        ("boot_id=" + BOOT, "boot_id=wrong", "boot identity"),
        ("transport=authenticated", "transport=unauthenticated", "transport/logger"),
        ("logger_healthy=yes", "logger_healthy=no", "transport/logger"),
        ("state=BOUND", "state=UNBOUND", "passive BOUND"),
        ("generation=1", "generation=0", "passive BOUND"),
        ("client=wlan-passive", "client=unknown", "passive BOUND"),
    ]
    for counter in ("power", "reset", "remap", "protection", "firmware", "radio", "dma"):
        mutations.append((counter + "=0", counter + "=1", "passive BOUND"))
    for old, new, reason in mutations:
        refuse(replace(capture(), old, new), reason)
        cases += 1
    refuse(capture().replace((RECORD + "\n").encode("ascii"), b""), "schema")
    cases += 1
    refuse(replace(capture(), " dma=0", " dma=0 unknown=0"), "passive BOUND")
    cases += 1
    refuse(replace(capture(), "state=BOUND", "state=BOUND malformed"), "passive BOUND")
    cases += 1
    refuse(capture() + (RECORD + "\n").encode("ascii"), "schema")
    cases += 1
    lines = capture().splitlines()
    lines[0], lines[1] = lines[1], lines[0]
    refuse(b"\n".join(lines) + b"\n", "reordered release")
    cases += 1
    refuse(capture() + b"\xff", "ASCII")
    cases += 1
    refuse(b"x" * (M.MAX_INPUT + 1), "64 KiB")
    cases += 1
    try:
        M.write_result(dict(result), "not-a-deployment")
    except M.CollectionError as exc:
        check("binding is malformed" in str(exc), "deployment refusal changed")
    else:
        raise AssertionError("accepted malformed deployment binding")
    cases += 1
    print(f"passive collector fixtures: PASS cases={cases}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
