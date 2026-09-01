#!/usr/bin/env bash

# Materialize the proven CPU8-to-CPU9 trigger while binding it to the exact
# pristine contract of the retained-reader mapping-fix candidate.
set -euo pipefail

readonly SOURCE_SHA256=2e8a307a837741ead989284b3c74832504a7c4e64fbf55c9b0b2e3dc4878a609
readonly VALIDATOR_SHA256=26fac1ea17aec094ba09c466956c4ccacab61f5e6ecc6aac2d1d385ab1597a7f
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_trigger="$script_dir/remote-progress-trigger.sh"
validator="$script_dir/validate-mapping-fix-pretrigger.py"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source CPU9 progress trigger changed\n' >&2
	exit 2
}
[[ "$(sha256sum "$validator" | awk '{print $1}')" == "$VALIDATOR_SHA256" ]] || {
	printf 'error: CPU9 mapping-fix pre-trigger validator changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-mapping-fix-trigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_trigger" "$@" >"$materialized"
python3 - "$materialized" "$validator" <<'PY'
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
spec = spec_from_file_location("cpu9_mapping_fix_pretrigger", sys.argv[2])
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)
armed = "ARMED='" + module.ARMED + "'"
if text.count(armed) != 1:
    raise SystemExit("CPU9 mapping-fix trigger status contract changed")
sys.stdout.write(text)
PY
cleanup
trap - EXIT HUP INT TERM
