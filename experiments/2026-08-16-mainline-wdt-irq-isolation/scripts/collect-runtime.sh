#!/usr/bin/env bash

# Source-pin and derive the pre-armed observer for one watchdog IRQ isolation
# attempt. The inherited collector retains an exact sanitized USB topology
# journal plus bounded mainline netcat probes and changed-Gemian detection.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=227808983cba54e6e425fcc89ee2623f3b80d4cd29ae7cf1f79d9b5192a0e928

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-16-mainline-scp-handoff-node/scripts/collect-runtime.sh"
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
    ("one SCP handoff-node repair attempt",
     "one watchdog IRQ isolation attempt", 1),
    ("2df0e486-4d13-44f9-a1ec-94f90726a612",
     "01d781fe-f0e9-4588-b5b9-36bd380b9af0", 1),
    ("73be76fd4eb26d6d1d718bb4c0a77653839ca40e00267a5a35defb5b8a45b0f7",
     "b103dd6dbe46caba7a635efb744885b66bfde7c0ef7ea538e93644dc6bf1169d", 1),
    ("mainline-scp-handoff-node-attempt-1",
     "mainline-wdt-irq-isolation-attempt-1", 1),
    (".gemini-scp-handoff-observation.XXXXXXXX",
     ".gemini-wdt-irq-observation.XXXXXXXX", 1),
    ("no-mainline-network-after-SCP-node-before-changed-Gemian-return",
     "no-mainline-network-after-watchdog-IRQ-removal-before-changed-Gemian-return", 1),
    ("exact-current-kernel-serviceable-with-disabled-SCP-node",
     "exact-current-kernel-serviceable-without-watchdog-IRQ", 1),
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
