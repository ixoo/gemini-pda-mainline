#!/usr/bin/env bash

# Source-pin the proven progress errno collector and retarget its exact
# candidate, validator identity, and private evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=939b5c9d7381ecea1c21544ffb5e347e0ac2954a79798c283169bfee5cd854ad
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_collector="$script_dir/collect-progress-errno-diagnostic-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || \
	die 'source CPU9 progress errno collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source CPU9 progress errno collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-cpu9-progress-raw-lane.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("4bf74874cbfe900576ae891d32b5e8996d5c66ed599b6fca09c7310e87cdeae8",
     "1cf367e021351f8a26643d827866786a879a8d6a3e68d8143cfce40bd1db52f7", 1),
    ("eeeb5ec90aea300c143564866158f314022e8576dcde93292900713b31ec5a31",
     "3edab4c7d0f83a3323a0a6b02c939b754ac9de59c36e1f8044155059d11aa3f4", 1),
    ("__GEMINI_A72_CPU9_PROGRESS_ERRNO_PRETRIGGER_SCRIPT__",
     "__GEMINI_A72_CPU9_PROGRESS_RAW_LANE_PRETRIGGER_SCRIPT__", 1),
    ("validate-progress-errno-diagnostic-pretrigger.py",
     "validate-progress-raw-lane-pretrigger.py", 1),
    ("a72-cpu9-progress-errno-pretrigger-attempt-1",
     "a72-cpu9-progress-raw-lane-pretrigger-attempt-1", 1),
    (".gemini-a72-cpu9-progress-errno-probe.XXXXXXXX",
     ".gemini-a72-cpu9-progress-raw-lane-probe.XXXXXXXX", 1),
    (".gemini-a72-cpu9-progress-errno-command.XXXXXXXX",
     ".gemini-a72-cpu9-progress-raw-lane-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 progress raw-lane collector derivation: expected "
            f"{count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
rc=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$rc"
