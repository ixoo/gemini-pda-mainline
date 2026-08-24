#!/usr/bin/env bash

# Source-pin the no-reboot platform-state collector and specialize its exact
# identities and Stage-27 serviceability-state acceptance gate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=e3ab9abd24e536513b0eaa12f1065d133183574757d2f5ad5b17e9b5f03daad6
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-24-mainline-a72-platform-state-only/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-platform-stage27.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("012f7eac6884e65baab075ef286929f610a63f2ea065eba45865bd046492a23f", "662e86846e783cf29b13c388f9e88217fe7bd32933eef4f32df86e44def0b16b", 1),
    ("PROBE_SHA256=c1d206cbdea16ca0f6ba68b429618bf0004a4beb50f586164e95f13e6a0980ca", "PROBE_SHA256=84cd91e6b842b86fbd8b62eb042be0e1873a9738625743aaf3896d5d5dda9d77", 1),
    ("VALIDATOR_SHA256=73e43ae3e4ec1df35f59b88caabaf17ab4b2f54ba1b5cfc51a7cff982a4d060d", "VALIDATOR_SHA256=c1ab2bae4f8b2f4f2d462707fb4191d34cb129946c41447d2ac653da57a6073d", 1),
    ("a72-platform-state-only-attempt-1", "a72-platform-state-stage27-attempt-1", 1),
    (".gemini-a72-platform-only.XXXXXXXX", ".gemini-a72-platform-stage27.XXXXXXXX", 1),
    ("runtime_gate=serviceable-platform-state-only-pass", "runtime_gate=serviceable-platform-state-stage27-pass", 1),
    ("exact platform-state-only pass", "exact Stage-27 minimum platform-state pass", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe Stage-27 provider collector derivation: expected {count}, found {actual}: {old}")
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
