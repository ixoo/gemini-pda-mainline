#!/usr/bin/env bash

# Source-pin the guarded installer and retarget only its exact coexistence
# candidate, evidence names, and experiment identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a7273b2118aca4435f2e78631743ba800cd0bfd6bddd2df4bc51390435e852e5

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-23-mainline-clock-backend-first-dmesg-entry/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived="$(mktemp "$script_dir/.derived-install-boot2-clock-cspm.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    (".derived-install-boot2-clock-entry.XXXXXXXX", ".derived-install-boot2-clock-cspm.XXXXXXXX", 2),
    ("exact clock-entry", "exact clock/CSPM coexistence", 1),
    ("40b7c663b835bcf4c48f4149f14aa416343e3e322ab78a0aa38448afff9455b4", "ae4010449e72ed4d02643616073e8d74f7cad25adb4afb5db69030d39eb324e7", 1),
    ("e19c8662b9e9f848bde83a9bd64e076b121c0bb6dcc43f9890404888e4b14243", "afdb8215a6035af7a4bb1b963dcc48c4c1cd94cd184cf3570708eb6392db2834", 1),
    ("candidate-clock-entry-first-dmesg-251e7925", "candidate-clock-cspm-coexistence-dc093771", 1),
    ("clock-entry-first-dmesg-deployment-", "clock-cspm-coexistence-deployment-", 1),
    (r"\.gemini-clock-entry-first-dmesg\.", r"\.gemini-clock-cspm-coexistence\.", 1),
    ("/home/gemini/.gemini-clock-entry-first-dmesg.XXXXXXXX", "/home/gemini/.gemini-clock-cspm-coexistence.XXXXXXXX", 1),
    ("experiment=2026-08-23-mainline-clock-backend-first-dmesg-entry", "experiment=2026-08-23-mainline-clock-backend-cspm-coexistence", 1),
    ("unsafe clock-entry installer derivation", "unsafe clock/CSPM installer derivation", 1),
    ("live clock-entry preflight failed", "live clock/CSPM preflight failed", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe coexistence installer derivation: expected {count}, found {actual}: {old}"
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
