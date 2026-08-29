#!/usr/bin/env python3
"""Exercise the changed-cycle pmsg parser and its rejection boundaries."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
import tempfile
from pathlib import Path
from types import ModuleType


SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate_pmsg.py"
PATCH = SCRIPT_DIR.parent / "patches/0001-diagnostic-add-same-version-pmsg-witness.patch"
PATCH_SHA256 = "cf102ea22af912a9a4755039c6acc109be36be859d1e3ac826d884d8a095fd59"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_validator() -> ModuleType:
    require(
        PATCH.is_file() and not PATCH.is_symlink() and digest(PATCH) == PATCH_SHA256,
        "pinned pmsg source patch changed",
    )
    spec = importlib.util.spec_from_file_location("a72_pmsg_validator", VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load pmsg validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    patch = PATCH.read_bytes()
    for record in module.KNOWN_RECORDS:
        require(record.rstrip(b"\n") in patch, "validator record is absent from source")
    return module


VALIDATOR_MODULE = load_validator()


def write_cycle(root: Path, *, changed: bool = True) -> None:
    initial = "1" * 64
    final = "2" * 64 if changed else initial
    (root / "cycle.txt").write_text(
        "wait_for_cycle=yes\n"
        "cycle_started_utc=2026-08-29T01:00:00Z\n"
        "disconnect_observed_utc=2026-08-29T01:01:00Z\n"
        "reconnect_observed_utc=2026-08-29T01:02:00Z\n"
        f"initial_boot_id_sha256={initial}\n"
        f"final_boot_id_sha256={final}\n"
        "boot_id_changed=yes\n"
        "capture_kernel=3.18.41+\n"
        "capture_arch=aarch64\n"
        "expected_kernel=3.18.41+\n"
        f"archive_pre_boot_id_sha256={final}\n"
        f"archive_post_boot_id_sha256={final}\n"
    )


def fixture(root: Path, raw: bytes | None, *, changed: bool = True) -> Path:
    root.mkdir()
    write_cycle(root, changed=changed)
    pstore = root / "pstore"
    pstore.mkdir()
    if raw is not None:
        path = pstore / "pmsg-ramoops-0"
        path.write_bytes(raw)
        path.chmod(0o600)
    return root


def validate_successes(temporary: Path) -> None:
    valid = (
        ("absent", None, "no-pmsg-witness"),
        (
            "entry",
            b"\x00android-prefix\xff" + VALIDATOR_MODULE.ENTRY + b"binary-tail\x00",
            "before-pre-scheduler",
        ),
        (
            "pre-scheduler",
            VALIDATOR_MODULE.ENTRY + b"noise\x00" + VALIDATOR_MODULE.PRE_SCHEDULER,
            "before-pre-capsule",
        ),
        (
            "terminal-pass",
            b"android\x00"
            + VALIDATOR_MODULE.ENTRY
            + VALIDATOR_MODULE.PRE_SCHEDULER
            + VALIDATOR_MODULE.TERMINAL_PASS
            + b"\xfftail",
            "pre-capsule-pass-await-capsules",
        ),
        (
            "terminal-fault",
            VALIDATOR_MODULE.ENTRY
            + VALIDATOR_MODULE.PRE_SCHEDULER
            + VALIDATOR_MODULE.TERMINAL_FAULT,
            "scheduler-capsule-fault",
        ),
        (
            "wrapped-entry-pre-scheduler",
            b"old-android-tail\x00" + VALIDATOR_MODULE.PRE_SCHEDULER,
            "before-pre-capsule",
        ),
        (
            "wrapped-entry-terminal-pass",
            VALIDATOR_MODULE.PRE_SCHEDULER + VALIDATOR_MODULE.TERMINAL_PASS,
            "pre-capsule-pass-await-capsules",
        ),
        (
            "wrapped-entry-terminal-fault",
            VALIDATOR_MODULE.PRE_SCHEDULER + VALIDATOR_MODULE.TERMINAL_FAULT,
            "scheduler-capsule-fault",
        ),
    )
    for name, raw, expected in valid:
        capture = fixture(temporary / name, raw)
        result = VALIDATOR_MODULE.classify_capture(capture)
        require(result["classification"] == expected, f"wrong result for {name}")
        require(result["boot_id_changed"] == "yes", f"cycle lost for {name}")


def validate_rejections(temporary: Path) -> None:
    entry = VALIDATOR_MODULE.ENTRY
    pre = VALIDATOR_MODULE.PRE_SCHEDULER
    passed = VALIDATOR_MODULE.TERMINAL_PASS
    fault = VALIDATOR_MODULE.TERMINAL_FAULT
    invalid = (
        ("duplicate-entry", entry + entry, "duplicate, mixed, or out-of-order"),
        ("both-terminals", entry + pre + passed + fault, "duplicate, mixed, or out-of-order"),
        ("terminal-without-pre", entry + passed, "duplicate, mixed, or out-of-order"),
        ("wrong-order", pre + entry, "duplicate, mixed, or out-of-order"),
        ("duplicate-pre", entry + pre + pre, "duplicate, mixed, or out-of-order"),
        ("terminal-only", passed, "duplicate, mixed, or out-of-order"),
        (
            "malformed-version",
            b"gemini-a72-pmsg-v2 stage=entry parent=register-capsule\n",
            "malformed pmsg witness-family record",
        ),
        (
            "malformed-stage",
            b"gemini-a72-pmsg-v1 stage=unknown\n",
            "malformed pmsg witness-family record",
        ),
        (
            "unterminated",
            b"gemini-a72-pmsg-v1 stage=entry parent=register-capsule",
            "unterminated pmsg witness-family record",
        ),
    )
    for name, raw, expected in invalid:
        capture = fixture(temporary / name, raw)
        try:
            VALIDATOR_MODULE.classify_capture(capture)
        except VALIDATOR_MODULE.EvidenceError as error:
            require(expected in str(error), f"wrong rejection for {name}: {error}")
        else:
            raise AssertionError(f"invalid capture accepted: {name}")

    unchanged = fixture(temporary / "unchanged-cycle", entry, changed=False)
    try:
        VALIDATOR_MODULE.classify_capture(unchanged)
    except VALIDATOR_MODULE.EvidenceError as error:
        require("hashes did not change" in str(error), "unchanged cycle rejected wrongly")
    else:
        raise AssertionError("unchanged cycle accepted")

    inventory = fixture(temporary / "unexpected-inventory", None)
    extra = inventory / "pstore/pmsg-ramoops-1"
    extra.write_bytes(entry)
    extra.chmod(0o600)
    try:
        VALIDATOR_MODULE.classify_capture(inventory)
    except VALIDATOR_MODULE.EvidenceError as error:
        require("inventory" in str(error), "inventory rejected wrongly")
    else:
        raise AssertionError("unexpected pmsg inventory accepted")

    unsafe = fixture(temporary / "symlink", None)
    outside = temporary / "outside"
    outside.write_bytes(entry)
    outside.chmod(0o600)
    os.symlink(outside, unsafe / "pstore/pmsg-ramoops-0")
    try:
        VALIDATOR_MODULE.classify_capture(unsafe)
    except VALIDATOR_MODULE.EvidenceError as error:
        require("unsafe pmsg file" in str(error), "symlink rejected wrongly")
    else:
        raise AssertionError("symlink pmsg accepted")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="a72-pmsg-runtime-") as name:
        temporary = Path(name)
        validate_successes(temporary)
        validate_rejections(temporary)
    print("validation=a72-pmsg-runtime-tools")
    print("valid_classifications=8")
    print("invalid_captures=12-rejected")
    print("binary_surroundings=accepted")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
