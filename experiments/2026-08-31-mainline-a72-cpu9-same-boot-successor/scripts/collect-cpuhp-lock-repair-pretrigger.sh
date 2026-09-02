#!/usr/bin/env bash

# Source-pin the progress raw-lane collector and retarget its exact candidate,
# validator identity, and private evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=e4bdf2f5f4a412dea148d9c16be5a27ba2b266b4d9bedf830e753efc9314bf96
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_collector="$script_dir/collect-progress-raw-lane-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || \
	die 'source progress raw-lane collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source progress raw-lane collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-cpu9-cpuhp-lock.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("1cf367e021351f8a26643d827866786a879a8d6a3e68d8143cfce40bd1db52f7",
     "0904c5a293fea22f6993cb25ab8d775ed539d57c8fac7a7a6c50b67e2916f293", 1),
    ("d745138fa7b6c0a2fb19bf6a01fe127929a28df48fbd3972bf26e1647b17aafe",
     "9cd506a4052dd65a5b4c877ff514a66262ec960ab77032d32381329ada2522d5", 1),
    ("0d56bd7182bd25c849ebaf1de59e6bfa8ecb1a0ff1e839a24259cdb9d861a17c",
     "6aae843d3d9ab89230a7e67ad838280b7716dc927495b8f4fc5e1566a6314c21", 1),
    ("3edab4c7d0f83a3323a0a6b02c939b754ac9de59c36e1f8044155059d11aa3f4",
     "09bdca67375272870ce27e325368d86967a104f224dcd61bc7c38848f8f9370d", 1),
    ("__GEMINI_A72_CPU9_PROGRESS_RAW_LANE_PRETRIGGER_SCRIPT__",
     "__GEMINI_A72_CPU9_CPUHP_LOCK_PRETRIGGER_SCRIPT__", 1),
    ("remote-progress-raw-lane-pretrigger.sh",
     "remote-cpuhp-lock-repair-pretrigger.sh", 1),
    ("validate-progress-raw-lane-pretrigger.py",
     "validate-cpuhp-lock-repair-pretrigger.py", 1),
    ("a72-cpu9-progress-raw-lane-pretrigger-attempt-1",
     "a72-cpu9-cpuhp-lock-pretrigger-attempt-1", 1),
    (".gemini-a72-cpu9-progress-raw-lane-probe.XXXXXXXX",
     ".gemini-a72-cpu9-cpuhp-lock-probe.XXXXXXXX", 1),
    (".gemini-a72-cpu9-progress-raw-lane-command.XXXXXXXX",
     ".gemini-a72-cpu9-cpuhp-lock-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPUHP lock-repair collector derivation: expected "
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
