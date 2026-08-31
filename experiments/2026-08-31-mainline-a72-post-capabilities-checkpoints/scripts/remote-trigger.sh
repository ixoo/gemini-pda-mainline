#!/usr/bin/env bash

# Materialize the reviewed one-shot trigger with the exact ABI-5 checkpoint guard.
set -euo pipefail

readonly SOURCE_SHA256=2a203083e9034b04e963f30e6bff557863f41287aff55ca1e3ce43d0152e5777
readonly VALIDATOR_SHA256=6b2949fddca6c2001ed75cd11321f66ddbff253e4daf520f2554b4cbee26b407
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_trigger="$repo_root/experiments/2026-08-31-mainline-a72-secondary-entry-checkpoints/scripts/remote-trigger.sh"
validator="$script_dir/validate-pretrigger.py"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source trigger changed\n' >&2
	exit 2
}
[[ "$(sha256sum "$validator" | awk '{print $1}')" == "$VALIDATOR_SHA256" ]] || {
	printf 'error: post-capabilities pre-trigger validator changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-postcap-trigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_trigger" "$@" >"$materialized"
python3 - "$materialized" "$validator" <<'PY'
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
spec = spec_from_file_location("postcap_pretrigger", sys.argv[2])
assert spec is not None and spec.loader is not None
module = module_from_spec(spec)
spec.loader.exec_module(module)
new = module.ARMED
detail = (
    " p30e_target_effects=0x0 p30e_target_entry_pc=0x0"
    " p30e_target_entry_sp=0x0"
)
if new.count("binder_abi=5") != 1 or new.count(detail) != 1:
    raise SystemExit("post-capabilities armed contract changed")
old = new.replace("binder_abi=5", "binder_abi=4", 1).replace(detail, "", 1)
if text.count(old) != 1:
    raise SystemExit("unsafe post-capabilities trigger derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
