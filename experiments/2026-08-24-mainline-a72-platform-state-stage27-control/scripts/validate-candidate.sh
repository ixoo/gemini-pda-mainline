#!/usr/bin/env bash

# Source-pin the independent platform-state-only validator and retarget its
# exact DT, layout, names, and identities to the Stage-27 minimum derivative.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=67c38b09c69760ed9c3d31aed596a68491410a522965cac23208163d323ec116
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_validator="$repo_root/experiments/2026-08-24-mainline-a72-platform-state-only/scripts/validate-candidate.sh"
[[ -f "$source_validator" && ! -L "$source_validator" ]] || die 'source validator is missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source validator changed'

derived=$(mktemp "$script_dir/.derived-validate-a72-platform-stage27.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("8e806c5305b6a2808fab59d3a25739d39cd3196a3498a1af21136dd7221923e1", "57e11e4392edfdb9fa695ac3f87b82aad4043bc2a61b78646bf97344bae101fd", 1),
    ("KERNEL_FIELD_SIZE = 4_832_561", "KERNEL_FIELD_SIZE = 4_831_882", 1),
    ("f3210fb38f9d3d5a61e23d60dc7f9d65b05b0a08cd5ef15033786a4f1bc50aff", "70ca589dbfc7649c38648a008e5197702295f396610ee2336fef5325f31b9546", 1),
    ("012f7eac6884e65baab075ef286929f610a63f2ea065eba45865bd046492a23f", "662e86846e783cf29b13c388f9e88217fe7bd32933eef4f32df86e44def0b16b", 1),
    ("gemini-mt6797-a72-platform-only.boot.img", "gemini-mt6797-a72-platform-state-stage27-control.boot.img", 1),
    ('b"gemini-a72plat"', 'b"gemini-a72min"', 1),
    ("validation=a72-platform-state-only-candidate", "validation=a72-platform-state-stage27-candidate", 2),
    ('print("control_dtb=exact-current-platform-state-only")', 'print("control_dtb=exact-stage27-plus-minimum-platform-state-contracts")', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe Stage-27 provider validator derivation: expected {count}, found {actual}: {old}")
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
