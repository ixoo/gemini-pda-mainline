#!/usr/bin/env bash

# Materialize the source-pinned read-only pre-trigger probe for the exact
# CPU9 progress-instrumented image.
set -euo pipefail

readonly SOURCE_SHA256=b3e672ac786626c8b2fcaa36e447941d2f7b16b97b5c4b80097cc0915eae2fbb
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_probe="$script_dir/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source CPU9 pre-trigger probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-progress-pretrigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "118096351905936e8f7c1fe9b186dadb191808bc94092cbd7a67a0b936a00562"
new = "ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72"
if text.count(old) != 1:
    raise SystemExit("unsafe CPU9 progress pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
