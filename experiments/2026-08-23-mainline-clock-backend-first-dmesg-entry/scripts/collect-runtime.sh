#!/usr/bin/env bash

# Source-pin the proven live/recovery collector, substitute the exact
# clock-entry oracle, and recover both retained records after changed-ID Gemian.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a5f4583de862f4a3e1f327cee1eeabb1ae1aea57fcdecf0515eedb65f6e35ebd

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-22-mainline-first-dmesg-raw-write-qualification/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] ||
	die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector identity changed'

derived="$(mktemp "$script_dir/.derived-clock-entry-collector.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
old_record = (
    'record_1_b64="$(dd if=/dev/mem bs=1 skip=$((0x44410000)) count=4096 status=none |\n'
    "\tbase64 | tr -d '\\n')\"\n"
)
new_record = old_record + (
    'record_2_b64="$(dd if=/dev/mem bs=1 skip=$((0x44411000)) count=4096 status=none |\n'
    "\tbase64 | tr -d '\\n')\"\n"
)
old_output = (
    "printf 'record_2_header=%s\\nramoops_registration_lines=%s\\n' \\\n"
    '\t"$record_2_header" "$ramoops_registration_lines"\n'
)
new_output = (
    "printf 'record_2_size=4096\\nrecord_2_header=%s\\nrecord_2_b64=%s\\n' \\\n"
    '\t"$record_2_header" "$record_2_b64"\n'
    "printf 'ramoops_registration_lines=%s\\n' \"$ramoops_registration_lines\"\n"
)
replacements = (
    (
        "# Source-pin the proven USB observer for one exact first-dmesg live result,\n",
        "# Source-pin the proven USB observer for one exact clock-entry live result,\n",
        1,
    ),
    (
        "99af34ba3f9bd33c6d56f105ca3a7eade0c6d4250b012bd3bb8bc303296e03a7",
        "e2a595f41846a1d89836ae252879bfdf0ae19308dc0bce234b4eed511290dbdc",
        2,
    ),
    (
        "78a6bfc99a1e597fe5c8d0381e1d3ece5c5648f96a28fa5842f64dd0a0c0befd",
        "dd6baafed2a1902c470caf149ee31c92a03407e85b13fe974429f09af95af0dc",
        2,
    ),
    (
        "c87a0e0a4ed969e0c2ea5cac3fc602fb4d6dd9641fa65984c6ab912be7d48ac3",
        "caebd9f33cff7ba7c7ac71575b094fc22a193e59d3f4c52b707f4bd27054cc1b",
        1,
    ),
    (
        "b96ec109b3f020fdaf0cdc6ca1733d012051e6607b5520a11d32a6441f569e96",
        "40b7c663b835bcf4c48f4149f14aa416343e3e322ab78a0aa38448afff9455b4",
        2,
    ),
    ("first-dmesg-raw-write-attempt-1", "clock-entry-first-dmesg-attempt-1", 3),
    (".derived-first-dmesg-collector.XXXXXXXX", ".derived-clock-entry-collector.XXXXXXXX", 1),
    (
        "# Pre-arm one bounded USB/netcat observation of the exact first-dmesg\\n",
        "# Pre-arm one bounded USB/netcat observation of the exact clock-entry\\n",
        1,
    ),
    (
        '("current-service", "first-dmesg-raw-write", 1)',
        '("current-service", "clock-backend-first-dmesg", 1)',
        1,
    ),
    (
        "__FIRST_DMESG_RAW_WRITE_RUNTIME_BEGIN__",
        "__CLOCK_BACKEND_FIRST_DMESG_RUNTIME_BEGIN__",
        1,
    ),
    (
        "__FIRST_DMESG_RAW_WRITE_RUNTIME_END__",
        "__CLOCK_BACKEND_FIRST_DMESG_RUNTIME_END__",
        1,
    ),
    (
        "first-dmesg-raw-write-live-pass",
        "clock-backend-first-dmesg-live-pass",
        2,
    ),
    ("unsafe first-dmesg collector derivation", "unsafe clock-entry collector derivation", 1),
    (old_record, new_record, 1),
    (old_output, new_output, 1),
    (
        "first-dmesg-cross-version-enumeration-pass|first-dmesg-direct-retention-only",
        "clock-entry-cross-version-enumeration-pass|clock-entry-direct-retention-only",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe clock-entry wrapper derivation: expected {count}, found {actual}: {old}"
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
