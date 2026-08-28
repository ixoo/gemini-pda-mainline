#!/usr/bin/env bash

# Source-pin the trace-softfail one-shot collector and retarget only its exact
# corrected candidate, materialized helpers, and experiment identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a49713d80cf263663cb61e324fc685bb4e8ed1c4024f1d7a2c87200d05eca826
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"; done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-28-mainline-a72-admission-trace-softfail/scripts/collect-live-trigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'
derived=$(mktemp "$script_dir/.derived-collect-a72-softtrace-serviceable.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("83dec18625b82289a2dad9ba6c59d43a2f81f48ffbaca752cc2200f3b1facdf0",
     "df82bbfa012a994642a145beee994125cc9069092aad22e6af0321dfb7202f60", 1),
    ("f2b9dc49d4ba68af080e7119776f0ea758e6d9dbc9082bc661b5a37dc52b53d8",
     "be5406eb224ec9e8e8a4e8fa3991b349dd47f48c3e0f826ce21d582c6da0c7bd", 1),
    ("9188f8b96bdfeedc1921df5043eeb6e0120b2383b9a8fa454c50b5ef1ed64f0a",
     "836abe63ae47cfe79619023399f0de0e4f759b585209fde6350fb010882ea6ff", 1),
    ("033a80bd39a494d0b1d3d6f0773ca278112f2e98cffbd3d2fcdceab6db3b653f",
     "bcead1fe23fc45e69a3e13aa47b648e67e2de49c37b54d6236dde851e21d9057", 1),
    ("2026-08-28-mainline-a72-admission-trace-softfail",
     "2026-08-28-mainline-a72-admission-softtrace-serviceable", 1),
    (".derived-collect-a72-admission-softtrace.XXXXXXXX",
     ".derived-collect-a72-softtrace-serviceable-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    if text.count(old) != count:
        raise SystemExit(f"unsafe corrected collector derivation: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e; /bin/bash "$derived" "$@"; status=$?; set -e
cleanup; trap - EXIT HUP INT TERM; exit "$status"
