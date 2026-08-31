#!/usr/bin/env bash

# Materialize the complete read-only P30E probe, retarget the exact candidate,
# and reject every arm64 late-profile blocker wording.
set -euo pipefail

readonly SOURCE_SHA256=742a8322254f617efe07ffff6265720cbeebe647edc3d1f0f77f087a5fb9a685
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_probe="$repo_root/experiments/2026-08-31-mainline-a72-p30e-entry-diagnostic/scripts/remote-pretrigger.sh"
[[ "$(sha256sum "$source_probe" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source probe changed\n' >&2
	exit 2
}
materialized=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-p30e-ready-identity-probe.XXXXXXXX")
cleanup() { rm -f -- "${materialized:-}"; }
trap cleanup EXIT HUP INT TERM
"$source_probe" >"$materialized"
python3 - "$materialized" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("a4ad4915c3a4cc76f009ddb26240f9aded7c7a05ac121af25c24f37c8d5e7453",
     "459bcf66fe807d9babfeefec7ea9b6e922edfaaa078fcbd288c7639048b31d16", 1),
    ("$BB printf 'profile_blocked_count='; $BB dmesg | $BB grep -Fc 'blocked: required evidence is incomplete' || true",
     "$BB printf 'profile_blocked_count='; $BB dmesg | $BB grep -Ec 'arm64-late-cpu-profile: .* blocked:' || true", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe P30E READY-identity pre-trigger derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
sys.stdout.write(text)
PY
cleanup
trap - EXIT HUP INT TERM
