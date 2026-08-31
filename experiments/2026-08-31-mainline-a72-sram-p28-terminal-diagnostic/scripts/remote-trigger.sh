#!/usr/bin/env bash

# Materialize the reviewed one-shot trigger with the exact ABI-2 armed guard.
set -euo pipefail

readonly SOURCE_SHA256=b609a64e41d664167912dd0156c45c3428a13b0c9495deab8317ca9288611508
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_trigger="$repo_root/experiments/2026-08-30-mainline-a72-isolation-held-result-contract-repair/scripts/remote-trigger.sh"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source trigger changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-sram-p28-diagnostic-trigger.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_trigger" "$@" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = (
    "GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 "
    "trigger_executions=0 operation_ret=-115 core_consumed=0 "
    "entry_trace_ret=0 terminal_trace_ret=0 failure_stage=0 derive_stage=0 "
    "cpu_requests=0 cpu9_requests=0 cpu_off_requests=0 retries=0 "
    "binder_snapshot_ret=0 binder_abi=1 lifecycle=0 terminal=0 last_stage=0 "
    "stage_errno=0 rollback_errno=0 checkpoint_errno=0 attempted=0 "
    "watchdog_armed=0 p27_owned=0 rollback_mask=0x0 retained_mask=0x0 "
    "p27a_op=0 p27a_error=0 p27a_attempted=0x0 p27a_completed=0x0 "
    "p27a_spm_before=0x0 p27a_spm_after=0x0 p27a_bpll=0x0 "
    "p27a_owned=0 p27a_sealed=0 p27r_op=0 p27r_error=0 "
    "p27r_attempted=0x0 p27r_completed=0x0 p27r_spm_before=0x0 "
    "p27r_spm_after=0x0 p27r_bpll=0x0 p27r_owned=0 p27r_sealed=0"
)
suffix = (
    " p28_begin_attempted=0 p28_begin_ret=0 p28_begun=0 "
    "sram_returned=0 sram_ret=0 sram_match=0x0 sram_required=0xfff "
    "p28_complete_attempted=0 p28_complete_ret=0 sram_abi=0 "
    "sram_attempted=0x0 sram_completed=0x0 sram_mv=0 "
    "sram_selector_first=0x0 sram_calibration_first=0x0 "
    "sram_selector_second=0x0 sram_calibration_second=0x0 "
    "sram_attempt_id=0 sram_cookie=0 sram_error=0 "
    "sram_effect_attempted=0 sram_verified=0 sram_sealed=0"
)
new = old.replace("binder_abi=1", "binder_abi=2", 1) + suffix
if text.count(old) != 1:
    raise SystemExit("unsafe SRAM/P28 diagnostic trigger derivation")
sys.stdout.write(text.replace(old, new))
PY
cleanup
trap - EXIT HUP INT TERM
