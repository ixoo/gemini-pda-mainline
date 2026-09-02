#!/usr/bin/env bash

# Materialize the source-pinned read-only probe for the exact membership-begin
# lock-repair candidate.
set -euo pipefail

readonly SOURCE_SHA256=41f4eac6c2fc0f3faca53706a9dc056f2956dfa549d12e115dc5b641482e2940
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_probe="$script_dir/remote-cpu-on-progress-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source CPU_ON progress pre-trigger probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-membership-lock-pretrigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "d4eca4accded2692418b5972f0a51df79a8be1a0fc52b52f755258da86eb87fe"
new = "65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c"
if text.count(old) != 1:
    raise SystemExit("unsafe membership-lock pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
