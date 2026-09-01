#!/usr/bin/env bash

# Source-pin the guarded live-GPT installer for the exact CPU9 controller
# candidate and require the repeatable CPU8 predecessor on boot2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a5b82cb085d44889db25e9911f13af8d66ab8308ff259f749819d6476294661b
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-expected-pair-model-contract-repair/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-cpu9-controller.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee",
     "fb473d2f3240137ec05f901163bb0374ef3015b66c42558eca6f1085cbd83468", 1),
    ("25ef693ecaa6b1bf214d2f5948f146e1d95674cc8108562b7a48b1d687208474",
     "f6a1ea0b96243207a1d8b6742fae2ecbfb87dda210320b5e214025a596db895a", 1),
    ("candidate-a72-expected-pair-model-contract-repair-c66c24c6",
     "candidate-a72-cpu9-controller-dd4b9358", 1),
    ("expected-pair-model-contract-repair", "cpu9-same-boot-successor", 1),
    ("expected-pair model-contract repair", "CPU9 same-boot successor", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 installer derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
predecessor = "b78ac044977749af97864676cc64b34224ce348ff8d9c14b41a67f21a453e8c1"
new_predecessor = "42c984ee72fe93e7f6157598dd479a9348a03d733df7948e4e4c14aa356c78ee"
if text.count(predecessor) != 2:
    raise SystemExit("unsafe CPU9 installer derivation: predecessor chain changed")
offset = text.rfind(predecessor)
text = text[:offset] + new_predecessor + text[offset + len(predecessor):]
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
