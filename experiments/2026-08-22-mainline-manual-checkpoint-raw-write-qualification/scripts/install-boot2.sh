#!/usr/bin/env bash

# Source-pin the guarded mapping-control installer and specialize its exact
# live-GPT boot2 write/readback/shutdown workflow for the raw-write candidate.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=75bcc25f7546e53285875367446847a98f60fd208982f33ad4c4158fcc5b8fda

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-22-mainline-manual-checkpoint-map-control/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] || die 'source installer missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived="$(mktemp "$script_dir/.derived-install-boot2-manual-raw-write.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM

python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("dd513384c78ee8378e1e4bf515f89b99ca87ed6ed86c1d38ec37f8aadd693b5b",
     "c10f2c03490fe1aa8ded11895a2d1817dd649edaffa307d0635fe2d69ce1c631", 1),
    ("af056a2eea1c410b68688b3d4b385d1b6f53d5e3fca3c12f66893eee6fccdbad",
     "65c6c3a48c2cbef17f48e816d7d05a5c6c03adf0eee1bbbe6ea4587ed099385e", 1),
    ("candidate-manual-checkpoint-map-control-ecd021b2",
     "candidate-manual-checkpoint-raw-write-6a2f698f", 1),
    ("manual-checkpoint-map-control-deployment-",
     "manual-checkpoint-raw-write-deployment-", 1),
    (r"\.gemini-manual-checkpoint-map-control\.",
     r"\.gemini-manual-checkpoint-raw-write\.", 1),
    ("/home/gemini/.gemini-manual-checkpoint-map-control.XXXXXXXX",
     "/home/gemini/.gemini-manual-checkpoint-raw-write.XXXXXXXX", 1),
    ("experiment=2026-08-22-mainline-manual-checkpoint-map-control",
     "experiment=2026-08-22-mainline-manual-checkpoint-raw-write-qualification", 1),
    (".derived-install-boot2-manual-map-inner.XXXXXXXX",
     ".derived-install-boot2-manual-raw-write-inner.XXXXXXXX", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe raw-write installer derivation: expected {count}, found {actual}: {old}"
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
