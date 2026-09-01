#!/usr/bin/env bash

# Materialize the proven CPU8-to-CPU9 trigger while binding it to the exact
# pristine contract of the progress raw-lane repair candidate.
set -euo pipefail

readonly SOURCE_SHA256=8a390fa06e7bd8fd30701fd947ff0e21a4fdbd3ae6c356fba36a8acab20472d9
readonly VALIDATOR_SHA256=3edab4c7d0f83a3323a0a6b02c939b754ac9de59c36e1f8044155059d11aa3f4
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_trigger="$script_dir/remote-progress-errno-diagnostic-trigger.sh"
validator="$script_dir/validate-progress-raw-lane-pretrigger.py"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source CPU9 progress errno trigger changed\n' >&2
	exit 2
}
[[ "$(sha256sum "$validator" | awk '{print $1}')" == "$VALIDATOR_SHA256" ]] || {
	printf 'error: CPU9 progress raw-lane pre-trigger validator changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-progress-raw-lane-trigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_trigger" "$@" >"$materialized"
python3 - "$materialized" "$validator" <<'PY'
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
spec = spec_from_file_location("cpu9_progress_raw_lane_pretrigger", sys.argv[2])
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)
armed = "ARMED='" + module.ARMED + "'"
if text.count(armed) != 1:
    raise SystemExit("CPU9 progress raw-lane trigger status contract changed")
sys.stdout.write(text)
PY
cleanup
trap - EXIT HUP INT TERM
