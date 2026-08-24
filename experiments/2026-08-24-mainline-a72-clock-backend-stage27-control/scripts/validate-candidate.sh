#!/usr/bin/env bash

# Source-pin the independent passed platform-state validator and specialize
# only its DT, layout, names, and exact candidate identities.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=25a83e9188658935fd8c586f18e7a1208e9082c520a6b1ca2b2007087ffddad6
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_validator="$repo_root/experiments/2026-08-24-mainline-a72-platform-state-stage27-control/scripts/validate-candidate.sh"
[[ -f "$source_validator" && ! -L "$source_validator" ]] || die 'source validator is missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source validator changed'

derived=$(mktemp "$script_dir/.derived-validate-a72-clock-stage27.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("57e11e4392edfdb9fa695ac3f87b82aad4043bc2a61b78646bf97344bae101fd", "5f5cd8b8af73cc1ae77887bb5761b8f1cc6b62e7028a6da24d6f9a3d0f22ab4f", 1),
    ("KERNEL_FIELD_SIZE = 4_831_882", "KERNEL_FIELD_SIZE = 4_832_094", 1),
    ("70ca589dbfc7649c38648a008e5197702295f396610ee2336fef5325f31b9546", "2ec5bd0751b71ba250a0b0e0e6d519d32375d6c445cc51a514d452fac51c995c", 1),
    ("662e86846e783cf29b13c388f9e88217fe7bd32933eef4f32df86e44def0b16b", "4c5276ecf3fe60d7df55fd1fe44235432fcd928d2174704e5928bae7d84056e4", 1),
    ("gemini-mt6797-a72-platform-state-stage27-control.boot.img", "gemini-mt6797-a72-clock-backend-stage27-control.boot.img", 1),
    ('b"gemini-a72min"', 'b"gemini-a72clk"', 1),
    ("validation=a72-platform-state-stage27-candidate", "validation=a72-clock-backend-stage27-candidate", 1),
    ('print("control_dtb=exact-stage27-plus-minimum-platform-state-contracts")', 'print("control_dtb=passed-stage27-platform-plus-read-free-clock-backend")', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe clock-backend validator derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
result=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$result"
