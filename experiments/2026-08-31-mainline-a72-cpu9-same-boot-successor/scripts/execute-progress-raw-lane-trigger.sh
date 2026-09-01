#!/usr/bin/env bash

# Source-pin the proven progress errno executor and retarget its exact
# candidate, classifier/validator identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=d02bda0115c6b915d1d4b23934acc251fe39b0c8c62591e1271dfe33eb080412
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_executor="$script_dir/execute-progress-errno-diagnostic-trigger.sh"
[[ -f "$source_executor" && ! -L "$source_executor" ]] || \
	die 'source CPU9 progress errno executor is missing or unsafe'
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source CPU9 progress errno executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-cpu9-progress-raw-lane.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("4bf74874cbfe900576ae891d32b5e8996d5c66ed599b6fca09c7310e87cdeae8",
     "1cf367e021351f8a26643d827866786a879a8d6a3e68d8143cfce40bd1db52f7", 1),
    ("8a390fa06e7bd8fd30701fd947ff0e21a4fdbd3ae6c356fba36a8acab20472d9",
     "00013d15f0bfa0a70ecb582ddee75d1834c8d888744f8af219c4246b2f181d7f", 1),
    ("14fff19f823c8bbe28cb11e941186754acf816a862be3d4f694f95c18e354b3c",
     "453ee0a46804d4d5c797037fbf6b1093eca0cb925785bcbe778a8048748158ec", 1),
    ("eeeb5ec90aea300c143564866158f314022e8576dcde93292900713b31ec5a31",
     "3edab4c7d0f83a3323a0a6b02c939b754ac9de59c36e1f8044155059d11aa3f4", 1),
    ("a72-cpu9-progress-errno-pretrigger-attempt-1",
     "a72-cpu9-progress-raw-lane-pretrigger-attempt-1", 1),
    ('trigger_wrapper="$script_dir/remote-progress-errno-diagnostic-trigger.sh"',
     'trigger_wrapper="$script_dir/remote-progress-raw-lane-trigger.sh"', 1),
    ('classifier="$script_dir/classify-progress-errno-diagnostic-attempt.py"',
     'classifier="$script_dir/classify-progress-raw-lane-attempt.py"', 1),
    ('validator="$script_dir/validate-progress-errno-diagnostic-pretrigger.py"',
     'validator="$script_dir/validate-progress-raw-lane-pretrigger.py"', 1),
    (".gemini-a72-cpu9-progress-errno-validation.XXXXXXXX",
     ".gemini-a72-cpu9-progress-raw-lane-validation.XXXXXXXX", 1),
    (".gemini-a72-cpu9-progress-errno-trigger.XXXXXXXX",
     ".gemini-a72-cpu9-progress-raw-lane-trigger.XXXXXXXX", 1),
    (".gemini-a72-cpu9-progress-errno-command.XXXXXXXX",
     ".gemini-a72-cpu9-progress-raw-lane-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 progress raw-lane executor derivation: expected "
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
