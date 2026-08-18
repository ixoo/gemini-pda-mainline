#!/usr/bin/env bash

# Source-pin the checksum-bound USB/netcat collector for one preflight boot.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=6d9d8d3d683b99dff3630e6e172c269d6b4c858e0ae6e018a9d41e327d23ff00

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_collector="$repo_root/experiments/2026-08-17-mainline-da921x-readonly-provider-baseline/scripts/collect-runtime.sh"
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
    ("# Pre-arm one bounded USB/netcat observation of the exact read-only provider\n"
     "# candidate, then request a native reboot and confirm changed Gemian return.",
     "# Pre-arm one bounded USB/netcat observation of the exact read-only preflight\n"
     "# candidate, then request a native reboot and confirm changed Gemian return.", 1),
    ("eeee7adea53134c8146e10591708725649a8331bdef7ad418a847b5d04c8e854",
     "41c652225d3627f5aaaba2272e29a58171008e17b0f7c936116842e7ab0166e3", 1),
    ("cf25dd25266fc4f12f91d4d6e2b91c25f79b7da6617d6a4aaf1169796cb520e8",
     "b7244ea21126bd826e6da158e695534b8cb879b9fed0007781c38d8db17eaa0a", 1),
    ("2b00879d1bc7a025de1d642262bdabe209c096a90c15aba403d09f034b69b324",
     "4fabe0607eb0b6a3e350d3572e70e9882ec76465d84abb0675800839f7be1d5e", 1),
    ("remote-provider-probe.sh", "remote-runtime-probe.sh", 1),
    ("mainline-da921x-lkro-provider-attempt-1",
     "mainline-da921x-preflight-attempt-1", 2),
    ("__DA921X_LKRO_BEGIN__", "__DA921X_PREFLIGHT_BEGIN__", 1),
    ("__DA921X_LKRO_END__", "__DA921X_PREFLIGHT_END__", 1),
    ("success-read-only-provider", "success-readonly-preflight-ledger", 2),
    ("${TMPDIR:-/tmp}/.gemini-da921x-lkro.XXXXXXXX",
     "${TMPDIR:-/tmp}/.gemini-da921x-preflight.XXXXXXXX", 1),
    ("provider runtime did not classify as success",
     "preflight runtime did not classify as success", 1),
    ("DA921x_register_data_writes=0\\n'",
     "I2C6_ledger_count=30\\nI2C6_ledger_overflow=0\\n"
     "DA921x_register_data_writes=0\\nGate6_B3=closed\\nGate6_B4=closed\\n'", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe collector derivation: expected {count}, found {actual}: {old}"
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
