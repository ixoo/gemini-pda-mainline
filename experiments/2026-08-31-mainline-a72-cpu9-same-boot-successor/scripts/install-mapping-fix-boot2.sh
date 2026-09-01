#!/usr/bin/env bash

# Source-pin the guarded CPU9 installer to the exact progress reader-mapping
# repair candidate and require the retired progress image on boot2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=fe736283cc5b6c582d5bd0a56545c5b6751d74f265862623d2fecb7aa1486be3
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/install-progress-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source progress installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source progress installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-cpu9-mapping-fix.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72",
     "c531a9e05ae6f2d51211d73fb487efbaef235cfede195ba135e819bd4f2575c0", 1),
    ("e398c2b9156c31f02cb126be40204608b17f9df8a44a0f2268e05545d40448e2",
     "5bae6aa70b27390b1c18a8310648afe7fa67796a7bed51eabb2b438abae5751a", 1),
    ("candidate-a72-cpu9-progress-85d3b591",
     "candidate-a72-cpu9-mapping-fix-a7290cdb", 1),
    ("cpu9-progress-ledger", "cpu9-progress-reader-mapping-fix", 1),
    ("CPU9 progress-ledger diagnostic",
     "CPU9 progress reader-mapping repair", 1),
    ('new_predecessor = "118096351905936e8f7c1fe9b186dadb191808bc94092cbd7a67a0b936a00562"',
     'new_predecessor = "ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72"', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 mapping-fix installer derivation: expected {count}, "
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
