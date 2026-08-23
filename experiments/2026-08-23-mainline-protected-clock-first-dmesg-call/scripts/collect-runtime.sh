#!/usr/bin/env bash

# Source-pin the proven two-record collector, substitute the exact one-read
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

derived="$(mktemp "$script_dir/.derived-protected-clock-collector.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("# clock-entry oracle, and recover both retained records after changed-ID Gemian.",
     "# one-read oracle, and recover both retained records after changed-ID Gemian.", 1),
    ("e2a595f41846a1d89836ae252879bfdf0ae19308dc0bce234b4eed511290dbdc", "641492bb60444c0b38c72c1b683b8b3dcff970eab2825dd664d769f5f139e59b", 1),
    ("dd6baafed2a1902c470caf149ee31c92a03407e85b13fe974429f09af95af0dc", "69f8697b26f92303c161c97e26aa1fdd75e062d48ac7955852578b7137949bd2", 1),
    ("caebd9f33cff7ba7c7ac71575b094fc22a193e59d3f4c52b707f4bd27054cc1b", "8f1b3d6a5fc9f18d7206a1c0cde233341cb55b22b40ddf4c18abf8685a27291d", 1),
    ("40b7c663b835bcf4c48f4149f14aa416343e3e322ab78a0aa38448afff9455b4", "3892e776c183027851d73bec8bf938732c43ddad030a80ddee42240537ba35f6", 1),
    ("clock-entry-first-dmesg-attempt-1", "protected-clock-first-dmesg-attempt-1", 1),
    (".derived-clock-entry-collector.XXXXXXXX", ".derived-protected-clock-collector.XXXXXXXX", 2),
    ("exact clock-entry live result", "exact one-read protected-clock live result", 1),
    (r"exact clock-entry\\n", r"exact one-read protected-clock\\n", 1),
    ('("current-service", "clock-backend-first-dmesg", 1)',
     '("current-service", "protected-clock-first-dmesg", 1)', 1),
    ("__CLOCK_BACKEND_FIRST_DMESG_RUNTIME_BEGIN__", "__PROTECTED_CLOCK_FIRST_DMESG_RUNTIME_BEGIN__", 1),
    ("__CLOCK_BACKEND_FIRST_DMESG_RUNTIME_END__", "__PROTECTED_CLOCK_FIRST_DMESG_RUNTIME_END__", 1),
    ("clock-backend-first-dmesg-live-pass", "protected-clock-first-dmesg-live-pass", 1),
    ("clock-entry-cross-version-enumeration-pass|clock-entry-direct-retention-only",
     "protected-clock-cross-version-enumeration-pass|protected-clock-direct-retention-only", 1),
    ("unsafe clock-entry", "unsafe protected-clock", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe protected-clock collector derivation: expected {count}, "
            f"found {actual}: {old}"
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
