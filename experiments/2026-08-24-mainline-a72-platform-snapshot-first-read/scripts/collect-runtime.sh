#!/usr/bin/env bash

# Source-pin the no-reboot BigiDVFS collector and specialize its exact
# identities and platform-snapshot acceptance gate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=c0332a677d325ece7e03813203e4e5623255b995de0441a08a0265eb55c1990a
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-24-mainline-a72-bigidvfs-backend-stage27-control/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-platform-snapshot.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("0b17da983293f68f227931c964021b43efb1cdd57b4d0cf4db3bd70312f6092a", "39f801f713a76c616ed8d9282fc0a662fb34c5a766d6839e4c47c757638bae43", 1),
    ("PROBE_SHA256=5efd814c132cd5ab710bdc0f27f7a42dc25db1c773f3dfcc54a478b5fc94ed7d", "PROBE_SHA256=0227c98f47e4fcebc01647694e126f3f64fe9a41802c438c1a6bab3fafef1e2b", 1),
    ("VALIDATOR_SHA256=02eecddd7696dabf4beafe716661194f1a9613a387f40362ea50e010d336c507", "VALIDATOR_SHA256=d3c4c03661a446e584a44f35534adb6a9e4b690f4244c7cc9a3b674ebcd6761d", 1),
    ("a72-bigidvfs-backend-stage27-attempt-1", "a72-platform-snapshot-attempt-1", 1),
    (".gemini-a72-bigidvfs-stage27.XXXXXXXX", ".gemini-a72-platform-snapshot.XXXXXXXX", 1),
    ("runtime_gate=serviceable-bigidvfs-backend-stage27-pass", "runtime_gate=serviceable-platform-snapshot-pass", 1),
    ("exact Stage-27 read-free BigiDVFS-backend serviceability pass", "exact one-shot platform-snapshot serviceability pass", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe platform-snapshot collector derivation: expected {count}, found {actual}: {old}"
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
