#!/usr/bin/env bash

# Source-pin the guarded platform-state installer and retarget only its exact
# Stage-27 minimum-contract candidate. The retained-record gate is unchanged.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=63d68dd576d7aaf7526f6ddaca9f28ae662d5dc48b4636ce57167c6c446a4918
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-24-mainline-a72-platform-state-only/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-platform-stage27.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("012f7eac6884e65baab075ef286929f610a63f2ea065eba45865bd046492a23f", "662e86846e783cf29b13c388f9e88217fe7bd32933eef4f32df86e44def0b16b", 1),
    ("07f89b083539be006efe1e8407694153daa00b581b95394e40844bd71d54c7da", "ed0eccbe2250cbb80aaf57f28b1b30f47fc0dde8b305eb94b256586ec2d78ba4", 1),
    ("candidate-a72-platform-state-only-f3210fb3", "candidate-a72-platform-state-stage27-70ca589d", 1),
    ("a72-platform-state-only-deployment-", "a72-platform-state-stage27-deployment-", 1),
    (r"\.gemini-a72-platform-state-only\.", r"\.gemini-a72-platform-state-stage27\.", 1),
    ("/home/gemini/.gemini-a72-platform-state-only.XXXXXXXX", "/home/gemini/.gemini-a72-platform-state-stage27.XXXXXXXX", 1),
    ("experiment=2026-08-24-mainline-a72-platform-state-only", "experiment=2026-08-24-mainline-a72-platform-state-stage27-control", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe Stage-27 provider installer derivation: expected {count}, found {actual}: {old}")
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
