#!/usr/bin/env bash

# Materialize the complete read-only probe for the exact r0p1 candidate.
set -euo pipefail

readonly SOURCE_SHA256=f0f558ce82cd712a84f5b6adc4a3b2ee48e370c42669489dd1dad6a108413772
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-31-mainline-a72-post-capabilities-checkpoints/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-r0p1-probe.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630"
new = "b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d"
if text.count(old) != 1:
    raise SystemExit("unsafe r0p1 pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
