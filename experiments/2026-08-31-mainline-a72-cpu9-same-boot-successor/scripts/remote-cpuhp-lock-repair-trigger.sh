#!/usr/bin/env bash

# Materialize the proven CPU8-to-CPU9 trigger while binding it to the exact
# pristine contract of the CPUHP lock-repair candidate.
set -euo pipefail

readonly SOURCE_SHA256=00013d15f0bfa0a70ecb582ddee75d1834c8d888744f8af219c4246b2f181d7f
readonly VALIDATOR_SHA256=09bdca67375272870ce27e325368d86967a104f224dcd61bc7c38848f8f9370d
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_trigger="$script_dir/remote-progress-raw-lane-trigger.sh"
validator="$script_dir/validate-cpuhp-lock-repair-pretrigger.py"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source progress raw-lane trigger changed\n' >&2
	exit 2
}
[[ "$(sha256sum "$validator" | awk '{print $1}')" == "$VALIDATOR_SHA256" ]] || {
	printf 'error: CPUHP lock-repair pre-trigger validator changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-cpuhp-lock-trigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_trigger" "$@" >"$materialized"
python3 - "$materialized" "$validator" <<'PY'
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
spec = spec_from_file_location("cpu9_cpuhp_lock_repair_pretrigger", sys.argv[2])
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)
armed = "ARMED='" + module.ARMED + "'"
if text.count(armed) != 1:
    raise SystemExit("CPUHP lock-repair trigger status contract changed")
sys.stdout.write(text)
PY
cleanup
trap - EXIT HUP INT TERM
