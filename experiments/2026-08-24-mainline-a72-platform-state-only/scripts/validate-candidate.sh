#!/usr/bin/env bash

# Source-pin the exact current-kernel live-control validator and specialize its
# DTB, layout, names, and candidate identities for platform-state only.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=f7d70de327696b940646aa1e2e5eb2fe7798de99ae2562704cf9d0fefe3c1d70
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_validator="$repo_root/experiments/2026-08-24-mainline-a72-early-live-control/scripts/validate-candidate.sh"
[[ -f "$source_validator" && ! -L "$source_validator" ]] || die 'source validator is missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source validator changed'

derived=$(mktemp "$script_dir/.derived-validate-a72-platform-only.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
gzip_tuple = '    ("539f83bf4e6f31e21edacde26399ea285c1e87cdf4df25fb2896d364822a89fe", "00992be8c2ccb222c42eecfd92c43b81305f12d756cc2e2a7fc533299e2ce293", 1),'
inserted = gzip_tuple + '\n    ("7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806", "8e806c5305b6a2808fab59d3a25739d39cd3196a3498a1af21136dd7221923e1", 1),'
replacements = (
    (gzip_tuple, inserted, 1),
    ("KERNEL_FIELD_SIZE = 4_831_601", "KERNEL_FIELD_SIZE = 4_832_561", 1),
    ("32ff42b3e8ba07e5b0267b521118f906aa27bd737613ae76a119961d3acc9e0d", "f3210fb38f9d3d5a61e23d60dc7f9d65b05b0a08cd5ef15033786a4f1bc50aff", 1),
    ("070e0ff4b019dd35e91ba91413b9ae958cf5e71e3573ed81bc9dd7d1cf3cc4ef", "012f7eac6884e65baab075ef286929f610a63f2ea065eba45865bd046492a23f", 1),
    ("gemini-mt6797-a72-early-live-control.boot.img", "gemini-mt6797-a72-platform-only.boot.img", 1),
    ('b"gemini-a72live"', 'b"gemini-a72plat"', 1),
    ("validation=a72-early-live-control-candidate", "validation=a72-platform-state-only-candidate", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe platform-only validator derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
needle = '    ("validation=lk-handoff-dtb-control-candidate", "validation=a72-platform-state-only-candidate", 1),'
addition = needle + '\n    (\'print("control_dtb=exact-runtime-proven-stage27")\', \'print("control_dtb=exact-current-platform-state-only")\', 1),'
if text.count(needle) != 1:
    raise SystemExit("unsafe platform-only validator output insertion")
text = text.replace(needle, addition)
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
