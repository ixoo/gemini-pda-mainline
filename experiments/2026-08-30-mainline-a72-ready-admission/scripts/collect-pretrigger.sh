#!/usr/bin/env bash

# Source-pin the proven read-only serviceability collector and retarget it to
# the exact READY-bound candidate. This script never sends the trigger token.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=31cd2e82d4dfa4fc666fdd8c8ff28e5d8022df4a78b05ed0fc5f964ec823c7ee
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-28-mainline-a72-admission-serviceability-restoration/scripts/collect-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'
derived=$(mktemp "$script_dir/.derived-collect-a72-ready-pretrigger.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("f4cb1b2c8bc3759a23515c41d6c3c9248c1095277cb158e082a5b322e6927c02", "8acf9227e6539e5011ab59a27e1320bf970c19cbbf5a5325fe3304f0e04dddb7", 1),
    ("55361c7e8df662a1c124b2bd1fe9eef6e22aee85a442883ccc2004173bb21c1e", "08d3c9d2780c59dd871f710e735a96181027978cb1d502cf76c162297638d0c9", 1),
    ("bd0c14b6320713e1b73ef4ec3fee908c026babd35bbbe2131701e3aaf082cd90", "68cbb6af510c45ee69b320246ccee04e2a2c5f3ec88f7bde0d0daf7e374a97f9", 1),
    ("5afa0f77e601f6407fc8a993ac0585148b8fc8567cb81947b576069f29b282e3", "b012426e2e3bc912da63655dc9e325b4d3113d8db73e41959b1746e2815aae80", 1),
    ("a72-admission-serviceability-attempt-1", "a72-ready-admission-pretrigger-attempt-1", 2),
    (".gemini-a72-serviceability-probe.XXXXXXXX", ".gemini-a72-ready-probe.XXXXXXXX", 1),
    (".gemini-a72-serviceability-command.XXXXXXXX", ".gemini-a72-ready-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe READY pre-trigger collector derivation: expected {count}, found {actual}: {old}")
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
