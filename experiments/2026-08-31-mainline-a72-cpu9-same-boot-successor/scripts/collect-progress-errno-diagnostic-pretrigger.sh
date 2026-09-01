#!/usr/bin/env bash

# Source-pin the proven mapping-fix collector and retarget its exact candidate,
# tooling identities, and private evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=cab629c6bb704dbd5ee9c36071b04692b2f9a0f628972759ec037943065aa7e5
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_collector="$script_dir/collect-mapping-fix-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || \
	die 'source CPU9 mapping-fix collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source CPU9 mapping-fix collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-cpu9-progress-errno.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("c531a9e05ae6f2d51211d73fb487efbaef235cfede195ba135e819bd4f2575c0",
     "4bf74874cbfe900576ae891d32b5e8996d5c66ed599b6fca09c7310e87cdeae8", 1),
    ("f284a4a27b84f87515f52fa68ade902cf7bf1920cd37ceeecb1d021fbbe99e63",
     "66d1c458600e481bc3dd7c59f32e3775081e34df0d83a50a3e9615d26013b9df", 1),
    ("1ae99b70ce93e139e2d27865683aec995af17ba432f8a707051543d1163d66e5",
     "f0a603d2ead8ee36c5b601c00aba75a25e670518f70119566a9f47ebc412630b", 1),
    ("26fac1ea17aec094ba09c466956c4ccacab61f5e6ecc6aac2d1d385ab1597a7f",
     "eeeb5ec90aea300c143564866158f314022e8576dcde93292900713b31ec5a31", 1),
    ("__GEMINI_A72_CPU9_MAPPING_FIX_PRETRIGGER_SCRIPT__",
     "__GEMINI_A72_CPU9_PROGRESS_ERRNO_PRETRIGGER_SCRIPT__", 1),
    ("remote-mapping-fix-pretrigger.sh",
     "remote-progress-errno-diagnostic-pretrigger.sh", 1),
    ("validate-mapping-fix-pretrigger.py",
     "validate-progress-errno-diagnostic-pretrigger.py", 1),
    ("a72-cpu9-mapping-fix-pretrigger-attempt-1",
     "a72-cpu9-progress-errno-pretrigger-attempt-1", 1),
    (".gemini-a72-cpu9-mapping-fix-probe.XXXXXXXX",
     ".gemini-a72-cpu9-progress-errno-probe.XXXXXXXX", 1),
    (".gemini-a72-cpu9-mapping-fix-command.XXXXXXXX",
     ".gemini-a72-cpu9-progress-errno-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 progress errno collector derivation: expected "
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
