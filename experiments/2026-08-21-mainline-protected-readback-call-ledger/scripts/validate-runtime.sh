#!/usr/bin/env bash

# Source-pin the strict predecessor USB classifier and specialize only the
# exact candidate and kernel-release identities.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=18419fe6ebf625a64be3a892ff5c9d5af5248e5a4cc0478ca04ebff2066169b7

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_validator="$repo_root/experiments/2026-08-21-mainline-protected-readback-runtime-observer/scripts/validate-runtime.py"
[[ -f "$source_validator" && ! -L "$source_validator" ]] || die 'source validator missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source validator identity changed'

derived="$(mktemp "$script_dir/.derived-validate-runtime.XXXXXXXX")"
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
        "Classify one exact protected-readback observer netcat capture.",
        "Classify one exact protected-readback call-ledger netcat capture.",
        1,
    ),
    (
        "30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a",
        "3ce494c971c24c9edab73aac592d0ba8dd0bbd25f06051245f7846f95d0c715a",
        1,
    ),
    (
        "7.1.3-gemini-protected-readback-ro",
        "7.1.3-gemini-protected-readback-ledger",
        1,
    ),
    (
        "claim_scope=one-shot-protected-readback-records-only",
        "claim_scope=one-shot-call-ledger-protected-readback-records-only",
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

set +e
python3 "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
