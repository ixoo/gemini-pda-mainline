#!/usr/bin/env bash

# Materialize the reviewed one-shot trigger for the exact r0p1 candidate.
set -euo pipefail

readonly SOURCE_SHA256=88a0d2d8cc3994a6b95b4c04c832531846e52bf5fff38435b2187ef4dcc161b0
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_trigger="$repo_root/experiments/2026-08-31-mainline-a72-post-capabilities-checkpoints/scripts/remote-trigger.sh"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source trigger changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-r0p1-trigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_trigger" "$@" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630"
new = "b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d"
if text.count(old) != 1:
    raise SystemExit("unsafe r0p1 trigger derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
