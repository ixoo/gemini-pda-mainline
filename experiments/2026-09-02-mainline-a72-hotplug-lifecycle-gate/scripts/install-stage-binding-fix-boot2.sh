#!/usr/bin/env bash

# Source-pin the live-GPT installer for the symbolic stage-binding-fix candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=280f81125b90f9e39adf71f42a6ea9492445997287a4008a6bdb6d92d3236fca
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/scripts/install-postsuccess-diagnostic-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source post-success diagnostic installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-stage-binding-fix.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("fe333d46ece958c7015a034c8cc8d2afd5ffd9b334dff47ff4bb33295d625671",
     "c84aea47c6dc4a9745687536b3a99c4e434af5826b10a5a83bae3f8171a81271", 1),
    ("09ab1511459efd84c0a01d994cc237ea1957fa94ec25550ff386c7b8791537a8",
     "0a4434843507ef43c7c2e0b16ca2b453e758d32d8fd198c2c757ee1af128f820", 1),
    ("candidate-a72-postsuccess-diagnostic-fd015493",
     "candidate-a72-stage-binding-fix-09c4f0b7", 1),
    ("a72-postsuccess-diagnostic", "a72-stage-binding-fix", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe stage-binding installer derivation: expected {count}, "
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
