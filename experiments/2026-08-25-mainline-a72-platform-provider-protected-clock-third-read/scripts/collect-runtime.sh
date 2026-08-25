#!/usr/bin/env bash

# Source-pin the no-reboot provider-ready collector and retarget its exact
# protected-clock candidate identities and decision gate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=20f795c6d389b2d37216dbaa363386145fc6be5e29e2b63dee287afb6b6342a2
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-25-mainline-a72-platform-provider-deferred-bind-repair/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-platform-provider-clock.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("f55bb272de24a62a0e4055624e8eb0ef35bc53432fa130463c867c43c059732e", "1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2", 1),
    ("PROBE_SHA256=f711822bc41d099ed417a7844ca5986cd9b150171674c3e40fbe57f4ecd8e2d7", "PROBE_SHA256=cd5f30e02a2d93b5794deac72ddda57f10680c6b91d137a3d3d2fd439d7a7c4c", 1),
    ("VALIDATOR_SHA256=8b88d26718faf70e98960e784d781e66041c37bbe45cd177bd4648fb5677db91", "VALIDATOR_SHA256=0ca1a9146b35c3c4a30300205b59513c7ac1a2c3fbf5433f6a687ee2260d682f", 1),
    ("a72-platform-provider-ready-attempt-1", "a72-platform-provider-clock-attempt-1", 1),
    (".gemini-a72-platform-provider-ready.XXXXXXXX", ".gemini-a72-platform-provider-clock.XXXXXXXX", 1),
    ("runtime_gate=serviceable-platform-provider-ready-pass", "runtime_gate=serviceable-platform-provider-clock-decision", 1),
    ("exact provider-ready one-shot platform/provider serviceability pass", "exact one-shot platform/provider/protected-clock decision", 1),
    ("unsafe provider-ready collector derivation", "unsafe platform/provider/protected-clock collector derivation", 1),
    (".derived-collect-a72-platform-provider-ready-nested.XXXXXXXX", ".derived-collect-a72-platform-provider-clock-nested.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe platform/provider/clock collector wrapper: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
