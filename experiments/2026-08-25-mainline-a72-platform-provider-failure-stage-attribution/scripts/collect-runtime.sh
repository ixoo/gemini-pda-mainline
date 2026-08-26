#!/usr/bin/env bash

# Source-pin the no-reboot third-reader collector and retarget its exact
# failure-stage candidate identities and decision gate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=3ae4fca56691f5f9f07e0e2b122aaf0e8cdbdef80c2c12442e9a6495931d1f01
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-25-mainline-a72-platform-provider-protected-clock-third-read/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-platform-provider-clock-stage.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2", "8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb", 1),
    ("PROBE_SHA256=cd5f30e02a2d93b5794deac72ddda57f10680c6b91d137a3d3d2fd439d7a7c4c", "PROBE_SHA256=37d31b04e83b5ea3863c4640fc34ddedda95e635bc47702ab4aeb251a7b89942", 1),
    ("VALIDATOR_SHA256=0ca1a9146b35c3c4a30300205b59513c7ac1a2c3fbf5433f6a687ee2260d682f", "VALIDATOR_SHA256=29005d94a93518901f9509e81b48c358defb521e617a097a4e013272a0287c7f", 1),
    ("a72-platform-provider-clock-attempt-1", "a72-platform-provider-clock-stage-attempt-1", 1),
    (".gemini-a72-platform-provider-clock.XXXXXXXX", ".gemini-a72-platform-provider-clock-stage.XXXXXXXX", 1),
    ("runtime_gate=serviceable-platform-provider-clock-decision", "runtime_gate=serviceable-platform-provider-clock-stage-decision", 1),
    ("exact one-shot platform/provider/protected-clock decision", "exact one-shot platform/provider/protected-clock failure-stage decision", 1),
    ("unsafe platform/provider/protected-clock collector derivation", "unsafe platform/provider/protected-clock-stage collector derivation", 1),
    (".derived-collect-a72-platform-provider-clock-nested.XXXXXXXX", ".derived-collect-a72-platform-provider-clock-stage-nested.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe platform/provider/clock-stage collector wrapper: expected {count}, "
            f"found {actual}: {old}"
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
