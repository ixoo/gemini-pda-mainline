#!/usr/bin/env bash

# Source-pin the guarded CPU9 installer to the exact progress-ledger
# diagnostic candidate and require the configuration-identity repair on boot2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=3cb6f89b89307a2aa4902252b4ab898370035c87283cc7f8b590f3a7de25ac7b
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/install-config-identity-repair-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-cpu9-progress.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("118096351905936e8f7c1fe9b186dadb191808bc94092cbd7a67a0b936a00562",
     "ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72", 1),
    ("5f8b1722c664c81d9c168c388c1f80037ea4dc16369ca94d04081cf897fc1c93",
     "e398c2b9156c31f02cb126be40204608b17f9df8a44a0f2268e05545d40448e2", 1),
    ("candidate-a72-cpu9-config-repair-e7ea9113",
     "candidate-a72-cpu9-progress-85d3b591", 1),
    ("cpu9-config-identity-repair", "cpu9-progress-ledger", 1),
    ("CPU9 configuration-identity repair", "CPU9 progress-ledger diagnostic", 1),
    ('new_predecessor = "fb473d2f3240137ec05f901163bb0374ef3015b66c42558eca6f1085cbd83468"',
     'new_predecessor = "118096351905936e8f7c1fe9b186dadb191808bc94092cbd7a67a0b936a00562"', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 progress installer derivation: expected {count}, "
            f"found {actual}: {old}"
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
