#!/usr/bin/env bash

# Materialize the proven CPU8-to-CPU9 trigger and bind it to the exact
# pristine status contract of the progress-instrumented candidate.
set -euo pipefail

readonly SOURCE_SHA256=afbf7980de788db22874af59ce58ff83aa1cda46ce8f7d098db1bd84183dd7a6
readonly VALIDATOR_SHA256=4ad80105fd840ea02ca57c3dff1dd9fbe10b81047d06169b3981f4caa130867e
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_trigger="$script_dir/remote-trigger.sh"
validator="$script_dir/validate-progress-pretrigger.py"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source CPU9 trigger changed\n' >&2
	exit 2
}
[[ "$(sha256sum "$validator" | awk '{print $1}')" == "$VALIDATOR_SHA256" ]] || {
	printf 'error: CPU9 progress pre-trigger validator changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-progress-trigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_trigger" "$@" >"$materialized"
python3 - "$materialized" "$validator" <<'PY'
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
spec = spec_from_file_location("cpu9_progress_pretrigger", sys.argv[2])
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)
old = "ARMED='" + module.OLD_ARMED + "'"
new = "ARMED='" + module.ARMED + "'"
if text.count(old) != 1:
    raise SystemExit("unsafe CPU9 progress trigger status derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
