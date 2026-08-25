#!/usr/bin/env bash

# Source-pin the no-reboot platform/provider collector and retarget its exact
# provider-ready identities and acceptance gate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=d046d0de715a6de747bffab1bc8aed9b74194bf229afaad7ab84ac02b91a241d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_collector="$repo_root/experiments/2026-08-25-mainline-a72-platform-provider-snapshot-second-read/scripts/collect-runtime.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || die 'source collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-platform-provider-ready.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("ff902d12b95893872990ebf813f24ca298ca76c4f86d4650f3b696cbdc00d79f", "f55bb272de24a62a0e4055624e8eb0ef35bc53432fa130463c867c43c059732e", 1),
    ("PROBE_SHA256=9af46dac149267f5c86dd48880e7f5b3c7bed74ab0bf55cbad6e387b9445ffc1", "PROBE_SHA256=f711822bc41d099ed417a7844ca5986cd9b150171674c3e40fbe57f4ecd8e2d7", 1),
    ("VALIDATOR_SHA256=9e60e9e297aa4412d98f2d7decb459684c049949fcc7bd760b69146be7a89ef9", "VALIDATOR_SHA256=8b88d26718faf70e98960e784d781e66041c37bbe45cd177bd4648fb5677db91", 1),
    ("a72-platform-provider-snapshot-attempt-1", "a72-platform-provider-ready-attempt-1", 1),
    (".gemini-a72-platform-provider-snapshot.XXXXXXXX", ".gemini-a72-platform-provider-ready.XXXXXXXX", 1),
    ("runtime_gate=serviceable-platform-provider-pass", "runtime_gate=serviceable-platform-provider-ready-pass", 1),
    ("exact one-shot platform/provider-snapshot serviceability pass", "exact provider-ready one-shot platform/provider serviceability pass", 1),
    ("unsafe platform/provider collector derivation", "unsafe provider-ready collector derivation", 1),
    (".derived-collect-a72-platform-provider-nested.XXXXXXXX", ".derived-collect-a72-platform-provider-ready-nested.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe provider-ready collector wrapper: expected {count}, found {actual}: {old}"
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
