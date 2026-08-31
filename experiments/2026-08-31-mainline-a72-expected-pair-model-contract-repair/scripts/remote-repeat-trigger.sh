#!/usr/bin/env bash

# Add one bounded, read-only CPU8 accounting sample pair to the reviewed
# boot-bound ABI-5 one-shot trigger. No second device session is required.
set -euo pipefail

readonly SOURCE_SHA256=623cbbf621da6ae924ff238e2acd0ace0d15d4c735ba11fbe8492afa91dfe25b
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_trigger="$script_dir/remote-trigger.sh"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source trigger changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-expected-pair-repeat-trigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_trigger" "$@" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
anchor = "$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline\n"
observation = anchor + (
    "$BB printf 'cpu8_stat_first='; "
    "$BB grep '^cpu8 ' /proc/stat 2>/dev/null || $BB printf 'unavailable\\n'\n"
    "$BB sleep 1\n"
    "$BB printf 'cpu8_stat_second='; "
    "$BB grep '^cpu8 ' /proc/stat 2>/dev/null || $BB printf 'unavailable\\n'\n"
)
if text.count(anchor) != 1:
    raise SystemExit("unsafe repeat accounting insertion")
sys.stdout.write(text.replace(anchor, observation))
PY
cleanup
trap - EXIT HUP INT TERM
