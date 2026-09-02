#!/usr/bin/env bash

# Materialize the proven trigger while binding it to the exact pristine
# membership-begin lock-repair contract.
set -euo pipefail

readonly SOURCE_SHA256=e7bd0d3a44f6e3c4e520b5514e98f2680247ced85ad2fb6bb912e399a925c4a4
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_trigger="$script_dir/remote-cpu-on-progress-trigger.sh"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source CPU_ON progress trigger changed\n' >&2
	exit 2
}
derived=$(mktemp "$script_dir/.derived-remote-a72-cpu9-membership-lock-trigger.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_trigger" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("bf19f8d6343df7aeff659941198986b6cd5deccca595b0600a6e951e60385645",
     "bd94d4e4c1f1ceba8aeb4108fb33be0a8358eb794cda27424b4f57c8c5379c88", 1),
    ("validate-cpu-on-progress-pretrigger.py",
     "validate-membership-lock-repair-pretrigger.py", 1),
    ("CPU_ON progress", "membership-lock repair", 3),
    (".gemini-a72-cpu9-cpu-on-progress-trigger.XXXXXXXX",
     ".gemini-a72-cpu9-membership-lock-trigger.XXXXXXXX", 1),
    ("cpu9_cpu_on_progress_pretrigger",
     "cpu9_membership_lock_repair_pretrigger", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe membership-lock trigger derivation: expected "
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
