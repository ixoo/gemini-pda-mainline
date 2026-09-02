#!/usr/bin/env bash

# Materialize the source-pinned read-only probe for the exact completion-path
# lock-repair candidate.
set -euo pipefail

readonly SOURCE_SHA256=3c96b40d8d48fec85bb78163363eae3806a1544e6536877183a6adff0a623a9b
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_probe="$script_dir/remote-membership-lock-repair-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source membership-lock pre-trigger probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-completion-lock-pretrigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c"
new = "370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e"
if text.count(old) != 1:
    raise SystemExit("unsafe completion-lock pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
