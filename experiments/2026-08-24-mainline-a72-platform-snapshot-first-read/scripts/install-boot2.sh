#!/usr/bin/env bash

# Source-pin the guarded passed-BigiDVFS installer and retarget only its exact
# platform-snapshot candidate. The retained-record and clean-shutdown gates stay unchanged.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=d532860817dba42a93259be70af2956517d80cfc98e5da10a92d7b86595b3c94
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-24-mainline-a72-bigidvfs-backend-stage27-control/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-platform-snapshot.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("0b17da983293f68f227931c964021b43efb1cdd57b4d0cf4db3bd70312f6092a", "39f801f713a76c616ed8d9282fc0a662fb34c5a766d6839e4c47c757638bae43", 1),
    ("e878c6dae9d1f3b196410cc66195f32141af7dba540cdfde1942983dedf43ff5", "5205af4fad4049f7acbcc000c1a417c6e9d555329f86b9dae759c9e45a7212f1", 1),
    ("candidate-a72-bigidvfs-backend-stage27-2abb81d0", "candidate-a72-platform-snapshot-7d87638c", 1),
    ("a72-bigidvfs-backend-stage27-deployment-", "a72-platform-snapshot-deployment-", 1),
    (r"\.gemini-a72-bigidvfs-backend-stage27\.", r"\.gemini-a72-platform-snapshot\.", 1),
    ("/home/gemini/.gemini-a72-bigidvfs-backend-stage27.XXXXXXXX", "/home/gemini/.gemini-a72-platform-snapshot.XXXXXXXX", 1),
    ("experiment=2026-08-24-mainline-a72-bigidvfs-backend-stage27-control", "experiment=2026-08-24-mainline-a72-platform-snapshot-first-read", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe platform-snapshot installer derivation: expected {count}, found {actual}: {old}"
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
