#!/usr/bin/env bash

# Source-pin the guarded live-control installer and retarget only its exact
# platform-state-only candidate, evidence names, and experiment identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=56db628cf2bd89bff35fdc2435ddc7aedf3681b9f90ee9cb4c67e67a0bf1bc90
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-24-mainline-a72-early-live-control/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-platform-only.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("Stage-27-DTB live-control candidate", "platform-state-only candidate", 2),
    (".derived-install-boot2-a72-early-live.XXXXXXXX", ".derived-install-boot2-a72-platform-only.XXXXXXXX", 2),
    ("exact A72 early live control", "exact A72 platform-state-only control", 1),
    ("070e0ff4b019dd35e91ba91413b9ae958cf5e71e3573ed81bc9dd7d1cf3cc4ef", "012f7eac6884e65baab075ef286929f610a63f2ea065eba45865bd046492a23f", 1),
    ("0751ffc0200f7062590e825feb8892537f024641ffea7d647dd6375f5206bd05", "07f89b083539be006efe1e8407694153daa00b581b95394e40844bd71d54c7da", 1),
    ("candidate-a72-early-live-control-32ff42b3", "candidate-a72-platform-state-only-f3210fb3", 1),
    ("a72-early-live-control-deployment-", "a72-platform-state-only-deployment-", 1),
    (r"\.gemini-a72-early-live-control\.", r"\.gemini-a72-platform-state-only\.", 1),
    ("/home/gemini/.gemini-a72-early-live-control.XXXXXXXX", "/home/gemini/.gemini-a72-platform-state-only.XXXXXXXX", 1),
    ("experiment=2026-08-24-mainline-a72-early-live-control", "experiment=2026-08-24-mainline-a72-platform-state-only", 1),
    ("unsafe live-control installer derivation", "unsafe platform-state-only installer derivation", 1),
    ("live A72 early-live-control preflight failed", "live A72 platform-state-only preflight failed", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe platform-only installer derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
