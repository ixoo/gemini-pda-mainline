#!/usr/bin/env bash

# Source-pin the proven serviceability transform and retarget it to the exact
# full admission DT while preserving the already-enabled A72 backends.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=550527d86331bd5eb037ba60e787dc7f132a136f005c89e8864c58721ed9dc7d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"; done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P); repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-21-mainline-current-tree-serviceability-control/scripts/build-serviceability-dtb.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'
derived=$(mktemp "$script_dir/.derived-admission-serviceability-dtb.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }; trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("dad6997c565d10dcacab23dea46166ac45f6594da2aab697b105b3fb2dcc474e", "1bd6ce2ded2e1186503cb0d9d00107964ec27abc48062b9210e1935d38d60509", 1),
    ("b638674b9be209219d51b7dd02538f7a0bc8b402bab7336188cb95011cd912dd", "1478f2c8817b1289958e8918545e54493a60c67bcc399fe0daeb82b2cf5d046c", 1),
    ('"$CLOCK_BACKEND" status)" == disabled', '"$CLOCK_BACKEND" status)" == okay', 2),
    ('"$BIGIDVFSP_BACKEND" status)" == disabled', '"$BIGIDVFSP_BACKEND" status)" == okay', 2),
    ("clock_backend_status=disabled", "clock_backend_status=okay", 1),
    ("bigidvfs_backend_status=disabled", "bigidvfs_backend_status=okay", 1),
    ("CPU8_CPU9_admission=closed", "automatic_CPU8_admission=closed", 1),
    ("validation=current-tree-serviceability-dtb", "validation=admission-serviceability-restoration-dtb", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe serviceability-DTB derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e; /bin/bash "$derived" "$@"; rc=$?; set -e
cleanup; trap - EXIT HUP INT TERM; exit "$rc"
