#!/usr/bin/env bash

# Recover terminal A72 proofs and unchanged boot2 after the concurrent child.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=88d04770acd7a6f587e7e278c4a45249a53899046da6f86c333815ec7894a238
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_collector="$script_dir/../../2026-09-02-mainline-mt6797-cpu-map/scripts/collect-integrated-recovery.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source recovery collector is absent or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source recovery collector changed'
derived=$(mktemp "$script_dir/.derived-collect-a72-concurrent-recovery.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
for old, new, count in (
    ('source_collector="$script_dir/collect-recovery.sh"',
     'source_collector="$script_dir/../../2026-09-02-mainline-mt6797-cpu-map/scripts/collect-recovery.sh"', 1),
    ("a72-mt6797-cpu-map-integrated-recovery-attempt-2",
     "a72-concurrent-multiline-recovery-attempt-2", 1),
    ("bea797dd-a01d-416c-b121-5718d12c8b12'",
     "bea797dd-a01d-416c-b121-5718d12c8b12 da3551ea-cfe4-4c42-bbcc-12ffdefdd64f'", 1),
):
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe concurrent recovery derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
/bin/bash "$derived" "$@"
