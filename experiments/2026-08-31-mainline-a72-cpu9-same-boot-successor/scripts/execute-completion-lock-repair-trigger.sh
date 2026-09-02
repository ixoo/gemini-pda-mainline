#!/usr/bin/env bash

# Source-pin the membership-lock executor and retarget its exact candidate,
# classifier/validator identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=4859d424ef721fcdc171db709b7992f10b6381e19e6cd9f646f9a95db6e7c151
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_executor="$script_dir/execute-membership-lock-repair-trigger.sh"
[[ -f "$source_executor" && ! -L "$source_executor" ]] || \
	die 'source membership-lock executor is missing or unsafe'
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source membership-lock executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-cpu9-completion-lock.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c",
     "370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e", 1),
    ("f9525d329b0c82dbba382065b222ba2a86f9b23cef282c904febd3b227fc5e55",
     "37c28c542989e02654561c45ecb5c5e95df327c21952af310be3dbe12b8bf3be", 1),
    ("5a866a7bd782e8518f6980aa0dd7ff14c266cdf42d2c3b8a50ec6a21ba7c8853",
     "b10dcf6a1f7d495b012e856d45ae04047a2ad70be5d8280724336adf9c82f536", 1),
    ("bd94d4e4c1f1ceba8aeb4108fb33be0a8358eb794cda27424b4f57c8c5379c88",
     "d86e78db5996f96b0e11efebd044454719ca8f0a6636671e72a405e1047499aa", 1),
    ("a72-cpu9-membership-lock-pretrigger-attempt-1",
     "a72-cpu9-completion-lock-pretrigger-attempt-1", 1),
    ('trigger_wrapper="$script_dir/remote-membership-lock-repair-trigger.sh"',
     'trigger_wrapper="$script_dir/remote-completion-lock-repair-trigger.sh"', 1),
    ('classifier="$script_dir/classify-membership-lock-repair-attempt.py"',
     'classifier="$script_dir/classify-completion-lock-repair-attempt.py"', 1),
    ('validator="$script_dir/validate-membership-lock-repair-pretrigger.py"',
     'validator="$script_dir/validate-completion-lock-repair-pretrigger.py"', 1),
    (".gemini-a72-cpu9-membership-lock-validation.XXXXXXXX",
     ".gemini-a72-cpu9-completion-lock-validation.XXXXXXXX", 1),
    (".gemini-a72-cpu9-membership-lock-trigger.XXXXXXXX",
     ".gemini-a72-cpu9-completion-lock-trigger.XXXXXXXX", 1),
    (".gemini-a72-cpu9-membership-lock-command.XXXXXXXX",
     ".gemini-a72-cpu9-completion-lock-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe completion-lock executor derivation: expected "
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
