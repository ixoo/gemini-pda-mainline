#!/usr/bin/env bash

# Source-pin the guarded CPU9 installer to the exact completion-path
# lock-repair candidate and require the retired membership-lock image on boot2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=cb65de4d9fe304f49611fbf1b6760053b90e64a127e2562f4317806a8ca77dc8
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/install-membership-lock-repair-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source membership-lock installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source membership-lock installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-cpu9-completion-lock-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c",
     "370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e", 1),
    ("19b225ca106c2e480bf604de37d18ceffdb04a37d67df139f508a86117033b76",
     "aae595e7884559d6f298a15c2a7f447c3b1b9c9f97d973ac8bc50169107bd128", 1),
    ("candidate-a72-cpu9-membership-lock-44aacf58",
     "candidate-a72-cpu9-completion-lock-eba0aa21", 1),
    ("cpu9-membership-lock-repair",
     "cpu9-completion-lock-repair", 2),
    ("CPU9 membership-begin lock repair",
     "CPU9 completion-path lock repair", 1),
    ('new_predecessor = "d4eca4accded2692418b5972f0a51df79a8be1a0fc52b52f755258da86eb87fe"',
     'new_predecessor = "65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c"', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe completion-lock installer derivation: expected "
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
