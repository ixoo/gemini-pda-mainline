#!/usr/bin/env bash

# Allocate a fresh pristine CPU-map boot for the concurrent multiline child.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=d1f92c8813cbb1ff337b9d5372a9a0b274f31f760745cbdf1fcce44a122ef290
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_collector="$script_dir/../../2026-09-02-mainline-mt6797-cpu-map/scripts/collect-integrated-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is absent or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'
derived=$(mktemp "$script_dir/.derived-collect-a72-concurrent.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
for old, new, count in (
    ('source_collector="$script_dir/collect-pretrigger.sh"',
     'source_collector="$script_dir/../../2026-09-02-mainline-mt6797-cpu-map/scripts/collect-pretrigger.sh"', 1),
    ("a72-mt6797-cpu-map-integrated-attempt-2",
     "a72-concurrent-multiline-attempt-2", 1),
    ('derived=$(mktemp "$script_dir/.derived-collect-mt6797-integrated.XXXXXXXX")',
     'derived=$(mktemp "$script_dir/../../2026-09-02-mainline-mt6797-cpu-map/scripts/.derived-collect-a72-concurrent.XXXXXXXX")', 1),
    ("136270ea-ff13-483f-b8ad-ce69f7bf6fa7'",
     "136270ea-ff13-483f-b8ad-ce69f7bf6fa7 4ea50a64-aa9b-4610-97b1-5391841ce676'", 1),
):
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe concurrent pretrigger derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
/bin/bash "$derived" "$@"
