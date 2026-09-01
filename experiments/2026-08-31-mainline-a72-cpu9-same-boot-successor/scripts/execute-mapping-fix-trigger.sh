#!/usr/bin/env bash

# Source-pin the proven one-shot CPU9 progress executor and retarget its exact
# mapping-fix candidate, tooling identities, and evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=64c84a17d8c2618629ec22b832fa801c05447d47abc9754ab061542e47e0b29d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_executor="$script_dir/execute-progress-trigger.sh"
[[ -f "$source_executor" && ! -L "$source_executor" ]] || \
	die 'source CPU9 progress executor is missing or unsafe'
[[ "$(sha256sum "$source_executor" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source CPU9 progress executor changed'

derived=$(mktemp "$script_dir/.derived-execute-a72-cpu9-mapping-fix.XXXXXXXX")
cleanup() { rm -f -- "${derived:-}"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_executor" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72",
     "c531a9e05ae6f2d51211d73fb487efbaef235cfede195ba135e819bd4f2575c0", 1),
    ("2e8a307a837741ead989284b3c74832504a7c4e64fbf55c9b0b2e3dc4878a609",
     "238c13324008dcfb1e9d79f09fa97beded98536168267b4d4074fb3c0882916a", 1),
    ("90e58cb4b7223cc038023cbf3f89ca351fbd805bbacd465d00ac1b95bcf21943",
     "c72ec553233aba2a1c425d416c9d2da49c7d5045a840560ad473f04d82b335b3", 1),
    ("4ad80105fd840ea02ca57c3dff1dd9fbe10b81047d06169b3981f4caa130867e",
     "26fac1ea17aec094ba09c466956c4ccacab61f5e6ecc6aac2d1d385ab1597a7f", 1),
    ("a72-cpu9-progress-attempt-pretrigger-attempt-1",
     "a72-cpu9-mapping-fix-pretrigger-attempt-1", 1),
    ('trigger_wrapper="$script_dir/remote-progress-trigger.sh"',
     'trigger_wrapper="$script_dir/remote-mapping-fix-trigger.sh"', 1),
    ('classifier="$script_dir/classify-progress-attempt.py"',
     'classifier="$script_dir/classify-mapping-fix-attempt.py"', 1),
    ('validator="$script_dir/validate-progress-pretrigger.py"',
     'validator="$script_dir/validate-mapping-fix-pretrigger.py"', 1),
    (".gemini-a72-cpu9-progress-validation.XXXXXXXX",
     ".gemini-a72-cpu9-mapping-fix-validation.XXXXXXXX", 1),
    (".gemini-a72-cpu9-progress-trigger.XXXXXXXX",
     ".gemini-a72-cpu9-mapping-fix-trigger.XXXXXXXX", 1),
    (".gemini-a72-cpu9-progress-command.XXXXXXXX",
     ".gemini-a72-cpu9-mapping-fix-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 mapping-fix executor derivation: expected {count}, "
            f"found {actual}: {old}"
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
