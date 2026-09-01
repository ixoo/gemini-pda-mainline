#!/usr/bin/env bash

# Source-pin the proven CPU9 progress collector and retarget its exact
# candidate, tooling identities, and private evidence namespace.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=fb8a37fb13b1fc8b76551301dc6b9985eafbfb94c68c6031d4048886fc911b33
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
source_collector="$script_dir/collect-progress-pretrigger.sh"
[[ -f "$source_collector" && ! -L "$source_collector" ]] || \
	die 'source CPU9 progress collector is missing or unsafe'
[[ "$(sha256sum "$source_collector" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || \
	die 'source CPU9 progress collector changed'

derived=$(mktemp "$script_dir/.derived-collect-a72-cpu9-mapping-fix.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_collector" "$derived" <<'PY'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("ce154daf63033fa235c4630365d5d12027d7c024fec3e9732ca07ac8ff9bbb72",
     "c531a9e05ae6f2d51211d73fb487efbaef235cfede195ba135e819bd4f2575c0", 1),
    ("ed6bbde65f0ce7dd0c5dd4bb53e1535c3cb624671b12904f27fe62edf03b5f99",
     "f284a4a27b84f87515f52fa68ade902cf7bf1920cd37ceeecb1d021fbbe99e63", 1),
    ("5f010324729e4735b3e6df2fdbe2333cec88e3acdbe36b86cf36ba8ab8c7b2cb",
     "1ae99b70ce93e139e2d27865683aec995af17ba432f8a707051543d1163d66e5", 1),
    ("4ad80105fd840ea02ca57c3dff1dd9fbe10b81047d06169b3981f4caa130867e",
     "26fac1ea17aec094ba09c466956c4ccacab61f5e6ecc6aac2d1d385ab1597a7f", 1),
    ("__GEMINI_A72_CPU9_PROGRESS_PRETRIGGER_SCRIPT__",
     "__GEMINI_A72_CPU9_MAPPING_FIX_PRETRIGGER_SCRIPT__", 1),
    ("remote-progress-pretrigger.sh", "remote-mapping-fix-pretrigger.sh", 1),
    ("validate-progress-pretrigger.py", "validate-mapping-fix-pretrigger.py", 1),
    ("a72-cpu9-progress-attempt-pretrigger-attempt-1",
     "a72-cpu9-mapping-fix-pretrigger-attempt-1", 1),
    (".gemini-a72-cpu9-progress-probe.XXXXXXXX",
     ".gemini-a72-cpu9-mapping-fix-probe.XXXXXXXX", 1),
    (".gemini-a72-cpu9-progress-command.XXXXXXXX",
     ".gemini-a72-cpu9-mapping-fix-command.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe CPU9 mapping-fix collector derivation: expected {count}, "
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
