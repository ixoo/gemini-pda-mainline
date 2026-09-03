#!/usr/bin/env bash

# Source-pin the live-GPT installer for the exact P30E-rearm candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=675318a4545eb3cdb41218d3890b5bc54e84905977ede222031f6791017c0b67
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/scripts/install-physical-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source physical-hotplug installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-p30e-rearm.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("44e1b42c2dbec86c5da4a3f6cdc0ac1a06d47405b953bdc5401d01facf1d7d09",
     "7ffd60d082633c21ae65fa3c0bb4b2dcbd69c0abfa04d6212788f7b7ae4daf9d", 1),
    ("645a9737be18640f8ecf10235043a974fc128edcd66d3982b8561e30b3844851",
     "c8e73b255162e8fbe3cfe9f5c6e600b705d6c63333b8a4451c47c4492b85edd8", 1),
    ("candidate-a72-hotplug-physical-f411b55d",
     "candidate-a72-p30e-rearm-c1cf7d7a", 1),
    ("a72-physical-hotplug", "a72-p30e-rearm", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E-rearm installer derivation: expected {count}, "
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
