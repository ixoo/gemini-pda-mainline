#!/usr/bin/env bash

# Materialize the read-only probe for the exact expected-pair model repair.
set -euo pipefail

readonly SOURCE_SHA256=2b6ed5dbcea25613ea5bef0b66f4500bf2d1b0b17d5eae49fe279e1cacb97406
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-31-mainline-a72-effect-plan-stage-ledger/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-expected-pair-model-probe.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old_candidate = "b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1"
new_candidate = "42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee"
if text.count(old_candidate) != 1:
    raise SystemExit("unsafe expected-pair pre-trigger probe derivation")
sys.stdout.write(text.replace(old_candidate, new_candidate))
PY
cleanup
trap - EXIT HUP INT TERM
