#!/usr/bin/env bash

# Materialize the read-only probe for the exact stage-ledger candidate.
set -euo pipefail

readonly SOURCE_SHA256=80e9a7220f329ce54d24101ce9ce73123af0e9d642b423a61a4709646f355dbb
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-31-mainline-a72-expected-midr-model-guard-repair/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-effect-plan-stage-probe.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old_candidate = "5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69"
new_candidate = "b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1"
anchor = (
    "$BB printf 'proof_mask_24000_count='; $BB dmesg | "
    "$BB grep -Fc 'proof mask 0x24000' || true\n"
)
insert = anchor + """$BB printf 'effect_derive_target8_count='; $BB dmesg | $BB grep -F 'A72_EFFECT_DERIVE_V1 ' | $BB grep -Fc ' target=8 ' || true
$BB printf 'effect_derive_target8_line='; $BB dmesg | $BB grep -F 'A72_EFFECT_DERIVE_V1 ' | $BB grep -Fm1 ' target=8 ' || $BB printf '\n'
$BB printf 'effect_derive_target9_count='; $BB dmesg | $BB grep -F 'A72_EFFECT_DERIVE_V1 ' | $BB grep -Fc ' target=9 ' || true
$BB printf 'effect_derive_target9_line='; $BB dmesg | $BB grep -F 'A72_EFFECT_DERIVE_V1 ' | $BB grep -Fm1 ' target=9 ' || $BB printf '\n'
$BB printf 'effect_plan_preconditions_count='; $BB dmesg | $BB grep -Fc 'ARM64_LATE_CPU_EFFECT_PLAN_V1 stage=preconditions ' || true
$BB printf 'effect_plan_preconditions_line='; $BB dmesg | $BB grep -Fm1 'ARM64_LATE_CPU_EFFECT_PLAN_V1 stage=preconditions ' || $BB printf '\n'
$BB printf 'effect_plan_derive_count='; $BB dmesg | $BB grep -Fc 'ARM64_LATE_CPU_EFFECT_PLAN_V1 stage=derive ' || true
$BB printf 'effect_plan_derive_line='; $BB dmesg | $BB grep -Fm1 'ARM64_LATE_CPU_EFFECT_PLAN_V1 stage=derive ' || $BB printf '\n'
$BB printf 'effect_plan_validate_count='; $BB dmesg | $BB grep -Fc 'ARM64_LATE_CPU_EFFECT_PLAN_V1 stage=validate ' || true
$BB printf 'effect_plan_validate_line='; $BB dmesg | $BB grep -Fm1 'ARM64_LATE_CPU_EFFECT_PLAN_V1 stage=validate ' || $BB printf '\n'
$BB printf 'effect_plan_complete_count='; $BB dmesg | $BB grep -Fc 'ARM64_LATE_CPU_EFFECT_PLAN_V1 stage=complete ' || true
$BB printf 'effect_plan_complete_line='; $BB dmesg | $BB grep -Fm1 'ARM64_LATE_CPU_EFFECT_PLAN_V1 stage=complete ' || $BB printf '\n'
"""
for old, new, count in (
    (old_candidate, new_candidate, 1),
    (anchor, insert, 1),
):
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe stage-ledger pre-trigger probe derivation: expected "
            f"{count}, found {actual}"
        )
    text = text.replace(old, new)
sys.stdout.write(text)
PY
cleanup
trap - EXIT HUP INT TERM
