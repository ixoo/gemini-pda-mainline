#!/usr/bin/env bash

# Source-pin the durable admission recovery collector for the exact ATAG
# prerequisite candidate after its one permitted live trigger is terminal.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=e46d85727064f332b2a418878dd2de0de19c42907cb8a4fc1e9c2cda3f917f9c
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-28-mainline-a72-admission-durable-candidate/scripts/collect-recovery.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] ||
	die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-postterminal-recovery.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1",
     "fd611a4ca87fd1645e2fa75b3927d56e9e7eac89f3d84712e5555a3aab8f4cf0", 1),
    ('classifier="$script_dir/classify-recovery.py"',
     'classifier="$repo_root/experiments/2026-08-28-mainline-a72-admission-durable-candidate/scripts/classify-recovery.py"', 1),
    ("experiment=2026-08-28-mainline-a72-admission-durable-candidate",
     "experiment=2026-08-28-mainline-a72-admission-atag-one-shot", 1),
    (".a72-admission-recovery.XXXXXXXX",
     ".a72-admission-atag-postterminal-recovery.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe postterminal recovery derivation: expected {count}, "
            f"found {actual}: {old}"
        )
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
