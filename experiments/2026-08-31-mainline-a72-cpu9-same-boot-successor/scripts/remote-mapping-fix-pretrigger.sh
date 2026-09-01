#!/usr/bin/env bash

# Materialize the source-pinned read-only probe for the exact CPU9 retained
# reader-mapping-fix candidate.
set -euo pipefail

readonly SOURCE_SHA256=ed6bbde65f0ce7dd0c5dd4bb53e1535c3cb624671b12904f27fe62edf03b5f99
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_probe="$script_dir/remote-progress-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source CPU9 progress pre-trigger probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-mapping-fix-pretrigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72"
new = "c531a9e05ae6f2d51211d73fb487efbaef235cfede195ba135e819bd4f2575c0"
if text.count(old) != 1:
    raise SystemExit("unsafe CPU9 mapping-fix pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
