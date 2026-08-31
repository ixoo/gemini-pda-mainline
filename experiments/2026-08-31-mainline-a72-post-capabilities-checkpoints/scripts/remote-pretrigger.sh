#!/usr/bin/env bash

# Materialize the complete read-only probe for the exact post-capabilities candidate.
set -euo pipefail

readonly SOURCE_SHA256=21fe26af7995e50cd9f4e50eecc299ed03a2da87fbb3e81b10c469b227d0b329
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-31-mainline-a72-secondary-entry-checkpoints/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-postcap-probe.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "6d0bf75b55ef981a915ba0b9a8d305d5713476acc4fc2ee95e4201f234b2253f"
new = "9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630"
if text.count(old) != 1:
    raise SystemExit("unsafe post-capabilities pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
