#!/usr/bin/env bash

# Source-pin the CPUHP lock-repair executor and retarget its exact candidate,
# classifier/validator identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=bced35271e4efda5a50dd82b33e03e3aa7165cad975f63999c5c0870128a2669
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_executor="$script_dir/execute-cpuhp-lock-repair-trigger.sh"
[[ -f "$source_executor" && ! -L "$source_executor" ]] || \
	die 'source CPUHP lock-repair executor is missing or unsafe'
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source CPUHP lock-repair executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-cpu9-cpu-on-progress.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("0904c5a293fea22f6993cb25ab8d775ed539d57c8fac7a7a6c50b67e2916f293",
     "d4eca4accded2692418b5972f0a51df79a8be1a0fc52b52f755258da86eb87fe", 1),
    ("eb0c33abd35fdc621a433968bc7192a20411fd1e0826d31345ec4b099ebca5f4",
     "e7bd0d3a44f6e3c4e520b5514e98f2680247ced85ad2fb6bb912e399a925c4a4", 1),
    ("12f93c321bae4f0e37649ea79e484dcd2ffd838c817c580ff4d6be826f921ef8",
     "af527d6c8cb515751271842bf71d94a0fd72521484fdcb2ce788aa64c9b30003", 1),
    ("09bdca67375272870ce27e325368d86967a104f224dcd61bc7c38848f8f9370d",
     "bf19f8d6343df7aeff659941198986b6cd5deccca595b0600a6e951e60385645", 1),
    ("a72-cpu9-cpuhp-lock-pretrigger-attempt-1",
     "a72-cpu9-cpu-on-progress-pretrigger-attempt-1", 1),
    ('trigger_wrapper="$script_dir/remote-cpuhp-lock-repair-trigger.sh"',
     'trigger_wrapper="$script_dir/remote-cpu-on-progress-trigger.sh"', 1),
    ('classifier="$script_dir/classify-cpuhp-lock-repair-attempt.py"',
     'classifier="$script_dir/classify-cpu-on-progress-attempt.py"', 1),
    ('validator="$script_dir/validate-cpuhp-lock-repair-pretrigger.py"',
     'validator="$script_dir/validate-cpu-on-progress-pretrigger.py"', 1),
    (".gemini-a72-cpu9-cpuhp-lock-validation.XXXXXXXX",
     ".gemini-a72-cpu9-cpu-on-progress-validation.XXXXXXXX", 1),
    (".gemini-a72-cpu9-cpuhp-lock-trigger.XXXXXXXX",
     ".gemini-a72-cpu9-cpu-on-progress-trigger.XXXXXXXX", 1),
    (".gemini-a72-cpu9-cpuhp-lock-command.XXXXXXXX",
     ".gemini-a72-cpu9-cpu-on-progress-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU_ON progress executor derivation: expected "
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
