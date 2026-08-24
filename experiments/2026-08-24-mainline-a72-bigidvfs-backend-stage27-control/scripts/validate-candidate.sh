#!/usr/bin/env bash

# Source-pin the independent passed clock-backend validator and specialize
# only its DT, layout, names, and exact candidate identities.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=5e4cd66be21839a9fbce8483f579e14813a21f23a76c8440874fd95cc06c1135
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_validator="$repo_root/experiments/2026-08-24-mainline-a72-clock-backend-stage27-control/scripts/validate-candidate.sh"
[[ -f "$source_validator" && ! -L "$source_validator" ]] || die 'source validator is missing or unsafe'
[[ "$(sha256sum "$source_validator" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source validator changed'

derived=$(mktemp "$script_dir/.derived-validate-a72-bigidvfs-stage27.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_validator" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("5f5cd8b8af73cc1ae77887bb5761b8f1cc6b62e7028a6da24d6f9a3d0f22ab4f", "d439ed8f4c226eda49f5bf652f16761ba3400bd0b80685bfc8f8da371d6ed9db", 1),
    ("KERNEL_FIELD_SIZE = 4_832_094", "KERNEL_FIELD_SIZE = 4_832_210", 1),
    ("2ec5bd0751b71ba250a0b0e0e6d519d32375d6c445cc51a514d452fac51c995c", "2abb81d0ab24dc83c4e1526d0564fdd235db202d0db95a869912e1abb31f30ba", 1),
    ("4c5276ecf3fe60d7df55fd1fe44235432fcd928d2174704e5928bae7d84056e4", "0b17da983293f68f227931c964021b43efb1cdd57b4d0cf4db3bd70312f6092a", 1),
    ("gemini-mt6797-a72-clock-backend-stage27-control.boot.img", "gemini-mt6797-a72-bigidvfs-backend-stage27-control.boot.img", 1),
    ('b"gemini-a72clk"', 'b"gemini-a72big"', 1),
    ("validation=a72-clock-backend-stage27-candidate", "validation=a72-bigidvfs-backend-stage27-candidate", 1),
    ('print("control_dtb=passed-stage27-platform-plus-read-free-clock-backend")', 'print("control_dtb=passed-stage27-platform-clock-plus-read-free-bigidvfs-backend")', 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe BigiDVFS validator derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
result=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$result"
