#!/usr/bin/env bash

# Source-pin the guarded CPU9 installer to the exact membership-begin
# lock-repair candidate and require the retired CPU_ON progress image on boot2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=688118052d783e998173f5d38626231f22e22dcd7a5edbfd1ded87d7f8a2e4ec
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/install-cpu-on-progress-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source CPU_ON progress installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source CPU_ON progress installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-cpu9-membership-lock-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("d4eca4accded2692418b5972f0a51df79a8be1a0fc52b52f755258da86eb87fe",
     "65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c", 1),
    ("f84b7b40e0f8dc6bbfef1521103233506b9508307a473ae758067613b6bec436",
     "19b225ca106c2e480bf604de37d18ceffdb04a37d67df139f508a86117033b76", 1),
    ("candidate-a72-cpu9-cpu-on-progress-88cf13cb",
     "candidate-a72-cpu9-membership-lock-44aacf58", 1),
    ("cpu9-cpu-on-progress",
     "cpu9-membership-lock-repair", 2),
    ("CPU9 CPU_ON progress",
     "CPU9 membership-begin lock repair", 1),
    ('new_predecessor = "0904c5a293fea22f6993cb25ab8d775ed539d57c8fac7a7a6c50b67e2916f293"',
     'new_predecessor = "d4eca4accded2692418b5972f0a51df79a8be1a0fc52b52f755258da86eb87fe"', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe membership-lock installer derivation: expected "
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
