#!/usr/bin/env bash

# Materialize the proven read-only frame probe with the exact value-observer
# identity and failure-only READY value fields. This script never triggers.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=10a6558897feb7d710ff35e9272ea469d9da4ee68d3dbf3a132bc17ec50ab127
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-30-mainline-a72-ready-plan-predicate-diagnostic/scripts/remote-diagnostic.sh"
[[ -f "$source_probe" && ! -L "$source_probe" ]] || die 'source probe is missing or unsafe'
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source probe changed'

derived=$(mktemp "$script_dir/.derived-remote-a72-ready-plan-value.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_probe" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
anchor = """$BB printf 'ready_plan_diag_line='; $BB dmesg | $BB grep -Fm1 'A72_READY_PLAN_DIAG_V1 ' || true
"""
insert = anchor + """$BB printf 'ready_plan_values_count='; $BB dmesg | $BB grep -Fc 'A72_READY_PLAN_VALUES_V1 ' || true
$BB printf 'ready_plan_values_line='; $BB dmesg | $BB grep -Fm1 'A72_READY_PLAN_VALUES_V1 ' || true
"""
replacements = (
    ("7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272", "1c08f1fc9c2153965983eb469ea58babe7740fc4e3e7f14d799a060a44649d28", 1),
    (anchor, insert, 1),
    (".derived-remote-a72-ready-plan-diagnostic.XXXXXXXX", ".derived-remote-a72-ready-plan-value-inner.XXXXXXXX", 1),
    ("unsafe predicate-diagnostic remote derivation", "unsafe value-diagnostic remote derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe value-diagnostic remote derivation: expected {count}, found {actual}: {old}"
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
