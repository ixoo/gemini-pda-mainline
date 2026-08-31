#!/usr/bin/env bash

# Source-pin the read-only retained-record collector and retarget only the
# selector-mask repair candidate, classifier location, and evidence namespace.
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
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-selector-mask-recovery.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        "60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1",
        "cd36efdfbf1e3d7da00cf5a36ded07abfaf2a640d1f731aaad00feef01549743",
        1,
    ),
    (
        "ff9ece359c3b5afd8852d2e4b09e14abc339dd32950219c001f54119a442d112",
        "382645a8f2883dbdfad80e199504454a37db395849329a59dc57c729cda0b639",
        1,
    ),
    (
        "2026-08-28-mainline-a72-admission-durable-candidate",
        "2026-08-31-mainline-a72-sram-selector-mask-contract-repair",
        1,
    ),
    (
        ".a72-admission-recovery.XXXXXXXX",
        ".a72-selector-mask-recovery.XXXXXXXX",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe selector-mask recovery derivation: expected "
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
