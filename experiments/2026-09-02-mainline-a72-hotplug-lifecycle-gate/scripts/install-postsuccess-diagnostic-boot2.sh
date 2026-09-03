#!/usr/bin/env bash

# Source-pin the live-GPT installer for the post-success diagnostic candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=bec944820075c4e66e758587929f5de71e05b572d79f46e0baadf5628a2862b5
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/scripts/install-p30e-rearm-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source P30E-rearm installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-postsuccess-diagnostic.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("7ffd60d082633c21ae65fa3c0bb4b2dcbd69c0abfa04d6212788f7b7ae4daf9d",
     "fe333d46ece958c7015a034c8cc8d2afd5ffd9b334dff47ff4bb33295d625671", 1),
    ("c8e73b255162e8fbe3cfe9f5c6e600b705d6c63333b8a4451c47c4492b85edd8",
     "09ab1511459efd84c0a01d994cc237ea1957fa94ec25550ff386c7b8791537a8", 1),
    ("candidate-a72-p30e-rearm-c1cf7d7a",
     "candidate-a72-postsuccess-diagnostic-fd015493", 1),
    ("a72-p30e-rearm", "a72-postsuccess-diagnostic", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe post-success installer derivation: expected {count}, "
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
