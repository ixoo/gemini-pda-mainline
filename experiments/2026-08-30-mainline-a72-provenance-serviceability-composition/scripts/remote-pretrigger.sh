#!/usr/bin/env bash

# Source-pin the exact read-only admission probe, retarget the installed
# candidate, and add positive architecture identity / blocker observations.
set -euo pipefail

readonly SOURCE_SHA256=d7a32a17362a92712a164d87f36c240c4af8e0261a90c43b41d3763131f93cc2
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-28-mainline-a72-admission-atag-one-shot/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
python3 - "$source_probe" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
anchor = '''$BB printf 'maxcpus8_tokens='; $BB grep -Eoc '(^| )maxcpus=8( |$)' /proc/cmdline || true
'''
insert = anchor + '''$BB printf 'provenance_node='; if $BB test -d /sys/firmware/devicetree/base/chosen/gemini-late-cpu-provenance; then $BB printf '1\\n'; else $BB printf '0\\n'; fi
$BB printf 'provenance_compatible='; $BB tr '\\000' ',' </sys/firmware/devicetree/base/chosen/gemini-late-cpu-provenance/compatible 2>/dev/null || true; $BB printf '\\n'
$BB printf 'runtime_identity_verified_count='; $BB dmesg | $BB grep -Fc 'arm64-late-cpu-profile: verified the pre-finalization runtime identity binding' || true
$BB printf 'runtime_identity_invalid_count='; $BB dmesg | $BB grep -Fc 'arm64-late-cpu-profile: static runtime identity record is unavailable or invalid' || true
$BB printf 'runtime_identity_mismatch_count='; $BB dmesg | $BB grep -Fc 'arm64-late-cpu-profile: running config, build-ID, or command-line identity did not match' || true
$BB printf 'runtime_identity_unconfigured_count='; $BB dmesg | $BB grep -Fc 'arm64-late-cpu-profile: runtime identity producer is not configured' || true
$BB printf 'profile_blocked_count='; $BB dmesg | $BB grep -Fc 'blocked: required evidence is incomplete' || true
'''
replacements = (
    ("fd611a4ca87fd1645e2fa75b3927d56e9e7eac89f3d84712e5555a3aab8f4cf0",
     "f694ddb95649db38ad72d08dcb2f81688608dca44782f08cfe4412e06b26204a", 1),
    (anchor, insert, 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe identity-aware probe derivation: expected {count}, found {actual}")
    text = text.replace(old, new)
sys.stdout.write(text)
PY
