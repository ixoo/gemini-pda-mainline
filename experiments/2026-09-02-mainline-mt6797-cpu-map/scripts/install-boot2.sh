#!/usr/bin/env bash

# Source-pin the guarded installer to the exact CPU-map candidate and require
# the runtime-proven completion-lock image as the boot2 predecessor.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=13b5c94d6b349aad13b6e9f7831eb5b57cacdfca9bc4149a3e618731f15b3e8a
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/scripts/install-completion-lock-repair-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source completion-lock installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source completion-lock installer changed'

derived=$(mktemp "$script_dir/.derived-install-mt6797-cpu-map.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e",
     "68ec1b7815cab7abae99cbdecabb2f0ba0dd1ddbf26943d652fcedf4d2b4e393", 1),
    ("aae595e7884559d6f298a15c2a7f447c3b1b9c9f97d973ac8bc50169107bd128",
     "0d99f36e5e6b10e1743fe88cc6f59f357805ab287d58f5c2b57be3aac7311742", 1),
    ("candidate-a72-cpu9-completion-lock-eba0aa21",
     "candidate-a72-cpu9-topology-7753563c", 1),
    ("cpu9-completion-lock-repair", "mt6797-cpu-map", 2),
    ("CPU9 completion-path lock repair", "MT6797 4+4+2 CPU map", 1),
    ('new_predecessor = "65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c"',
     'new_predecessor = "370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e"', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU-map installer derivation: expected {count}, "
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
