#!/usr/bin/env bash

# Materialize the proven read-only pre-trigger probe for the exact CPU9 image.
set -euo pipefail

readonly SOURCE_SHA256=a303ab237d22d2ae55d1df656cd963698152937dc7d122f87f5896eb7c7ae561
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-31-mainline-a72-expected-pair-model-contract-repair/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-pretrigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee"
new = "118096351905936e8f7c1fe9b186dadb191808bc94092cbd7a67a0b936a00562"
if text.count(old) != 1:
    raise SystemExit("unsafe CPU9 pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
