#!/usr/bin/env bash

# Source-pin the no-reboot passed-platform collector and specialize its exact
# identities and read-free clock-backend isolation acceptance gate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=239730f184500dab38f51e0d9913638a825235c537f485ce9269b48004f83291
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-24-mainline-a72-platform-state-stage27-control/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-clock-stage27.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("662e86846e783cf29b13c388f9e88217fe7bd32933eef4f32df86e44def0b16b", "4c5276ecf3fe60d7df55fd1fe44235432fcd928d2174704e5928bae7d84056e4", 1),
    ("PROBE_SHA256=84cd91e6b842b86fbd8b62eb042be0e1873a9738625743aaf3896d5d5dda9d77", "PROBE_SHA256=9cd0a08c73f881595cfd788db5e391a5d3d9c31675f17e1c09441ff8fc80260b", 1),
    ("VALIDATOR_SHA256=c1ab2bae4f8b2f4f2d462707fb4191d34cb129946c41447d2ac653da57a6073d", "VALIDATOR_SHA256=e08a7c12f6e237e9e67eb0ce2a077aecde9c2cae0da35510c3cc62a418be4c8a", 1),
    ("a72-platform-state-stage27-attempt-1", "a72-clock-backend-stage27-attempt-1", 1),
    (".gemini-a72-platform-stage27.XXXXXXXX", ".gemini-a72-clock-stage27.XXXXXXXX", 1),
    ("runtime_gate=serviceable-platform-state-stage27-pass", "runtime_gate=serviceable-clock-backend-stage27-pass", 1),
    ("exact Stage-27 minimum platform-state pass", "exact Stage-27 read-free clock-backend serviceability pass", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe clock-backend collector derivation: expected {count}, found {actual}: {old}")
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
