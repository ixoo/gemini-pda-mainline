#!/usr/bin/env bash

# Source-pin the strict call-ledger USB classifier and specialize only the
# exact probe/gate candidate and kernel-release identities.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=2d760b225ac950b2f202ba0f0f31304eb75c46eb4574c7e79b2938c2ae59ff94

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_validator="$repo_root/experiments/2026-08-21-mainline-protected-readback-call-ledger/scripts/validate-runtime.sh"
[[ -f "$source_validator" && ! -L "$source_validator" ]] ||
	die 'source validator missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator identity changed'

derived="$(mktemp "$script_dir/.derived-validate-runtime-probe-gate.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    (
        "Classify one exact protected-readback call-ledger netcat capture.",
        "Classify one exact protected-readback probe/gate-ledger netcat capture.",
        1,
    ),
    (
        "3ce494c971c24c9edab73aac592d0ba8dd0bbd25f06051245f7846f95d0c715a",
        "6cb729efacea914b993221f0f85a1ab7e67eb6bca915802a8236bb31edab2e62",
        1,
    ),
    (
        "7.1.3-gemini-protected-readback-ledger",
        "7.1.3-gemini-protected-readback-probe-gate",
        1,
    ),
    (
        "claim_scope=one-shot-call-ledger-protected-readback-records-only",
        "claim_scope=one-shot-probe-gate-protected-readback-records-only",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe runtime-validator derivation: expected {count} occurrences, "
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
