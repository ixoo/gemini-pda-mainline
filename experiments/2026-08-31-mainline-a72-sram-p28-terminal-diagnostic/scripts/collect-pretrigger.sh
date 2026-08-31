#!/usr/bin/env bash

# Source-pin the bounded read-only collector and retarget only the exact
# SRAM/P28 diagnostic candidate, tooling identities, and capture namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=b2b5baf50249924fde0de4e6cec32b54498280c10da389113bd57150d32e2b33
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-30-mainline-a72-isolation-held-result-contract-repair/scripts/collect-pretrigger.sh"
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-sram-p28-terminal-diagnostic.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("510cb652f1240dad18ed3de7e7a7dcf63624861ad1d47ca9d9e73e68b8e4d726", "7cddf03025df29b718659322789d1ecbe17a2af87a373d88ca9ba9058e7928a3", 1),
    ("feb927cd43bc54b32bd4cedfc2da8164e83f5b722cdae636feaedfa3fc3a3d78", "e0cf19260f8542d33fe5f143310247748966adb6e9ce1ab8db595bd60d2e0165", 1),
    ("20b11cebf6950f8f241b46dd1b2775e9ab872b3eefed3c6b45cf65355fff56a1", "a9d5c1a38363ed6c5fe722e093f8f7fa35833eddce6f232f5b927931e448fe77", 1),
    ("c75c6c43f30f9b029b94aeb3ce17229f51fa26f20d08087b0208fed3a0926b2e", "7ef27071938eef32a5a2ffa63b582d09006eebb999f17e0e0b991102bd63d615", 1),
    ("a72-isolation-held-result-contract-repair", "a72-sram-p28-terminal-diagnostic", 1),
    (".derived-collect-a72-isolation-held-result-repair-inner.XXXXXXXX", ".derived-collect-a72-sram-p28-terminal-diagnostic-inner.XXXXXXXX", 1),
    ("isolation-result repair collector derivation", "SRAM/P28 diagnostic collector derivation", 2),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe SRAM/P28 diagnostic collector derivation: expected "
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
