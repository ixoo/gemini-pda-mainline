#!/usr/bin/env bash

# Materialize the complete read-only probe for the exact P30E candidate.
set -euo pipefail

readonly SOURCE_SHA256=23177682a61122b6055aba518d15e803c207b828f2d4c4d41cc3f332b9dccd14
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-31-mainline-a72-sram-selector-mask-contract-repair/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-p30e-entry-probe.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "cd36efdfbf1e3d7da00cf5a36ded07abfaf2a640d1f731aaad00feef01549743"
new = "a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453"
if text.count(old) != 1:
    raise SystemExit("unsafe P30E pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
