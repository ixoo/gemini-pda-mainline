#!/usr/bin/env bash

# Materialize the exact read-only frame probe for the repaired candidate. It
# observes the READY contract and never sends the CPU trigger.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=03a4164606deccc6714ce22ad5e8099009e98d8e186c0dbe0a9eb50c96c11325
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-30-mainline-a72-ready-plan-value-diagnostic/scripts/remote-diagnostic.sh"
[[ -f "$source_probe" && ! -L "$source_probe" ]] || die 'source probe is missing or unsafe'
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source probe changed'

derived=$(mktemp "$script_dir/.derived-remote-a72-ready-plan-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_probe" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("1c08f1fc9c2153965983eb469ea58babe7740fc4e3e7f14d799a060a44649d28", "9abdd1c66b8665ed7ccd0b9ca8e0cc7b74ddd40ebce65b2fb5d7a37aef6571cc", 1),
    (".derived-remote-a72-ready-plan-value.XXXXXXXX", ".derived-remote-a72-ready-plan-repair-inner.XXXXXXXX", 1),
    ("unsafe value-diagnostic remote derivation", "unsafe READY-repair remote derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe READY-repair remote derivation: expected {count}, found {actual}: {old}"
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
