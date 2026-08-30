#!/usr/bin/env python3
"""Exercise the boot-bound, exact-one-write CPU8 trigger derivation."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
WRAPPER = SCRIPT_DIR / "remote-trigger.sh"
EXPECTED_BOOT_ID = "11111111-2222-3333-4444-555555555555"
OTHER_BOOT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def run(*args: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(WRAPPER), *args],
        text=True,
        capture_output=True,
        check=False,
        **kwargs,
    )


derived = run("--boot-id", EXPECTED_BOOT_ID)
assert derived.returncode == 0, derived.stderr
text = derived.stdout
assert text.count(f"EXPECTED_BOOT_ID='{EXPECTED_BOOT_ID}'") == 1
assert text.count("failure_stage=0 derive_stage=0") == 1
assert text.count("trigger_commit=yes token_sha256=") == 1
assert text.count("run-a72-admission-20260828-a\\n' >\"$TRIGGER\"") == 1
assert text.count("reason=boot-id-changed") == 1

for args in ((), ("--boot-id", "malformed"), ("--boot-id", EXPECTED_BOOT_ID, "extra")):
    rejected = run(*args)
    assert rejected.returncode == 2, (args, rejected.returncode, rejected.stderr)

with tempfile.TemporaryDirectory(prefix="gemini-trigger-test-") as temporary:
    root = Path(temporary)
    log = root / "side-effects.log"
    busybox = root / "busybox"
    busybox.write_text(
        """#!/bin/sh
set -u
command=$1
shift
case "$command" in
cat)
    if [ "${1-}" = /proc/sys/kernel/random/boot_id ]; then
        printf '%s\\n' "$MOCK_BOOT_ID"
        exit 0
    fi
    printf 'unexpected-cat=%s\\n' "$*" >>"$MOCK_SIDE_EFFECT_LOG"
    exit 99
    ;;
printf)
    exec /usr/bin/printf "$@"
    ;;
*)
    printf 'unexpected-command=%s %s\\n' "$command" "$*" >>"$MOCK_SIDE_EFFECT_LOG"
    exit 99
    ;;
esac
""",
        encoding="utf-8",
    )
    busybox.chmod(0o755)
    instrumented = root / "remote-trigger"
    anchor = "BB=/bin/busybox"
    assert text.count(anchor) == 1
    instrumented.write_text(
        text.replace(anchor, f"BB='{busybox}'"),
        encoding="utf-8",
    )
    instrumented.chmod(0o755)
    environment = os.environ.copy()
    environment.update({
        "MOCK_BOOT_ID": OTHER_BOOT_ID,
        "MOCK_SIDE_EFFECT_LOG": str(log),
    })
    mismatch = subprocess.run(
        [str(instrumented)],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )
    assert mismatch.returncode == 3, (mismatch.returncode, mismatch.stderr)
    assert mismatch.stdout.splitlines() == [
        "__GEMINI_A72_LIVE_TRIGGER_BEGIN__",
        f"boot_id={OTHER_BOOT_ID}",
        "trigger_commit=no",
        "reason=boot-id-changed",
        "__GEMINI_A72_LIVE_TRIGGER_END__",
    ], (mismatch.stdout, mismatch.stderr)
    assert not log.exists(), log.read_text(encoding="utf-8") if log.exists() else ""

print("derived_trigger_write_sites=1")
print("boot_id_mismatch_side_effects=0")
print("malformed_invocations_rejected=3")
print("result=pass")
