#!/usr/bin/env bash

# Source-pin the proven one-shot mapping-fix executor and retarget its exact
# progress errno candidate, tooling identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=f3e2090babfcfe7fbf90ebf81db04b9d323623e33ee1a355eea5a73cee12d6d3
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_executor="$script_dir/execute-mapping-fix-trigger.sh"
[[ -f "$source_executor" && ! -L "$source_executor" ]] || \
	die 'source CPU9 mapping-fix executor is missing or unsafe'
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source CPU9 mapping-fix executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-cpu9-progress-errno.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("c531a9e05ae6f2d51211d73fb487efbaef235cfede195ba135e819bd4f2575c0",
     "4bf74874cbfe900576ae891d32b5e8996d5c66ed599b6fca09c7310e87cdeae8", 1),
    ("238c13324008dcfb1e9d79f09fa97beded98536168267b4d4074fb3c0882916a",
     "8a390fa06e7bd8fd30701fd947ff0e21a4fdbd3ae6c356fba36a8acab20472d9", 1),
    ("c72ec553233aba2a1c425d416c9d2da49c7d5045a840560ad473f04d82b335b3",
     "14fff19f823c8bbe28cb11e941186754acf816a862be3d4f694f95c18e354b3c", 1),
    ("26fac1ea17aec094ba09c466956c4ccacab61f5e6ecc6aac2d1d385ab1597a7f",
     "eeeb5ec90aea300c143564866158f314022e8576dcde93292900713b31ec5a31", 1),
    ("a72-cpu9-mapping-fix-pretrigger-attempt-1",
     "a72-cpu9-progress-errno-pretrigger-attempt-1", 1),
    ('trigger_wrapper="$script_dir/remote-mapping-fix-trigger.sh"',
     'trigger_wrapper="$script_dir/remote-progress-errno-diagnostic-trigger.sh"', 1),
    ('classifier="$script_dir/classify-mapping-fix-attempt.py"',
     'classifier="$script_dir/classify-progress-errno-diagnostic-attempt.py"', 1),
    ('validator="$script_dir/validate-mapping-fix-pretrigger.py"',
     'validator="$script_dir/validate-progress-errno-diagnostic-pretrigger.py"', 1),
    (".gemini-a72-cpu9-mapping-fix-validation.XXXXXXXX",
     ".gemini-a72-cpu9-progress-errno-validation.XXXXXXXX", 1),
    (".gemini-a72-cpu9-mapping-fix-trigger.XXXXXXXX",
     ".gemini-a72-cpu9-progress-errno-trigger.XXXXXXXX", 1),
    (".gemini-a72-cpu9-mapping-fix-command.XXXXXXXX",
     ".gemini-a72-cpu9-progress-errno-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 progress errno executor derivation: expected "
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
