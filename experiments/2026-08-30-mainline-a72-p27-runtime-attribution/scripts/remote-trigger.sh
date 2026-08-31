#!/usr/bin/env bash

# Materialize the reviewed one-shot CPU8 trigger for one accepted boot ID and
# require the complete P27 diagnostic armed status before its sole sysfs write.
set -euo pipefail

readonly SOURCE_SHA256=79bc42ca393f5726648be93b7a4e1d2378fd0b9c306007209d1901cf49824468
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# == 2 && $1 == --boot-id ]] || die "usage: $0 --boot-id UUID"
boot_id=$2
[[ "$boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] || die 'boot ID is malformed'
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_trigger="$repo_root/experiments/2026-08-30-mainline-a72-cpu8-ready-one-shot/scripts/remote-trigger.sh"
[[ -f "$source_trigger" && ! -L "$source_trigger" ]] || die 'source trigger is absent or unsafe'
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source trigger changed'

python3 - "$source_trigger" "$boot_id" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
boot_id = sys.argv[2]
old_armed = (
    "GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 "
    "trigger_executions=0 operation_ret=-115 core_consumed=0 "
    "entry_trace_ret=0 terminal_trace_ret=0 cpu_requests=0 "
    "cpu9_requests=0 cpu_off_requests=0 retries=0"
)
new_armed = (
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
anchor = "$BB printf '%s\\n' __GEMINI_A72_LIVE_TRIGGER_BEGIN__\n"
guard = anchor + (
    f"EXPECTED_BOOT_ID='{boot_id}'\n"
    "current_boot_id=$($BB cat /proc/sys/kernel/random/boot_id 2>/dev/null)\n"
    "$BB printf 'boot_id=%s\\n' \"$current_boot_id\"\n"
    "if [ \"$current_boot_id\" != \"$EXPECTED_BOOT_ID\" ]; then\n"
    "\t$BB printf '%s\\n' trigger_commit=no reason=boot-id-changed\n"
    "\t$BB printf '%s\\n' __GEMINI_A72_LIVE_TRIGGER_END__\n"
    "\texit 3\n"
    "fi\n"
)
replacements = ((old_armed, new_armed, 1), (anchor, guard, 1))
for old, new, count in replacements:
    if text.count(old) != count:
        raise SystemExit("unsafe P27 diagnostic trigger derivation")
    text = text.replace(old, new)
sys.stdout.write(text)
PY
