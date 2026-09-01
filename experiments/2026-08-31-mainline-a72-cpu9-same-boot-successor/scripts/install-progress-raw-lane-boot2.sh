#!/usr/bin/env bash

# Source-pin the guarded CPU9 installer to the exact progress raw-lane repair
# candidate and require the retired errno diagnostic image on boot2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=970f57695bcb82777b9075f53f7b330ed7cdca7e885d4a0f73b602f07f8f6ddd
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/install-progress-errno-diagnostic-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source progress errno installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source progress errno installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-cpu9-progress-raw-lane.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("4bf74874cbfe900576ae891d32b5e8996d5c66ed599b6fca09c7310e87cdeae8",
     "1cf367e021351f8a26643d827866786a879a8d6a3e68d8143cfce40bd1db52f7", 1),
    ("3e1ca9603abb8e3f5171a6fa832da59b4ec1546a9ef5c53b89af969246940081",
     "099757f497ee4e94ce5518c1d2c3974a2952df307bf82fb692f24cd949e5f422", 1),
    ("candidate-a72-cpu9-progress-errno-32d304dc",
     "candidate-a72-cpu9-progress-raw-lane-243ddc6e", 1),
    ("cpu9-progress-errno-diagnostic",
     "cpu9-progress-raw-lane-repair", 1),
    ("CPU9 progress errno diagnostic",
     "CPU9 progress raw-lane repair", 1),
    ('new_predecessor = "c531a9e05ae6f2d51211d73fb487efbaef235cfede195ba135e819bd4f2575c0"',
     'new_predecessor = "4bf74874cbfe900576ae891d32b5e8996d5c66ed599b6fca09c7310e87cdeae8"', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 progress raw-lane installer derivation: expected "
            f"{count}, found {actual}: {old}"
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
