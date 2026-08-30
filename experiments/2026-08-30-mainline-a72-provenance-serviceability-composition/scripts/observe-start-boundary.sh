#!/usr/bin/env bash

# Source-pin the proven contact-free USB transition observer and retarget only
# its experiment identity. It never opens a device network or shell session.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=9af39a43f53525261b36a58e0032401f3c8b405e7d64c04e45616ca46462720f
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_observer="$repo_root/experiments/2026-08-28-mainline-a72-admission-trace-softfail/scripts/observe-usb-cycle.sh"
[[ -f "$source_observer" && ! -L "$source_observer" ]] || die 'source observer is missing or unsafe'
[[ "$(sha256sum "$source_observer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source observer changed'

derived=$(mktemp "$script_dir/.derived-observe-a72-provenance-start.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_observer" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "experiment=2026-08-28-mainline-a72-admission-trace-softfail"
new = "experiment=2026-08-30-mainline-a72-provenance-serviceability-composition"
if text.count(old) != 1:
    raise SystemExit("unsafe start-boundary observer derivation")
Path(sys.argv[2]).write_text(text.replace(old, new), encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
