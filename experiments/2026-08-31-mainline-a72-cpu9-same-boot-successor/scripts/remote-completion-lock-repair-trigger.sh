#!/usr/bin/env bash

# Materialize the proven trigger while binding it to the exact pristine
# completion-path lock-repair contract.
set -euo pipefail

readonly SOURCE_SHA256=f9525d329b0c82dbba382065b222ba2a86f9b23cef282c904febd3b227fc5e55
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_trigger="$script_dir/remote-membership-lock-repair-trigger.sh"
[[ "$(sha256sum "$source_trigger" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || {
	printf 'error: source membership-lock trigger changed\n' >&2
	exit 2
}
derived=$(mktemp "$script_dir/.derived-remote-a72-cpu9-completion-lock-trigger.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_trigger" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("bd94d4e4c1f1ceba8aeb4108fb33be0a8358eb794cda27424b4f57c8c5379c88",
     "d86e78db5996f96b0e11efebd044454719ca8f0a6636671e72a405e1047499aa", 1),
    ("validate-membership-lock-repair-pretrigger.py",
     "validate-completion-lock-repair-pretrigger.py", 1),
    ("membership-lock repair", "completion-lock repair", 1),
    (".gemini-a72-cpu9-membership-lock-trigger.XXXXXXXX",
     ".gemini-a72-cpu9-completion-lock-trigger.XXXXXXXX", 1),
    ("cpu9_membership_lock_repair_pretrigger",
     "cpu9_completion_lock_repair_pretrigger", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe completion-lock trigger derivation: expected "
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
