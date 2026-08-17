#!/usr/bin/env bash

# Source-pin and derive the pre-armed observer for one I2C5/AW9523
# serviceability attempt. The inherited collector retains an exact sanitized
# USB topology journal plus bounded mainline netcat probes and changed-Gemian
# detection.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=4dcb8570db2bdb181e0b3f056e558d1db71605172bd64bc5cd0d295fe0ac3e93

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-16-mainline-wdt-irq-isolation/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
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
    ("one watchdog IRQ isolation attempt",
     "one I2C5/AW9523 serviceability attempt", 1),
    ("01d781fe-f0e9-4588-b5b9-36bd380b9af0",
     "669f7fa0-04df-4bc7-b0ff-260ebc74d362", 1),
    ("b103dd6dbe46caba7a635efb744885b66bfde7c0ef7ea538e93644dc6bf1169d",
     "8d04c2c7e9c67dcd17189422d1968e416eb9eec304e2b9300b83f48dc9e0ebb5", 1),
    ("mainline-wdt-irq-isolation-attempt-1",
     "mainline-i2c5-serviceability-attempt-1", 1),
    (".gemini-wdt-irq-observation.XXXXXXXX",
     ".gemini-i2c5-serviceability-observation.XXXXXXXX", 1),
    ("no-mainline-network-after-watchdog-IRQ-removal-before-changed-Gemian-return",
     "no-mainline-network-after-I2C5-serviceability-restoration-before-changed-Gemian-return", 1),
    ("exact-current-kernel-serviceable-without-watchdog-IRQ",
     "exact-current-kernel-serviceable-with-I2C5-AW9523-keyboard", 1),
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
