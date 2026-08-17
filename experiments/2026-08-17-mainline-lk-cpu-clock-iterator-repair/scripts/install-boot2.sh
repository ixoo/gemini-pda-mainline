#!/usr/bin/env bash

# Source-pin and derive the guarded installer for the exact LK CPU-clock
# iterator repair candidate. The inherited policy resolves live GPT boot2,
# records but does not back up the predecessor, verifies a full readback, and
# powers off after success.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=571c540e064143544a22f71df28528ac47ac2fea521cde823b3113c7254292d7

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in awk chmod dirname mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-17-mainline-i2c5-serviceability-restoration/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived="$(mktemp "$script_dir/.derived-install-boot2.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("coherent I2C5/AW9523 polling-keyboard serviceability candidate",
     "LK CPU-clock iterator repair candidate", 2),
    ("8d04c2c7e9c67dcd17189422d1968e416eb9eec304e2b9300b83f48dc9e0ebb5",
     "b478b79a983889514b2b8d122fb6d5ff5057e52c332882b186b82698d1de62b8", 1),
    ("9a05fd5ea6266d04595307575425e296b476dc2cfdf478a87ca402b4108ed143",
     "fdb6a6c4619a046e9d2763f77368fd11ead57ed1a32b8d0d5cccae0eb8789235", 1),
    ("candidate-mainline-i2c5-serviceability-e115127d",
     "candidate-mainline-lk-cpu-clock-repair-fe22ae35", 1),
    ("mainline-i2c5-serviceability-deployment-",
     "mainline-lk-cpu-clock-repair-deployment-", 1),
    (r"\.gemini-mainline-i2c5-serviceability\.",
     r"\.gemini-mainline-lk-cpu-clock-repair\.", 1),
    ("/home/gemini/.gemini-mainline-i2c5-serviceability.XXXXXXXX",
     "/home/gemini/.gemini-mainline-lk-cpu-clock-repair.XXXXXXXX", 1),
    ("experiment=2026-08-17-mainline-i2c5-serviceability-restoration",
     "experiment=2026-08-17-mainline-lk-cpu-clock-iterator-repair", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe installer derivation: expected {count} occurrences, found {actual}: {old}"
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
