#!/usr/bin/env bash

# Source-pin the membership-lock collector and retarget its exact candidate,
# tooling identities, and private evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=458e25f09662b5ef6d7eec5b244611daa7e787d1e5047076138cf99b12da904d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_collector="$script_dir/collect-membership-lock-repair-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || \
	die 'source membership-lock collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source membership-lock collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-cpu9-completion-lock.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c",
     "370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e", 1),
    ("3c96b40d8d48fec85bb78163363eae3806a1544e6536877183a6adff0a623a9b",
     "a120caa080db781eb92cec9166b240446a01f870f8f3aeeccaecdbc9fa50c787", 1),
    ("be61f9bf92f3b08c18fadd7a510e3e757b1db4e22b3cbd672a426d0c6ca9d95e",
     "139e2260aedc1b10c085c540f3a0e21b82c28e319193a915ab66d2ebbec7fbd0", 1),
    ("bd94d4e4c1f1ceba8aeb4108fb33be0a8358eb794cda27424b4f57c8c5379c88",
     "d86e78db5996f96b0e11efebd044454719ca8f0a6636671e72a405e1047499aa", 1),
    ("__GEMINI_A72_CPU9_MEMBERSHIP_LOCK_PRETRIGGER_SCRIPT__",
     "__GEMINI_A72_CPU9_COMPLETION_LOCK_PRETRIGGER_SCRIPT__", 1),
    ("remote-membership-lock-repair-pretrigger.sh",
     "remote-completion-lock-repair-pretrigger.sh", 1),
    ("validate-membership-lock-repair-pretrigger.py",
     "validate-completion-lock-repair-pretrigger.py", 1),
    ("a72-cpu9-membership-lock-pretrigger-attempt-1",
     "a72-cpu9-completion-lock-pretrigger-attempt-1", 1),
    (".gemini-a72-cpu9-membership-lock-probe.XXXXXXXX",
     ".gemini-a72-cpu9-completion-lock-probe.XXXXXXXX", 1),
    (".gemini-a72-cpu9-membership-lock-command.XXXXXXXX",
     ".gemini-a72-cpu9-completion-lock-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe completion-lock collector derivation: expected "
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
