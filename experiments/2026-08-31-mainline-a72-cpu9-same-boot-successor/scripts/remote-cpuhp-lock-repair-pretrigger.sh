#!/usr/bin/env bash

# Materialize the source-pinned read-only probe for the exact CPUHP
# lock-repair candidate.
set -euo pipefail

readonly SOURCE_SHA256=d745138fa7b6c0a2fb19bf6a01fe127929a28df48fbd3972bf26e1647b17aafe
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_probe="$script_dir/remote-progress-raw-lane-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source progress raw-lane pre-trigger probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-cpuhp-lock-pretrigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "1cf367e021351f8a26643d827866786a879a8d6a3e68d8143cfce40bd1db52f7"
new = "0904c5a293fea22f6993cb25ab8d775ed539d57c8fac7a7a6c50b67e2916f293"
if text.count(old) != 1:
    raise SystemExit("unsafe CPUHP lock-repair pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
