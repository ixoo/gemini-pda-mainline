#!/usr/bin/env bash

# Source-pin the proven classification-closure collector and give the fresh
# CPU8 one-shot pre-arm frame its own private evidence identity. No trigger.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=41294a0dd64cdad778851460414b7586a6837f6a28e8154f56b6c35d8d87de88
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-30-mainline-a72-classification-universe-closure/scripts/collect-ready.sh"
source_dir=$(dirname -- "$source_collector")
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

# Keep the derived wrapper beside its source-pinned support files so every
# location-sensitive helper identity remains exact.
derived=$(mktemp "$source_dir/.derived-collect-a72-cpu8-ready-prearm.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    (
        "a72-classification-universe-closure-attempt-2",
        "a72-cpu8-ready-one-shot-prearm-1",
        1,
    ),
    (
        ".derived-collect-a72-classification-closure.XXXXXXXX",
        ".derived-collect-a72-cpu8-ready-prearm-inner.XXXXXXXX",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU8 READY pre-arm derivation: expected {count}, found {actual}: {old}"
        )
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
