#!/usr/bin/env bash

# Materialize the proven read-only pristine-state probe for the exact CPU-map
# candidate without altering any device state.
set -euo pipefail

readonly SOURCE_SHA256=a120caa080db781eb92cec9166b240446a01f870f8f3aeeccaecdbc9fa50c787
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/remote-completion-lock-repair-pretrigger.sh"
[[ -f "$source_probe" && ! -L "$source_probe" ]] || {
	printf 'error: source completion-lock pre-trigger probe is absent or unsafe\n' >&2
	exit 2
}
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source completion-lock pre-trigger probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-mt6797-cpu-map-pretrigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e"
new = "68ec1b7815cab7abae99cbdecabb2f0ba0dd1ddbf26943d652fcedf4d2b4e393"
if text.count(old) != 1:
    raise SystemExit("unsafe CPU-map pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
