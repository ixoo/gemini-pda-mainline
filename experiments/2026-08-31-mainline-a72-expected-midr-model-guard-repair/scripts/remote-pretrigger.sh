#!/usr/bin/env bash

# Materialize the complete read-only probe for the exact model-guard candidate.
set -euo pipefail

readonly SOURCE_SHA256=9c4491e18cac8b403fa120cfd3f6c31735b3079130d9e02d8594f1aa2b31b8a2
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-31-mainline-a72-r0p1-expected-pair-repair/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-model-guard-probe.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d"
new = "5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69"
if text.count(old) != 1:
    raise SystemExit("unsafe model-guard pre-trigger probe derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
