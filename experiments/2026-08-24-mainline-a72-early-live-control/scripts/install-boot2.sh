#!/usr/bin/env bash

# Source-pin the guarded early-initcall installer and retarget only its exact
# Stage-27-DTB live-control candidate, evidence names, and experiment identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=c057570db33590b6496c9647a86c6141fc34ca476bc6df619ecf293ee61a2628

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-24-mainline-a72-early-initcall-ledger/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-early-live.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("exact\n# early-initcall candidate", "exact\n# Stage-27-DTB live-control candidate", 1),
    (".derived-install-boot2-a72-early-initcall.XXXXXXXX", ".derived-install-boot2-a72-early-live.XXXXXXXX", 2),
    ("exact A72 early-initcall", "exact A72 early live control", 1),
    ("d2951eade3c08c889ecaeb1376f85262c44ad729048ddc3164c1db39acced609", "070e0ff4b019dd35e91ba91413b9ae958cf5e71e3573ed81bc9dd7d1cf3cc4ef", 1),
    ("7e2c47c9f46e24b0778848bdeec5b303ab0674b5b336cd812fae4336833a0b5f", "0751ffc0200f7062590e825feb8892537f024641ffea7d647dd6375f5206bd05", 1),
    ("candidate-a72-early-initcall-8bff9059", "candidate-a72-early-live-control-32ff42b3", 1),
    ("a72-early-initcall-deployment-", "a72-early-live-control-deployment-", 1),
    (r"\.gemini-a72-early-initcall\.", r"\.gemini-a72-early-live-control\.", 1),
    ("/home/gemini/.gemini-a72-early-initcall.XXXXXXXX", "/home/gemini/.gemini-a72-early-live-control.XXXXXXXX", 1),
    ("experiment=2026-08-24-mainline-a72-early-initcall-ledger", "experiment=2026-08-24-mainline-a72-early-live-control", 1),
    ("unsafe early-initcall installer derivation", "unsafe early-live-control installer derivation", 2),
    ("live A72 early-initcall preflight failed", "live A72 early-live-control preflight failed", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe live-control installer derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"

set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
