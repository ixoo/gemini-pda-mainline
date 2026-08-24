#!/usr/bin/env bash

# Source-pin the guarded passed-clock installer and retarget only its exact
# read-free BigiDVFS-backend candidate. The retained-record gate is unchanged.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=21e3380fb9bfbb0aab80f6d08799d3eef1bbfa69a023765ac3875ed4a5550411
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-24-mainline-a72-clock-backend-stage27-control/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-bigidvfs-stage27.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("4c5276ecf3fe60d7df55fd1fe44235432fcd928d2174704e5928bae7d84056e4", "0b17da983293f68f227931c964021b43efb1cdd57b4d0cf4db3bd70312f6092a", 1),
    ("333be3f8e73ac92b0d745c8edf3ca596e9813eeabb112ac529ed497a4eb3f923", "e878c6dae9d1f3b196410cc66195f32141af7dba540cdfde1942983dedf43ff5", 1),
    ("candidate-a72-clock-backend-stage27-2ec5bd07", "candidate-a72-bigidvfs-backend-stage27-2abb81d0", 1),
    ("a72-clock-backend-stage27-deployment-", "a72-bigidvfs-backend-stage27-deployment-", 1),
    (r"\.gemini-a72-clock-backend-stage27\.", r"\.gemini-a72-bigidvfs-backend-stage27\.", 1),
    ("/home/gemini/.gemini-a72-clock-backend-stage27.XXXXXXXX", "/home/gemini/.gemini-a72-bigidvfs-backend-stage27.XXXXXXXX", 1),
    ("experiment=2026-08-24-mainline-a72-clock-backend-stage27-control", "experiment=2026-08-24-mainline-a72-bigidvfs-backend-stage27-control", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe BigiDVFS installer derivation: expected {count}, found {actual}: {old}")
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
