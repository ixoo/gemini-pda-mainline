#!/usr/bin/env bash

# Materialize the source-pinned read-only probe for the exact CPU9 progress
# errno diagnostic candidate.
set -euo pipefail

readonly SOURCE_SHA256=f284a4a27b84f87515f52fa68ade902cf7bf1920cd37ceeecb1d021fbbe99e63
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_probe="$script_dir/remote-mapping-fix-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source CPU9 mapping-fix pre-trigger probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-progress-errno-pretrigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "c531a9e05ae6f2d51211d73fb487efbaef235cfede195ba135e819bd4f2575c0"
new = "4bf74874cbfe900576ae891d32b5e8996d5c66ed599b6fca09c7310e87cdeae8"
if text.count(old) != 1:
    raise SystemExit("unsafe CPU9 progress errno pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
