#!/usr/bin/env bash

# Source-pin the movement-attribution live probe and retarget its installed
# identity to the exact CPU-status-mask candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=0ca3407536cb3f399e6e31fab443bd097511237feaf455f434364a2e03c0c78a
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod grep mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-26-mainline-a72-platform-movement-attribution/scripts/remote-live-probe.sh"
[[ -f "$source_probe" && ! -L "$source_probe" ]] || die 'source probe is missing or unsafe'
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source probe changed'

derived=$(mktemp "$script_dir/.derived-remote-live-probe-cpu-status-mask.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_probe" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("exact movement-attribution candidate", "exact CPU-status-mask candidate", 1),
    ("9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78", "6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7", 2),
    (".derived-remote-live-probe-platform-movement.XXXXXXXX", ".derived-remote-live-probe-cpu-status-mask-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU-status-mask probe derivation: expected {count}, found {actual}: {old}"
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
