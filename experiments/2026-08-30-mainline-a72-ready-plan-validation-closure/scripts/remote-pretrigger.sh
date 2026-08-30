#!/usr/bin/env bash

# Source-pin the exact read-only probe and bind it to the post-0437 boot2 image.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=5826658d983313d2ddb7b032dc80f8a7a3844076aaf346e36f852702e7cec010
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-30-mainline-a72-provenance-serviceability-composition/scripts/remote-pretrigger.sh"
[[ -f "$source_probe" && ! -L "$source_probe" ]] || die 'source probe is missing or unsafe'
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source probe changed'

derived=$(mktemp "$script_dir/.derived-remote-ready-plan-closure.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_probe" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
old = "f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a"
new = "726b622ab503e844e2faddb33fe357250df329510d5b3ab5877687f4db7bfcb0"
if text.count(old) != 1:
    raise SystemExit("unsafe READY-plan remote-probe derivation")
Path(sys.argv[2]).write_text(text.replace(old, new), encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
rc=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
