#!/usr/bin/env bash

# Materialize the complete read-only probe for the exact checkpoint candidate.
set -euo pipefail

readonly SOURCE_SHA256=57f7c9dc2ff66143c4297d02fd689b34f01126cacf8141e92e137327eaf297c0
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-31-mainline-a72-p30e-ready-identity-repair/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-entry-checkpoint-probe.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "459bcf66fe807d9babfeefec7ea9b6e922edfaaa078fcbd288c7639048b31d16"
new = "6d0bf75b55ef981a915ba0b9a8d305d5713476acc4fc2ee95e4201f234b2253f"
if text.count(old) != 1:
    raise SystemExit("unsafe checkpoint pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
