#!/usr/bin/env bash

# Materialize the complete read-only probe for the exact selector-mask repair.
set -euo pipefail

readonly SOURCE_SHA256=e0cf19260f8542d33fe5f143310247748966adb6e9ce1ab8db595bd60d2e0165
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-31-mainline-a72-sram-p28-terminal-diagnostic/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-selector-mask-repair-probe.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3"
new = "cd36efdfbf1e3d7da00cf5a36ded07abfaf2a640d1f731aaad00feef01549743"
if text.count(old) != 1:
    raise SystemExit("unsafe selector-mask repair pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
