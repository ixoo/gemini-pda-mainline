#!/usr/bin/env bash

# Source-pin the CPU_ON progress collector and retarget its exact candidate,
# tooling identities, and private evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=f6767fab3efbd088652b2835886fe6c356f4071cc90d461caa6c7cafceda8203
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_collector="$script_dir/collect-cpu-on-progress-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || \
	die 'source CPU_ON progress collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source CPU_ON progress collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-cpu9-membership-lock.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("d4eca4accded2692418b5972f0a51df79a8be1a0fc52b52f755258da86eb87fe",
     "65355ce48e1bbab736a33452160493f6b61915ab09a8713ba0ef2da1262f676c", 1),
    ("41f4eac6c2fc0f3faca53706a9dc056f2956dfa549d12e115dc5b641482e2940",
     "3c96b40d8d48fec85bb78163363eae3806a1544e6536877183a6adff0a623a9b", 1),
    ("4ba88f79edae86e9af4448b72841bb465ea75d2b9c8fd05828075aeda97c4049",
     "be61f9bf92f3b08c18fadd7a510e3e757b1db4e22b3cbd672a426d0c6ca9d95e", 1),
    ("bf19f8d6343df7aeff659941198986b6cd5deccca595b0600a6e951e60385645",
     "bd94d4e4c1f1ceba8aeb4108fb33be0a8358eb794cda27424b4f57c8c5379c88", 1),
    ("__GEMINI_A72_CPU9_CPU_ON_PROGRESS_PRETRIGGER_SCRIPT__",
     "__GEMINI_A72_CPU9_MEMBERSHIP_LOCK_PRETRIGGER_SCRIPT__", 1),
    ("remote-cpu-on-progress-pretrigger.sh",
     "remote-membership-lock-repair-pretrigger.sh", 1),
    ("validate-cpu-on-progress-pretrigger.py",
     "validate-membership-lock-repair-pretrigger.py", 1),
    ("a72-cpu9-cpu-on-progress-pretrigger-attempt-1",
     "a72-cpu9-membership-lock-pretrigger-attempt-1", 1),
    (".gemini-a72-cpu9-cpu-on-progress-probe.XXXXXXXX",
     ".gemini-a72-cpu9-membership-lock-probe.XXXXXXXX", 1),
    (".gemini-a72-cpu9-cpu-on-progress-command.XXXXXXXX",
     ".gemini-a72-cpu9-membership-lock-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe membership-lock collector derivation: expected "
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
