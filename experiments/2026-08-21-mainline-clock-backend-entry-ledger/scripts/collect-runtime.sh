#!/usr/bin/env bash

# Source-pin the proven USB/netcat collector and specialize it for the exact
# clock-backend entry candidate. Raw capture remains below ignored artifacts/.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a64b67249ad9a0ad55100b872bf54568797906c421da657d6404237682cbff93

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-21-mainline-protected-readback-runtime-observer/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] ||
	die 'source collector missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector identity changed'

derived="$(mktemp "$script_dir/.derived-collect-runtime-clock-entry.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    (
        "exact protected-readback probe",
        "exact clock-backend entry serviceability probe",
        1,
    ),
    (
        "190ad3e7b83b90e1517d946780240e135b7c99185d4b0dcd9016fceada5a592c",
        "6c66c5633d57235601d5a8900c674551c2c387e0dff3f4909b9a1c6111b53936",
        1,
    ),
    (
        "30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a",
        "444ffc4a3631e75d05e567f6304fdd1607695adbd1f3c8b5654714633e6278de",
        1,
    ),
    ("protected-readback-attempt-", "clock-backend-entry-attempt-", 3),
    (".protected-readback-runtime.", ".clock-backend-entry-runtime.", 1),
    ("__PROTECTED_READBACK_HOST_BEGIN__", "__CLOCK_BACKEND_ENTRY_HOST_BEGIN__", 1),
    ("__PROTECTED_READBACK_HOST_END__", "__CLOCK_BACKEND_ENTRY_HOST_END__", 1),
    ("protected_readback", "clock_entry_runtime", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe clock-entry collector derivation: expected {count} occurrences, "
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
