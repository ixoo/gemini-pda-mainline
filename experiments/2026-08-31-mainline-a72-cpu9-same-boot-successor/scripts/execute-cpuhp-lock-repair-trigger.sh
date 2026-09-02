#!/usr/bin/env bash

# Source-pin the progress raw-lane executor and retarget its exact candidate,
# classifier/validator identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=1641f0b1c7f13c48680d240be839c82ab35d63de364166d7ef3442b88cd2cb81
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_executor="$script_dir/execute-progress-raw-lane-trigger.sh"
[[ -f "$source_executor" && ! -L "$source_executor" ]] || \
	die 'source progress raw-lane executor is missing or unsafe'
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source progress raw-lane executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-cpu9-cpuhp-lock.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("1cf367e021351f8a26643d827866786a879a8d6a3e68d8143cfce40bd1db52f7",
     "0904c5a293fea22f6993cb25ab8d775ed539d57c8fac7a7a6c50b67e2916f293", 1),
    ("00013d15f0bfa0a70ecb582ddee75d1834c8d888744f8af219c4246b2f181d7f",
     "eb0c33abd35fdc621a433968bc7192a20411fd1e0826d31345ec4b099ebca5f4", 1),
    ("453ee0a46804d4d5c797037fbf6b1093eca0cb925785bcbe778a8048748158ec",
     "12f93c321bae4f0e37649ea79e484dcd2ffd838c817c580ff4d6be826f921ef8", 1),
    ("3edab4c7d0f83a3323a0a6b02c939b754ac9de59c36e1f8044155059d11aa3f4",
     "09bdca67375272870ce27e325368d86967a104f224dcd61bc7c38848f8f9370d", 1),
    ("a72-cpu9-progress-raw-lane-pretrigger-attempt-1",
     "a72-cpu9-cpuhp-lock-pretrigger-attempt-1", 1),
    ('trigger_wrapper="$script_dir/remote-progress-raw-lane-trigger.sh"',
     'trigger_wrapper="$script_dir/remote-cpuhp-lock-repair-trigger.sh"', 1),
    ('classifier="$script_dir/classify-progress-raw-lane-attempt.py"',
     'classifier="$script_dir/classify-cpuhp-lock-repair-attempt.py"', 1),
    ('validator="$script_dir/validate-progress-raw-lane-pretrigger.py"',
     'validator="$script_dir/validate-cpuhp-lock-repair-pretrigger.py"', 1),
    (".gemini-a72-cpu9-progress-raw-lane-validation.XXXXXXXX",
     ".gemini-a72-cpu9-cpuhp-lock-validation.XXXXXXXX", 1),
    (".gemini-a72-cpu9-progress-raw-lane-trigger.XXXXXXXX",
     ".gemini-a72-cpu9-cpuhp-lock-trigger.XXXXXXXX", 1),
    (".gemini-a72-cpu9-progress-raw-lane-command.XXXXXXXX",
     ".gemini-a72-cpu9-cpuhp-lock-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPUHP lock-repair executor derivation: expected "
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
