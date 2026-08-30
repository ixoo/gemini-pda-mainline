#!/usr/bin/env bash

# Source-pin the exact identity-aware collector and advance only its private
# output identity for the observer-armed start-boundary retry.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=c1e0ecb7e0f10b3c9fd1824b0111b9c641097b61c695ff53121246f87b901c2e
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_collector="$script_dir/collect-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-provenance-pretrigger-attempt-2.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("a72-provenance-serviceability-pretrigger-attempt-1",
     "a72-provenance-serviceability-pretrigger-attempt-2", 1),
    (".derived-collect-a72-provenance-pretrigger.XXXXXXXX",
     ".derived-collect-a72-provenance-pretrigger-attempt-2-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe attempt-2 collector derivation: expected {count}, found {actual}: {old}"
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
