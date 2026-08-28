#!/usr/bin/env bash

# Source-pin the exact guarded softtrace installer and retarget only the
# serviceability-corrected candidate, predecessor, evidence, and experiment.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=ca866ec9263dbcb628c0caef79aafa2c3f933e08971eafa3fbcb97ac91f6aa6d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-28-mainline-a72-admission-trace-softfail/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer changed'

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-softtrace-serviceable.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("83dec18625b82289a2dad9ba6c59d43a2f81f48ffbaca752cc2200f3b1facdf0",
     "df82bbfa012a994642a145beee994125cc9069092aad22e6af0321dfb7202f60", 1),
    ("dec15778248b91bd4a2159ae677fad7d9c0ce5ef7c5ca77aa2915ef7985b13fd",
     "5fbb91bc08497bebb82514f3dc72d92352cacbe20051cae2ca5620c269868a55", 1),
    ("fd611a4ca87fd1645e2fa75b3927d56e9e7eac89f3d84712e5555a3aab8f4cf0",
     "83dec18625b82289a2dad9ba6c59d43a2f81f48ffbaca752cc2200f3b1facdf0", 1),
    ("candidate-a72-admission-softtrace-9d1912aa",
     "candidate-a72-admission-softtrace-serviceable-8dbc6642", 1),
    ('("a72-admission-trace", "a72-admission-softtrace", 5)',
     '("a72-admission-trace", "a72-admission-softtrace-serviceable", 5)', 1),
    ("2026-08-28-mainline-a72-admission-trace-softfail",
     "2026-08-28-mainline-a72-admission-softtrace-serviceable", 1),
    (".derived-install-boot2-a72-admission-softtrace.XXXXXXXX",
     ".derived-install-boot2-a72-softtrace-serviceable-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe serviceable-softtrace installer derivation: expected {count}, "
            f"found {actual}: {old}"
        )
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
