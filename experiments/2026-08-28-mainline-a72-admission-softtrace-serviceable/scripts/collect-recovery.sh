#!/usr/bin/env bash

# Source-pin the trace-softfail recovery collector and retarget only the exact
# corrected candidate, experiment identity, and private temporary name.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=687632364741e7efff2e48d8fee768f039c1d4f73e2f4a38c41614855b5865e6
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"; done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-28-mainline-a72-admission-trace-softfail/scripts/collect-recovery.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'
derived=$(mktemp "$script_dir/.derived-collect-softtrace-serviceable-recovery.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("83dec18625b82289a2dad9ba6c59d43a2f81f48ffbaca752cc2200f3b1facdf0",
     "df82bbfa012a994642a145beee994125cc9069092aad22e6af0321dfb7202f60", 1),
    ("2026-08-28-mainline-a72-admission-trace-softfail",
     "2026-08-28-mainline-a72-admission-softtrace-serviceable", 1),
    (".derived-collect-softtrace-recovery.XXXXXXXX",
     ".derived-collect-softtrace-serviceable-recovery-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    if text.count(old) != count:
        raise SystemExit(f"unsafe corrected recovery derivation: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e; /bin/bash "$derived" "$@"; status=$?; set -e
cleanup; trap - EXIT HUP INT TERM; exit "$status"
