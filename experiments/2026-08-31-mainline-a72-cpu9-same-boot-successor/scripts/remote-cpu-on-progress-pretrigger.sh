#!/usr/bin/env bash

# Materialize the source-pinned read-only probe for the exact CPU_ON progress
# candidate.
set -euo pipefail

readonly SOURCE_SHA256=9cd506a4052dd65a5b4c877ff514a66262ec960ab77032d32381329ada2522d5
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_probe="$script_dir/remote-cpuhp-lock-repair-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source CPUHP lock-repair pre-trigger probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-cpu-on-progress-pretrigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "0904c5a293fea22f6993cb25ab8d775ed539d57c8fac7a7a6c50b67e2916f293"
new = "d4eca4accded2692418b5972f0a51df79a8be1a0fc52b52f755258da86eb87fe"
if text.count(old) != 1:
    raise SystemExit("unsafe CPU_ON progress pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
