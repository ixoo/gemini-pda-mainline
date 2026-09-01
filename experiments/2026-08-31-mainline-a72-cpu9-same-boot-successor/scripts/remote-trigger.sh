#!/usr/bin/env bash

# Materialize the proven boot-bound trigger with the exact pristine CPU9
# suffix and one bounded accounting interval for both A72 CPUs.
set -euo pipefail

readonly SOURCE_SHA256=623cbbf621da6ae924ff238e2acd0ace0d15d4c735ba11fbe8492afa91dfe25b
readonly VALIDATOR_SHA256=5bdf84f1ef47796a1e87f3208922f5ec5c088e48765138acef5e34764a6844c9
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_trigger="$repo_root/experiments/2026-08-31-mainline-a72-expected-pair-model-contract-repair/scripts/remote-trigger.sh"
validator="$script_dir/validate-pretrigger.py"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source trigger changed\n' >&2
	exit 2
}
[[ "$(sha256sum "$validator" | awk '{print $1}')" == "$VALIDATOR_SHA256" ]] || {
	printf 'error: CPU9 pre-trigger validator changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-cpu9-trigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_trigger" "$@" >"$materialized"
python3 - "$materialized" "$validator" <<'PY'
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
spec = spec_from_file_location("cpu9_pretrigger", sys.argv[2])
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)
old_armed = module.OLD_ARMED
new_armed = module.ARMED
for old, new, count in (
    ("ARMED='" + old_armed + "'", "ARMED='" + new_armed + "'", 1),
    ("$BB printf '%s\\n' cpu9_request=none",
     "$BB printf '%s\\n' cpu9_request=conditional-controller-one-shot", 1),
):
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 trigger derivation: expected {count}, found {actual}"
        )
    text = text.replace(old, new)

anchor = "$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline\n"
samples = anchor + (
    "$BB printf 'cpu8_stat_first='; "
    "$BB grep '^cpu8 ' /proc/stat 2>/dev/null || $BB printf 'unavailable\\n'\n"
    "$BB printf 'cpu9_stat_first='; "
    "$BB grep '^cpu9 ' /proc/stat 2>/dev/null || $BB printf 'unavailable\\n'\n"
    "$BB sleep 1\n"
    "$BB printf 'cpu8_stat_second='; "
    "$BB grep '^cpu8 ' /proc/stat 2>/dev/null || $BB printf 'unavailable\\n'\n"
    "$BB printf 'cpu9_stat_second='; "
    "$BB grep '^cpu9 ' /proc/stat 2>/dev/null || $BB printf 'unavailable\\n'\n"
)
if text.count(anchor) != 1:
    raise SystemExit("unsafe CPU9 accounting insertion")
sys.stdout.write(text.replace(anchor, samples))
PY
cleanup
trap - EXIT HUP INT TERM
