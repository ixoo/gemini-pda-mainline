#!/usr/bin/env bash

# Source-pin the CPU_ON progress executor and retarget its exact candidate,
# classifier/validator identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=2e714717c25159336109d761bb88b6f0746bb9c39b956cdb813a39a998de1706
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_executor="$script_dir/execute-cpu-on-progress-trigger.sh"
[[ -f "$source_executor" && ! -L "$source_executor" ]] || \
	die 'source CPU_ON progress executor is missing or unsafe'
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source CPU_ON progress executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-cpu9-membership-lock.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("d4eca4accded2692418b5972f0a51df79a8be1a0fc52b52f755258da86eb87fe",
     "65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c", 1),
    ("e7bd0d3a44f6e3c4e520b5514e98f2680247ced85ad2fb6bb912e399a925c4a4",
     "f9525d329b0c82dbba382065b222ba2a86f9b23cef282c904febd3b227fc5e55", 1),
    ("af527d6c8cb515751271842bf71d94a0fd72521484fdcb2ce788aa64c9b30003",
     "5a866a7bd782e8518f6980aa0dd7ff14c266cdf42d2c3b8a50ec6a21ba7c8853", 1),
    ("bf19f8d6343df7aeff659941198986b6cd5deccca595b0600a6e951e60385645",
     "bd94d4e4c1f1ceba8aeb4108fb33be0a8358eb794cda27424b4f57c8c5379c88", 1),
    ("a72-cpu9-cpu-on-progress-pretrigger-attempt-1",
     "a72-cpu9-membership-lock-pretrigger-attempt-1", 1),
    ('trigger_wrapper="$script_dir/remote-cpu-on-progress-trigger.sh"',
     'trigger_wrapper="$script_dir/remote-membership-lock-repair-trigger.sh"', 1),
    ('classifier="$script_dir/classify-cpu-on-progress-attempt.py"',
     'classifier="$script_dir/classify-membership-lock-repair-attempt.py"', 1),
    ('validator="$script_dir/validate-cpu-on-progress-pretrigger.py"',
     'validator="$script_dir/validate-membership-lock-repair-pretrigger.py"', 1),
    (".gemini-a72-cpu9-cpu-on-progress-validation.XXXXXXXX",
     ".gemini-a72-cpu9-membership-lock-validation.XXXXXXXX", 1),
    (".gemini-a72-cpu9-cpu-on-progress-trigger.XXXXXXXX",
     ".gemini-a72-cpu9-membership-lock-trigger.XXXXXXXX", 1),
    (".gemini-a72-cpu9-cpu-on-progress-command.XXXXXXXX",
     ".gemini-a72-cpu9-membership-lock-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe membership-lock executor derivation: expected "
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
