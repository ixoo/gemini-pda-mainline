#!/usr/bin/env bash

# Materialize the proven read-only frame probe with the exact observer identity
# and failure-only READY predicate fields. This script never sends a trigger.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=5826658d983313d2ddb7b032dc80f8a7a3844076aaf346e36f852702e7cec010
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-30-mainline-a72-provenance-serviceability-composition/scripts/remote-pretrigger.sh"
[[ -f "$source_probe" && ! -L "$source_probe" ]] || die 'source probe is missing or unsafe'
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source probe changed'

derived=$(mktemp "$script_dir/.derived-remote-a72-ready-plan-diagnostic.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_probe" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
anchor = '''$BB printf 'profile_blocked_count='; $BB dmesg | $BB grep -Fc 'blocked: required evidence is incomplete' || true
'''
insert = anchor + '''$BB printf 'ready_plan_diag_count='; $BB dmesg | $BB grep -Fc 'A72_READY_PLAN_DIAG_V1 ' || true
$BB printf 'ready_plan_diag_line='; $BB dmesg | $BB grep -Fm1 'A72_READY_PLAN_DIAG_V1 ' || true
$BB printf 'proof_mask_24000_count='; $BB dmesg | $BB grep -Fc 'proof mask 0x24000' || true
'''
replacements = (
    ("f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", "7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272", 1),
    (anchor, insert, 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe predicate-diagnostic remote derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
rc=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
