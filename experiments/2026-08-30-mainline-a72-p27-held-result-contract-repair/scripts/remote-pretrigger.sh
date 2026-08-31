#!/usr/bin/env bash

# Materialize the complete read-only probe for the exact held-result repair.
set -euo pipefail

readonly SOURCE_SHA256=c7530fde97bc834bb6d8ae3e1a47ebbcffc21b1c78dbb9103c13bb9ef1198702
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-30-mainline-a72-p27-runtime-attribution/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-p27-held-result-probe.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "e22db74764e70d11f75271012733b8922a6f231d46ce363dfad9fafacdec0a80"
new = "fbe0bf76dd0cd88f1bc89043b72e9b7e4fe705568d8107b956eb6c3bd18593b5"
if text.count(old) != 1:
    raise SystemExit("unsafe held-result repair pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
