#!/usr/bin/env bash

# Source-pin the proven read-only collector and retarget it to the exact
# failure-only READY value observer. This script never sends a trigger.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=c6eb8f220565b2fb41721f9e149fc19b055b4719598786094e5027b5e2f7c2b8
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-30-mainline-a72-ready-plan-predicate-diagnostic/scripts/collect-diagnostic.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-ready-plan-value.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("7ac6f42938365d8bb1de49803a46287186e9a25347039975c48c386d0c1d6272", "1c08f1fc9c2153965983eb469ea58babe7740fc4e3e7f14d799a060a44649d28", 1),
    ("10a6558897feb7d710ff35e9272ea469d9da4ee68d3dbf3a132bc17ec50ab127", "03a4164606deccc6714ce22ad5e8099009e98d8e186c0dbe0a9eb50c96c11325", 1),
    ("66dc7ad5e5675b99513042948b37201a4369e98c87cd141fd3e3da557dbfe426", "64e63a26e65abfa76497a319fa2e426eb00305bd98589a83263ce8c0a9fdf34f", 1),
    ("3ea7296b8431f19343b63d9f7fbefb11360b1a370cd9727cc069cb49e6673407", "9eb45c3045466b5beb4ff623de96aa9a3c35b5bd7764fe89540b7238f355bfbc", 1),
    ("a72-ready-plan-predicate-diagnostic-attempt-1", "a72-ready-plan-value-diagnostic-attempt-1", 1),
    (".derived-collect-a72-ready-plan-diagnostic.XXXXXXXX", ".derived-collect-a72-ready-plan-value-inner.XXXXXXXX", 1),
    (".gemini-a72-ready-plan-diagnostic-probe.XXXXXXXX", ".gemini-a72-ready-plan-value-probe.XXXXXXXX", 1),
    (".gemini-a72-ready-plan-diagnostic-command.XXXXXXXX", ".gemini-a72-ready-plan-value-command.XXXXXXXX", 1),
    ("diagnostic_classification=attributable-predicate-diagnostic-zero-execution", "diagnostic_classification=attributable-value-diagnostic-zero-execution", 1),
    ("unsafe predicate-diagnostic collector derivation", "unsafe value-diagnostic collector derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe value-diagnostic collector derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
