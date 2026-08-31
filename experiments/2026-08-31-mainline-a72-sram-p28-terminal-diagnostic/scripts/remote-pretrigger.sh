#!/usr/bin/env bash

# Materialize the complete read-only probe for the exact SRAM/P28 diagnostic.
set -euo pipefail

readonly SOURCE_SHA256=feb927cd43bc54b32bd4cedfc2da8164e83f5b722cdae636feaedfa3fc3a3d78
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-30-mainline-a72-isolation-held-result-contract-repair/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-sram-p28-diagnostic-probe.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726"
new = "7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3"
if text.count(old) != 1:
    raise SystemExit("unsafe SRAM/P28 diagnostic pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
