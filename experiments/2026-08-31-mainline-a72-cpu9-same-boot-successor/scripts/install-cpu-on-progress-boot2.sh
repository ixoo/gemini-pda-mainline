#!/usr/bin/env bash

# Source-pin the guarded CPU9 installer to the exact CPU_ON progress candidate
# and require the retired CPUHP lock-repair image on inactive boot2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=2afab8c3c39b62c30b12ce80e48d6606db82c6b5643d84217c755defdb1f67b2
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/install-cpuhp-lock-repair-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source CPUHP lock-repair installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source CPUHP lock-repair installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-cpu9-cpu-on-progress.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("0904c5a293fea22f6993cb25ab8d775ed539d57c8fac7a7a6c50b67e2916f293",
     "d4eca4accded2692418b5972f0a51df79a8be1a0fc52b52f755258da86eb87fe", 1),
    ("2769dba806def496822adc6b65ab6634dcc4be53e4394224b96534d6add05429",
     "f84b7b40e0f8dc6bbfef1521103233506b9508307a473ae758067613b6bec436", 1),
    ("candidate-a72-cpu9-cpuhp-lock-56986d08",
     "candidate-a72-cpu9-cpu-on-progress-88cf13cb", 1),
    ("cpu9-cpuhp-lock-repair",
     "cpu9-cpu-on-progress", 2),
    ("CPU9 CPUHP lock repair",
     "CPU9 CPU_ON progress", 1),
    ('new_predecessor = "1cf367e021351f8a26643d827866786a879a8d6a3e68d8143cfce40bd1db52f7"',
     'new_predecessor = "0904c5a293fea22f6993cb25ab8d775ed539d57c8fac7a7a6c50b67e2916f293"', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU_ON progress installer derivation: expected "
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
