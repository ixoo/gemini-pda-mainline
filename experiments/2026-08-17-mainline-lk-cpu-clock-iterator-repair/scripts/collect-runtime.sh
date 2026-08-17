#!/usr/bin/env bash

# Source-pin and derive the pre-armed observer for one LK CPU-clock iterator
# repair attempt. The inherited collector retains an exact sanitized USB
# topology journal plus bounded mainline netcat probes and changed-Gemian
# detection.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=18949ed60798f7d5a6fdf1049449fc048d6684d44740e02869a5afe6b0f4b6ea

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-17-mainline-i2c5-serviceability-restoration/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] ||
	die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector identity changed'

derived="$(mktemp "$script_dir/.derived-collect-runtime.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("one I2C5/AW9523 serviceability attempt",
     "one LK CPU-clock iterator repair attempt", 1),
    ("669f7fa0-04df-4bc7-b0ff-260ebc74d362",
     "f61a6a96-8d71-4ea6-b308-0c20511316d1", 1),
    ("8d04c2c7e9c67dcd17189422d1968e416eb9eec304e2b9300b83f48dc9e0ebb5",
     "b478b79a983889514b2b8d122fb6d5ff5057e52c332882b186b82698d1de62b8", 1),
    ("mainline-i2c5-serviceability-attempt-1",
     "mainline-lk-cpu-clock-repair-attempt-1", 1),
    (".gemini-i2c5-serviceability-observation.XXXXXXXX",
     ".gemini-lk-cpu-clock-repair-observation.XXXXXXXX", 1),
    ("no-mainline-network-after-I2C5-serviceability-restoration-before-changed-Gemian-return",
     "no-mainline-network-after-LK-CPU-clock-repair-before-changed-Gemian-return", 1),
    ("exact-current-kernel-serviceable-with-I2C5-AW9523-keyboard",
     "exact-current-kernel-serviceable-after-LK-CPU-clock-iterator-repair", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe collector derivation: expected {count} occurrences, found {actual}: {old}"
        )
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
