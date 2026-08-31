#!/usr/bin/env bash

# Source-pin the live-GPT installer, retarget it to the exact r0p1 repair
# candidate, and require the exact post-capabilities predecessor.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=00bedb309ad28ebd1f87749c776f53711c49d5f4e8f34157d3864d4f6a358220
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-post-capabilities-checkpoints/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-a72-r0p1-expected-pair-repair.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630",
     "b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d", 1),
    ("6d0bf75b55ef981a915ba0b9a8d305d5713476acc4fc2ee95e4201f234b2253f",
     "9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630", 1),
    ("115719788a95923b3b41f7f9d2aeb4b11acf3289147f01969b3a43032429cefe",
     "1af85a3dcf598e1ff2ca7beb5ea668e30f0dbdd9f2f627f5229c3abb3927968f", 1),
    ("candidate-a72-post-capabilities-checkpoints-cb7c886e",
     "candidate-a72-r0p1-expected-pair-repair-6083935b", 1),
    ("post-capabilities-checkpoints", "r0p1-expected-pair-repair", 2),
    ("post-capabilities checkpoint", "r0p1 expected-pair repair", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe r0p1 installer derivation: expected {count}, "
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
