#!/usr/bin/env bash

# Source-pin the guarded prefix-control installer and specialize its exact
# live-GPT boot2 write/readback/shutdown workflow for the map candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=2cd4262573ff536fae37e8017aab85e90fb453e8191e35181687c16819f85ef7

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-21-mainline-manual-checkpoint-prefix-control/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived="$(mktemp "$script_dir/.derived-install-boot2-manual-map.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("ced1f56fc56833ce47b63a98205a373276f5d666007190ec0d3bd5adb98f3901",
     "dd513384c78ee8378e1e4bf515f89b99ca87ed6ed86c1d38ec37f8aadd693b5b", 1),
    ("bab777146bff18c83c698cfee6f957a806252a696720ae0f1f59d947c8886990",
     "af056a2eea1c410b68688b3d4b385d1b6f53d5e3fca3c12f66893eee6fccdbad", 1),
    ("candidate-manual-checkpoint-prefix-control-1d69e033",
     "candidate-manual-checkpoint-map-control-ecd021b2", 1),
    ("manual-checkpoint-prefix-control-deployment-",
     "manual-checkpoint-map-control-deployment-", 1),
    (r"\.gemini-manual-checkpoint-prefix-control\.",
     r"\.gemini-manual-checkpoint-map-control\.", 1),
    ("/home/gemini/.gemini-manual-checkpoint-prefix-control.XXXXXXXX",
     "/home/gemini/.gemini-manual-checkpoint-map-control.XXXXXXXX", 1),
    ("experiment=2026-08-21-mainline-manual-checkpoint-prefix-control",
     "experiment=2026-08-22-mainline-manual-checkpoint-map-control", 1),
    (".derived-install-boot2-manual-prefix.XXXXXXXX",
     ".derived-install-boot2-manual-map-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe map installer derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"

set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
