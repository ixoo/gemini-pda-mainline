#!/usr/bin/env python3
"""Source-pin and specialize the independent durable candidate validator."""

from __future__ import annotations

import hashlib
from pathlib import Path


SOURCE_SHA256 = "7ecef33af8a4549918fb5d09d79c51a4d084243e1bfa8b07d2fbe68dd32552f8"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = (
    ROOT / "experiments/2026-08-28-mainline-a72-admission-durable-candidate/"
    "scripts/validate-candidate.py"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if digest(SOURCE) != SOURCE_SHA256:
    raise SystemExit("source candidate validator changed")

text = SOURCE.read_text(encoding="utf-8")
replacements = (
    ("eb87d46ae9d58df1ff336751103745d58eed59fe",
     "c147e2ddc1acc93827b59f8e3bb38b9b2f4d3fb2", 1),
    ("a72-admission-durable-candidate", "a72-admission-live-trigger-candidate", 3),
    ("7.1.3-gemini-a72-admission-trace",
     "7.1.3-gemini-a72-admission-live", 1),
    ("linux-7.1.3-gemini-a72-admission-live-trigger-candidate-13dd59d3-a15d3567",
     "linux-7.1.3-gemini-a72-admission-live-trigger-candidate-40a78b77-c2c76c89", 1),
    ("3468c9ccc8c5e965980d283e4e441ab78ca6531a5a44e989ff4d742285f2f3b3",
     "96c86abe4084333bf462f028c217c41eb0342ad080dae3014b439eef0f0cab18", 1),
    ("05c9f1960ac315baf4d20b37f126a7fc700acfc137f5e977650cf916395c3d3b",
     "4b884c0176d4d3e7d96c35f84ce36f0e591b2b7a411fe217f43427824f8377f4", 1),
    ("d59b56cfe259fdc4294a3d51c7dcab66ba4b5270bf4b6ea526763fd4dc534c89",
     "265f610b5200dff9184cd0dcca3c6993b572e167316e149a9856f05723c9eebd", 1),
    ("f9d1242a102c4a0e5544991ab8d9f7bd5263e158f0ec5d07d41368fbbc701585",
     "4d6e3ad347b755907a99b0c7dc0f1cb91fff00f533f21baeab663e77373731bd", 1),
    ("d02a8aa8ac144fb590ac4515a1bce4b67d8286fa1bc857bf5135daa4b59d29c5",
     "c1009fab6642739161d913bdb676fb027d7849dd60c61e1291ec04a8c2541241", 1),
    ("27d550c7c88a49331d325ed1cf8dfba64dd6ed2f8fc3ae83c66f7301ea3a0604",
     "0b6c85b3d6d870c22513f64d3b61d0944a3e9729ad26c0297b4d29414d561f41", 1),
    ("ed6fc5294f5677ed1895bf1157649330c91dd1f6051a6677f2d26972915cd185",
     "633f897ace3d0382dcc88bc064be03107ee3197bb8c7d0b686abab0e9e6b8135", 1),
    ("60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1",
     "4e0f86885a16df2f8b0c1efb4dd2e67394938bad1ef720adabf70ff4635ec0ef", 1),
    ("gemini-a72adm", "gemini-a72live", 1),
    ("gemini-mt6797-a72-admission-trace.boot.img",
     "gemini-mt6797-a72-admission-live.boot.img", 1),
    ("candidate-a72-admission-trace-", "candidate-a72-admission-live-", 1),
    ('        "CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER=y",\n'
     '        "CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER=y",\n',
     '        "CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER=y",\n'
     '        "CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER=y",\n'
     '        "CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER=y",\n', 1),
    ('CONFIG_LOCALVERSION="-gemini-a72-admission-trace"',
     'CONFIG_LOCALVERSION="-gemini-a72-admission-live"', 1),
    ('    marker = (b"GEMINI_A72_ADMISSION_V1 state=terminal ret=%d consumed=1 "\n'
     '              b"requests=%u/0/0 retries=0")\n'
     '    require(image.read_bytes().count(marker) == 1, "Image admission marker changed")',
     '    for marker in (\n'
     '        b"GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 "\n'
     '        b"trigger_executions=0 core_consumed=0 requests=0/0/0 retries=0",\n'
     '        b"GEMINI_A72_ADMISSION_LIVE_V1 state=terminal ret=%d "\n'
     '        b"core_consumed=%d requests=%u/0/0 retries=0",\n'
     '        b"run-a72-admission-20260828-a",\n'
     '    ):\n'
     '        require(image.read_bytes().count(marker) == 1,\n'
     '                f"Image live-trigger marker changed: {marker!r}")', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe live-candidate validator derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)

namespace = {"__file__": str(SCRIPT), "__name__": "live_candidate_validator"}
exec(compile(text, str(SOURCE), "exec"), namespace)
namespace["main"]()
