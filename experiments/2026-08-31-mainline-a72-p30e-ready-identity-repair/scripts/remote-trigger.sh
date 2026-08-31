#!/usr/bin/env bash

# Materialize the reviewed one-shot trigger with the exact ABI-3 P30E guard
# validated by the corrected all-blocker pretrigger contract.
set -euo pipefail

readonly SOURCE_SHA256=5a01a7128202b7e1d6c776d38cd594e8c90bf21b94cbf493c3a17dcd05cfe029
readonly VALIDATOR_SHA256=05accc9657be8268b0602216324919efa193243c61ad2ae78bdc2a6e3734304d
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_trigger="$repo_root/experiments/2026-08-31-mainline-a72-sram-selector-mask-contract-repair/scripts/remote-trigger.sh"
validator="$script_dir/validate-pretrigger.py"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source trigger changed\n' >&2
	exit 2
}
[[ "$(sha256sum "$validator" | awk '{print $1}')" == "$VALIDATOR_SHA256" ]] || {
	printf 'error: P30E READY-identity pre-trigger validator changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-p30e-ready-identity-trigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_trigger" "$@" >"$materialized"
python3 - "$materialized" "$validator" <<'PY'
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
spec = spec_from_file_location("p30e_ready_identity_pretrigger", sys.argv[2])
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)
new = module.ARMED
suffix = (
    " p30e_prepare_attempted=0 p30e_prepare_ret=0 p30e_arm_attempted=0"
    " p30e_arm_ret=0 p30e_armed=0 p30e_readback_attempted=0"
    " p30e_readback_ret=0 p30e_controller_state=0 p30e_target_state=0"
    " p30e_target_sequence=0 p30e_controller_sequence=0"
)
if not new.endswith(suffix) or new.count("binder_abi=3") != 1:
    raise SystemExit("P30E armed contract changed")
old = new[:-len(suffix)].replace("binder_abi=3", "binder_abi=2", 1)
if text.count(old) != 1:
    raise SystemExit("unsafe P30E READY-identity trigger derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
