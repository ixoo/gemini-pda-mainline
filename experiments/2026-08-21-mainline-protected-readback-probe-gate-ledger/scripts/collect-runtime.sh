#!/usr/bin/env bash

# Source-pin the proven call-ledger USB/netcat collector and specialize it for
# the exact probe/gate candidate. Raw capture remains below ignored artifacts/.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=2e37a83fa8bec300bf47e4e4233d97bf825271be97e5376f86829eb6ce62ffc1

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-21-mainline-protected-readback-call-ledger/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] ||
	die 'source collector missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector identity changed'

derived="$(mktemp "$script_dir/.derived-collect-runtime-probe-gate.XXXXXXXX")"
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
        "exact protected-readback call-ledger probe",
        "exact protected-readback probe/gate-ledger probe",
        1,
    ),
    (
        "4e7d26aaf2be80b12b7cca84d2946f3bbaf420b5e1700ad7e4ecae97f415ca94",
        "5e5be25b55b9c7c986e0f54ca0016d9bf98f13a72a839d89d15f62faee2a9f6b",
        1,
    ),
    (
        "3ce494c971c24c9edab73aac592d0ba8dd0bbd25f06051245f7846f95d0c715a",
        "6cb729efacea914b993221f0f85a1ab7e67eb6bca915802a8236bb31edab2e62",
        1,
    ),
    (
        "protected-readback-call-ledger-attempt-",
        "protected-readback-probe-gate-attempt-",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe runtime-collector derivation: expected {count} occurrences, "
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
