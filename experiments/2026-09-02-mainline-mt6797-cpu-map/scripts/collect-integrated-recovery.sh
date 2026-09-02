#!/usr/bin/env bash

# Retarget the exact CPU-map recovery collector to integrated attempt 2.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=19c366209e386159dfc0047a266a362f960d1cfd029a2c3c145f9d0e91a1a88a
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_collector="$script_dir/collect-recovery.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source recovery collector is absent or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source recovery collector changed'
derived=$(mktemp "$script_dir/.derived-collect-mt6797-integrated-recovery.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
for old, new, count in (
    ("a72-mt6797-cpu-map-recovery-attempt-1",
     "a72-mt6797-cpu-map-integrated-recovery-attempt-2", 2),
    ("de44c0b2-2ff2-4423-8f0b-8d6e9b0b9e04'",
     "de44c0b2-2ff2-4423-8f0b-8d6e9b0b9e04 bea797dd-a01d-416c-b121-5718d12c8b12'", 1),
    (".derived-collect-mt6797-cpu-map-recovery.XXXXXXXX",
     ".derived-collect-mt6797-cpu-map-integrated-recovery.XXXXXXXX", 1),
):
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe integrated recovery derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
/bin/bash "$derived" "$@"
