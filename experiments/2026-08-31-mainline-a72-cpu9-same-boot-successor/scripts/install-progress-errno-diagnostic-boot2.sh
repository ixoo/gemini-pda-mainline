#!/usr/bin/env bash

# Source-pin the guarded CPU9 installer to the exact progress errno
# diagnostic candidate and require the retired mapping-fix image on boot2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=b779bd470eaf642b07bd33eec09d444afae2b93e7e4a873c8f4229a9a89f5ec1
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/install-mapping-fix-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source mapping-fix installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source mapping-fix installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-cpu9-progress-errno.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("c531a9e05ae6f2d51211d73fb487efbaef235cfede195ba135e819bd4f2575c0",
     "4bf74874cbfe900576ae891d32b5e8996d5c66ed599b6fca09c7310e87cdeae8", 1),
    ("5bae6aa70b27390b1c18a8310648afe7fa67796a7bed51eabb2b438abae5751a",
     "3e1ca9603abb8e3f5171a6fa832da59b4ec1546a9ef5c53b89af969246940081", 1),
    ("candidate-a72-cpu9-mapping-fix-a7290cdb",
     "candidate-a72-cpu9-progress-errno-32d304dc", 1),
    ("cpu9-progress-reader-mapping-fix",
     "cpu9-progress-errno-diagnostic", 1),
    ("CPU9 progress reader-mapping repair",
     "CPU9 progress errno diagnostic", 1),
    ('new_predecessor = "ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72"',
     'new_predecessor = "c531a9e05ae6f2d51211d73fb487efbaef235cfede195ba135e819bd4f2575c0"', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 progress errno installer derivation: expected "
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
