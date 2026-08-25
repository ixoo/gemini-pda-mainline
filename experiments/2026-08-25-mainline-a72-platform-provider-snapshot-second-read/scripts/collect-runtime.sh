#!/usr/bin/env bash

# Source-pin the no-reboot platform-snapshot collector and specialize its exact
# identities and composed platform/provider acceptance gate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=2d76709b49023c96ad213666d75f5da1365824edc474d6486a931cc2615dbf71
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-24-mainline-a72-platform-snapshot-first-read/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-platform-provider.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("39f801f713a76c616ed8d9282fc0a662fb34c5a766d6839e4c47c757638bae43", "ff902d12b95893872990ebf813f24ca298ca76c4f86d4650f3b696cbdc00d79f", 1),
    ("PROBE_SHA256=0227c98f47e4fcebc01647694e126f3f64fe9a41802c438c1a6bab3fafef1e2b", "PROBE_SHA256=9af46dac149267f5c86dd48880e7f5b3c7bed74ab0bf55cbad6e387b9445ffc1", 1),
    ("VALIDATOR_SHA256=d3c4c03661a446e584a44f35534adb6a9e4b690f4244c7cc9a3b674ebcd6761d", "VALIDATOR_SHA256=9e60e9e297aa4412d98f2d7decb459684c049949fcc7bd760b69146be7a89ef9", 1),
    ("a72-platform-snapshot-attempt-1", "a72-platform-provider-snapshot-attempt-1", 1),
    (".gemini-a72-platform-snapshot.XXXXXXXX", ".gemini-a72-platform-provider-snapshot.XXXXXXXX", 1),
    ("runtime_gate=serviceable-platform-snapshot-pass", "runtime_gate=serviceable-platform-provider-pass", 1),
    ("exact one-shot platform-snapshot serviceability pass", "exact one-shot platform/provider-snapshot serviceability pass", 1),
    ("unsafe platform-snapshot collector derivation", "unsafe platform/provider collector derivation", 1),
    (".derived-collect-a72-platform-snapshot.XXXXXXXX", ".derived-collect-a72-platform-provider-nested.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe platform/provider collector wrapper: expected {count}, found {actual}: {old}"
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
