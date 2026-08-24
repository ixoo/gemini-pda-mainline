#!/usr/bin/env bash

# Source-pin the no-reboot passed-clock collector and specialize its exact
# identities and read-free BigiDVFS-backend isolation acceptance gate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=c168f0303bb3f89c40d29fb79c13a2683a3222d414758832b1e2f5135355dfe7
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-24-mainline-a72-clock-backend-stage27-control/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-bigidvfs-stage27.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("4c5276ecf3fe60d7df55fd1fe44235432fcd928d2174704e5928bae7d84056e4", "0b17da983293f68f227931c964021b43efb1cdd57b4d0cf4db3bd70312f6092a", 1),
    ("PROBE_SHA256=9cd0a08c73f881595cfd788db5e391a5d3d9c31675f17e1c09441ff8fc80260b", "PROBE_SHA256=5efd814c132cd5ab710bdc0f27f7a42dc25db1c773f3dfcc54a478b5fc94ed7d", 1),
    ("VALIDATOR_SHA256=e08a7c12f6e237e9e67eb0ce2a077aecde9c2cae0da35510c3cc62a418be4c8a", "VALIDATOR_SHA256=02eecddd7696dabf4beafe716661194f1a9613a387f40362ea50e010d336c507", 1),
    ("a72-clock-backend-stage27-attempt-1", "a72-bigidvfs-backend-stage27-attempt-1", 1),
    (".gemini-a72-clock-stage27.XXXXXXXX", ".gemini-a72-bigidvfs-stage27.XXXXXXXX", 1),
    ("runtime_gate=serviceable-clock-backend-stage27-pass", "runtime_gate=serviceable-bigidvfs-backend-stage27-pass", 1),
    ("exact Stage-27 read-free clock-backend serviceability pass", "exact Stage-27 read-free BigiDVFS-backend serviceability pass", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe BigiDVFS collector derivation: expected {count}, found {actual}: {old}")
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
