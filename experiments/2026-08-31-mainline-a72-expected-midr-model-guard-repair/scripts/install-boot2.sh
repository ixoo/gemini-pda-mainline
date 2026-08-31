#!/usr/bin/env bash

# Source-pin the live-GPT installer for the exact model-guard candidate and
# require the exact r0p1 predecessor already installed on boot2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=12912dbe8a5b12b713d3f115555c53854e19de96afa65826e71b2a37f8a76da8
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-31-mainline-a72-r0p1-expected-pair-repair/scripts/install-boot2.sh"
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source installer changed'
derived=$(mktemp "$script_dir/.derived-install-a72-expected-midr-model-guard.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ('("9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630",\n'
     '     "b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d", 1),',
     '("9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630",\n'
     '     "5e686d2c7e9f59c7345ec3c50048a01371ab1938ceb8753b599d0afdd3084d69", 1),', 1),
    ('("6d0bf75b55ef981a915ba0b9a8d305d5713476acc4fc2ee95e4201f234b2253f",\n'
     '     "9f7ff84912ff7b8f4f95661751972d32f6dfbfd1c3315e00145960bbcab2d630", 1),',
     '("6d0bf75b55ef981a915ba0b9a8d305d5713476acc4fc2ee95e4201f234b2253f",\n'
     '     "b5328f6a422627d2ea9bdfb12cbfc1acb6024a25a7c0f3bc911520e50d23530d", 1),', 1),
    ("1af85a3dcf598e1ff2ca7beb5ea668e30f0dbdd9f2f627f5229c3abb3927968f",
     "ee5eefe99d8940598a0a4218a34b16a460fab684daf580d4ae8b5f0813d5c22b", 1),
    ("candidate-a72-r0p1-expected-pair-repair-6083935b",
     "candidate-a72-expected-midr-model-guard-repair-bf7ebec8", 1),
    ("r0p1-expected-pair-repair", "expected-midr-model-guard-repair", 2),
    ("r0p1 expected-pair repair", "expected-MIDR model-guard repair", 1),
)
for old, new, count in replacements:
    if text.count(old) != count:
        raise SystemExit(f"unsafe model-guard installer derivation: {old}")
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
