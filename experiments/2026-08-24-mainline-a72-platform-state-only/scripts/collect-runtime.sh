#!/usr/bin/env bash

# Source-pin the no-reboot live collector and specialize its identities and
# acceptance gate for the platform-state-only candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0a4cf2cf6f21e588a8b393247f2dae3876e071ab471fe4892095f30c68284305
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-24-mainline-a72-early-live-control/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-platform-only.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("070e0ff4b019dd35e91ba91413b9ae958cf5e71e3573ed81bc9dd7d1cf3cc4ef", "012f7eac6884e65baab075ef286929f610a63f2ea065eba45865bd046492a23f", 1),
    ("PROBE_SHA256=29aabf7219a476e352fa43b7988258d17aa941b87cbcac797a3963e3da28909f", "PROBE_SHA256=c1d206cbdea16ca0f6ba68b429618bf0004a4beb50f586164e95f13e6a0980ca", 1),
    ("VALIDATOR_SHA256=6fb2c2f7773c49d44d1cc9aa20402823d7f30c9bfd240bb204eb93f909f353fb", "VALIDATOR_SHA256=73e43ae3e4ec1df35f59b88caabaf17ab4b2f54ba1b5cfc51a7cff982a4d060d", 1),
    ("a72-early-live-control-attempt-1", "a72-platform-state-only-attempt-1", 2),
    (".gemini-a72-early-live.XXXXXXXX", ".gemini-a72-platform-only.XXXXXXXX", 1),
    ("runtime_classification=serviceable-stage27-control-pass", "runtime_gate=serviceable-platform-state-only-pass", 2),
    ("exact Stage-27 control pass", "exact platform-state-only pass", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe platform-only collector derivation: expected {count}, found {actual}: {old}")
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
