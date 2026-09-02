#!/usr/bin/env bash

# Materialize the proven CPU8-to-CPU9 trigger while binding it to the exact
# pristine contract of the CPU_ON progress candidate.
set -euo pipefail

readonly SOURCE_SHA256=eb0c33abd35fdc621a433968bc7192a20411fd1e0826d31345ec4b099ebca5f4
readonly VALIDATOR_SHA256=bf19f8d6343df7aeff659941198986b6cd5deccca595b0600a6e951e60385645
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_trigger="$script_dir/remote-cpuhp-lock-repair-trigger.sh"
validator="$script_dir/validate-cpu-on-progress-pretrigger.py"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source CPUHP lock-repair trigger changed\n' >&2
	exit 2
}
[[ "$(sha256sum "$validator" | awk '{print $1}')" == "$VALIDATOR_SHA256" ]] || {
	printf 'error: CPU_ON progress pre-trigger validator changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-cpu-on-progress-trigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_trigger" "$@" >"$materialized"
python3 - "$materialized" "$validator" <<'PY'
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
spec = spec_from_file_location("cpu9_cpu_on_progress_pretrigger", sys.argv[2])
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)
armed = "ARMED='" + module.ARMED + "'"
if text.count(armed) != 1:
    raise SystemExit("CPU_ON progress trigger status contract changed")
sys.stdout.write(text)
PY
cleanup
trap - EXIT HUP INT TERM
