#!/usr/bin/env bash

# Source-pin the guarded installer and retarget only its exact one-read
# candidate, evidence names, and experiment identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=217eadb881a280d654fe8293458674d41b2c25b5202abbabf15722fddef587fe

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-23-mainline-clock-backend-cspm-coexistence/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived="$(mktemp "$script_dir/.derived-install-boot2-protected-clock.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("# Source-pin the guarded installer and retarget only its exact coexistence\n# candidate, evidence names, and experiment identity.",
     "# Source-pin the guarded installer and retarget only its exact one-read\n# candidate, evidence names, and experiment identity.", 1),
    (".derived-install-boot2-clock-cspm.XXXXXXXX", ".derived-install-boot2-protected-clock.XXXXXXXX", 2),
    ("exact clock/CSPM coexistence", "exact one-read protected-clock", 1),
    ("ae4010449e72ed4d02643616073e8d74f7cad25adb4afb5db69030d39eb324e7", "3892e776c183027851d73bec8bf938732c43ddad030a80ddee42240537ba35f6", 1),
    ("afdb8215a6035af7a4bb1b963dcc48c4c1cd94cd184cf3570708eb6392db2834", "649175a1d5c80c6d7b44e8b3f009c157dc9f017dbbd746f047fb1075a60dc93a", 1),
    ("candidate-clock-cspm-coexistence-dc093771", "candidate-protected-clock-first-dmesg-d71c1f7e", 1),
    ("clock-cspm-coexistence-deployment-", "protected-clock-first-dmesg-deployment-", 1),
    (r"\.gemini-clock-cspm-coexistence\.", r"\.gemini-protected-clock-first-dmesg\.", 1),
    ("/home/gemini/.gemini-clock-cspm-coexistence.XXXXXXXX", "/home/gemini/.gemini-protected-clock-first-dmesg.XXXXXXXX", 1),
    ("experiment=2026-08-23-mainline-clock-backend-cspm-coexistence", "experiment=2026-08-23-mainline-protected-clock-first-dmesg-call", 1),
    ("unsafe clock/CSPM installer derivation", "unsafe protected-clock installer derivation", 1),
    ("live clock/CSPM preflight failed", "live protected-clock preflight failed", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe protected-clock installer derivation: expected {count}, "
            f"found {actual}: {old}"
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
