#!/usr/bin/env bash

# Source-pin the proven read-only collector and retarget it to the
# classification-universe closure candidate. This script never sends a trigger.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=510779e08ca1fe5b45e7ef43f09b70b670be6e51bba97a7a87809445effbe8be
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-30-mainline-a72-ready-plan-expectation-repair/scripts/collect-ready.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-classification-closure.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("9abdd1c66b8665ed7ccd0b9ca8e0cc7b74ddd40ebce65b2fb5d7a37aef6571cc", "2245c1c4056cfd849ff89ba8afa220bf0cf038f1ea23a324c1e717c6ea23d89b", 1),
    ("d59dc7827e8883370a38bc1aed7891e38e470785ece30185f82fa16a50e977a9", "5fd6b13e4d73adec3f8e8e838222987e96ba2123322112fcedb7188504975c5c", 1),
    ("867490436bca15d897486a586deb1e9545383356c5781bd77efacdd249d75cd0", "474fe44035b14a5947cb3dc2462185d5586a2a64941f7a455db65e6e1406f6fc", 1),
    ("a72-ready-plan-expectation-repair-attempt-1", "a72-classification-universe-closure-attempt-1", 1),
    (".derived-collect-a72-ready-plan-repair.XXXXXXXX", ".derived-collect-a72-classification-closure-inner.XXXXXXXX", 1),
    (".gemini-a72-ready-plan-repair-probe.XXXXXXXX", ".gemini-a72-classification-closure-probe.XXXXXXXX", 1),
    (".gemini-a72-ready-plan-repair-command.XXXXXXXX", ".gemini-a72-classification-closure-command.XXXXXXXX", 1),
    ("unsafe READY-repair collector derivation", "unsafe classification-closure collector derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe classification-closure collector derivation: expected {count}, found {actual}: {old}"
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
