#!/usr/bin/env bash

# Source-pin the proven two-record collector, substitute the exact coexistence
# oracle, and recover both retained records after changed-ID Gemian.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=e3167e0b740962dd9cb126f48f483f2698f02012f082abffcdb9e5abdf858aa8

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-23-mainline-clock-backend-first-dmesg-entry/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] ||
	die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector identity changed'

derived="$(mktemp "$script_dir/.derived-clock-cspm-collector.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("e2a595f41846a1d89836ae252879bfdf0ae19308dc0bce234b4eed511290dbdc", "c7b3c623a4324748cca0f701cc64226eb5c1f78186dcb8a8316487968b819a1b", 1),
    ("dd6baafed2a1902c470caf149ee31c92a03407e85b13fe974429f09af95af0dc", "b959fbbb270da33d893ed5e6ba7e1e1e4ab6eb9221345ddfb111b63474c8da5f", 1),
    ("caebd9f33cff7ba7c7ac71575b094fc22a193e59d3f4c52b707f4bd27054cc1b", "2d964800011e738f02d8699f375183d20ce1c936ee406d55683b82413f7e8d00", 1),
    ("40b7c663b835bcf4c48f4149f14aa416343e3e322ab78a0aa38448afff9455b4", "ae4010449e72ed4d02643616073e8d74f7cad25adb4afb5db69030d39eb324e7", 1),
    ("clock-entry-first-dmesg-attempt-1", "clock-cspm-coexistence-attempt-1", 1),
    (".derived-clock-entry-collector.XXXXXXXX", ".derived-clock-cspm-collector.XXXXXXXX", 2),
    ('("current-service", "clock-backend-first-dmesg", 1)', '("current-service", "clock-backend-cspm-coexistence", 1)', 1),
    ("__CLOCK_BACKEND_FIRST_DMESG_RUNTIME_BEGIN__", "__CLOCK_BACKEND_CSPM_COEXISTENCE_RUNTIME_BEGIN__", 1),
    ("__CLOCK_BACKEND_FIRST_DMESG_RUNTIME_END__", "__CLOCK_BACKEND_CSPM_COEXISTENCE_RUNTIME_END__", 1),
    ("clock-backend-first-dmesg-live-pass", "clock-backend-cspm-coexistence-live-pass", 1),
    ("clock-entry-cross-version-enumeration-pass", "clock-cspm-cross-version-enumeration-pass", 1),
    ("clock-entry-direct-retention-only", "clock-cspm-direct-retention-only", 1),
    ("unsafe clock-entry wrapper derivation", "unsafe clock/CSPM wrapper derivation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe coexistence collector derivation: expected {count}, found {actual}: {old}"
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
