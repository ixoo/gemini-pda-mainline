#!/usr/bin/env bash

# Source-pin the live-GPT installer, retarget it to the exact post-capabilities
# candidate, and require the exact checkpoint-5 predecessor.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=beef5262766b61de10e8544dc89b526cd3cdbe78870abe0f281cb424c7ae2666
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-p30e-ready-identity-repair/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-post-capabilities-checkpoints.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("459bcf66fe807d9babfeefec7ea9b6e922edfaaa078fcbd288c7639048b31d16",
     "9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630", 2),
    ("a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453",
     "6d0bf75b55ef981a915ba0b9a8d305d5713476acc4fc2ee95e4201f234b2253f", 1),
    ("c98b9e676236d59339ff7939f8cd723310c04474ffda924296f07879177f90e2",
     "115719788a95923b3b41f7f9d2aeb4b11acf3289147f01969b3a43032429cefe", 1),
    ("candidate-a72-p30e-ready-identity-repair-417d911f",
     "candidate-a72-post-capabilities-checkpoints-cb7c886e", 1),
    ("p30e-ready-identity-repair", "post-capabilities-checkpoints", 4),
    ("P30E READY-identity", "post-capabilities checkpoint", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe post-capabilities installer derivation: expected "
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
