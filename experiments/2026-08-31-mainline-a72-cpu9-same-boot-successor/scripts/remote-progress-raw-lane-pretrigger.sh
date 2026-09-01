#!/usr/bin/env bash

# Materialize the source-pinned read-only probe for the exact CPU9 progress
# raw-lane repair candidate.
set -euo pipefail

readonly SOURCE_SHA256=66d1c458600e481bc3dd7c59f32e3775081e34df0d83a50a3e9615d26013b9df
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_probe="$script_dir/remote-progress-errno-diagnostic-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source CPU9 progress errno pre-trigger probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-progress-raw-lane-pretrigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "4bf74874cbfe900576ae891d32b5e8996d5c66ed599b6fca09c7310e87cdeae8"
new = "1cf367e021351f8a26643d827866786a879a8d6a3e68d8143cfce40bd1db52f7"
if text.count(old) != 1:
    raise SystemExit("unsafe CPU9 progress raw-lane pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
