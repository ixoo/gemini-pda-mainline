#!/usr/bin/env bash

# Retarget the exact CPU-map pre-trigger collector to integrated attempt 2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=ae906c132e5bec20e2b9fa668a79ff0bfb3527614d01527393f7e60e99e1b31d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_collector="$script_dir/collect-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is absent or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source collector changed'
derived=$(mktemp "$script_dir/.derived-collect-mt6797-integrated.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
for old, new, count in (
    ("a72-mt6797-cpu-map-attempt-1",
     "a72-mt6797-cpu-map-integrated-attempt-2", 2),
    ("ce55410c-cf39-4028-b248-052865eb161c'",
     "ce55410c-cf39-4028-b248-052865eb161c 136270ea-ff13-483f-b8ad-ce69f7bf6fa7'", 1),
    (".derived-collect-mt6797-cpu-map.XXXXXXXX",
     ".derived-collect-mt6797-cpu-map-integrated.XXXXXXXX", 1),
):
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe integrated collector derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
/bin/bash "$derived" "$@"
