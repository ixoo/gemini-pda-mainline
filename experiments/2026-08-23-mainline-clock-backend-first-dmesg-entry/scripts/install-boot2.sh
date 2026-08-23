#!/usr/bin/env bash

# Source-pin the guarded two-record installer and retarget only its exact
# candidate, evidence names, and experiment identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=e2cf4006ae224b65ac2ec570b494a064079cf5541db2f5a2df6f4dbab0678bd8

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-22-mainline-first-dmesg-raw-write-qualification/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived="$(mktemp "$script_dir/.derived-install-boot2-clock-entry.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_installer" "$derived" <<'PY'
from pathlib import Path
import sys


source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    (
        ".derived-install-boot2-first-dmesg.XXXXXXXX",
        ".derived-install-boot2-clock-entry.XXXXXXXX",
        1,
    ),
    (
        "# Source-pin and derive the guarded installer for the exact first-dmesg\\n",
        "# Source-pin and derive the guarded installer for the exact clock-entry\\n",
        1,
    ),
    (
        "b96ec109b3f020fdaf0cdc6ca1733d012051e6607b5520a11d32a6441f569e96",
        "40b7c663b835bcf4c48f4149f14aa416343e3e322ab78a0aa38448afff9455b4",
        1,
    ),
    (
        "d6df5940e4b6f471363bb853c9be14679b4d8934055f15a90de5b31c5b42b945",
        "e19c8662b9e9f848bde83a9bd64e076b121c0bb6dcc43f9890404888e4b14243",
        1,
    ),
    (
        "candidate-first-dmesg-raw-write-bcb8b61a",
        "candidate-clock-entry-first-dmesg-251e7925",
        1,
    ),
    (
        "first-dmesg-raw-write-deployment-",
        "clock-entry-first-dmesg-deployment-",
        1,
    ),
    (
        r"\.gemini-first-dmesg-raw-write\.",
        r"\.gemini-clock-entry-first-dmesg\.",
        1,
    ),
    (
        "/home/gemini/.gemini-first-dmesg-raw-write.XXXXXXXX",
        "/home/gemini/.gemini-clock-entry-first-dmesg.XXXXXXXX",
        1,
    ),
    (
        "experiment=2026-08-22-mainline-first-dmesg-raw-write-qualification",
        "experiment=2026-08-23-mainline-clock-backend-first-dmesg-entry",
        1,
    ),
    ("unsafe first-dmesg installer derivation", "unsafe clock-entry installer derivation", 1),
    ("live first-dmesg preflight failed", "live clock-entry preflight failed", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe clock-entry wrapper derivation: expected {count}, found {actual}: {old}"
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
