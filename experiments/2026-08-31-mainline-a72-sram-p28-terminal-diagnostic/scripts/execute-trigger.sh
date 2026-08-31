#!/usr/bin/env bash

# Source-pin the boot-bound one-shot executor and retarget only the exact
# SRAM/P28 diagnostic candidate, tooling identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=f8859acfe9ce6246d450d6f577d8523e2aca95958253047b4cef9f1694d406bc
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_executor="$repo_root/experiments/2026-08-30-mainline-a72-isolation-held-result-contract-repair/scripts/execute-trigger.sh"
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-sram-p28-terminal-diagnostic.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726", "7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3", 1),
    ("b609a64e41d664167912dd0156c45c3428a13b0c9495deab8317ca9288611508", "fe0b58d25fca1b7cbfd81b8388cc6614770c2a1f357904893deace67dd110bbe", 1),
    ("69034fd59cfee5a8d5ae34bd23a55ef199bcbe61007b763fef014762eb45bfe3", "6f2063d9254ff4d956f30faefe36481392b60011083b4980c5583a2b68ae39f5", 1),
    ("c75c6c43f30f9b029b94aeb3ce17229f51fa26f20d08087b0208fed3a0926b2e", "7ef27071938eef32a5a2ffa63b582d09006eebb999f17e0e0b991102bd63d615", 1),
    ("2026-08-30-mainline-a72-isolation-held-result-contract-repair", "2026-08-31-mainline-a72-sram-p28-terminal-diagnostic", 1),
    ("a72-isolation-held-result-contract-repair", "a72-sram-p28-terminal-diagnostic", 1),
    (".derived-execute-a72-isolation-held-result-repair-inner.XXXXXXXX", ".derived-execute-a72-sram-p28-terminal-diagnostic-inner.XXXXXXXX", 1),
    ("isolation-result repair executor derivation", "SRAM/P28 diagnostic executor derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe SRAM/P28 diagnostic executor derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
rc=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
