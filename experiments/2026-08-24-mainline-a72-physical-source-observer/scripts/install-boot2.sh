#!/usr/bin/env bash

# Source-pin the guarded two-record installer and retarget only its exact
# physical-source candidate, evidence names, and experiment identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=715b444c9e76863d77de1995fd1be207de7f382a5cbebedfe8551f894cb69630

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required host command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_installer="$repo_root/experiments/2026-08-23-mainline-protected-clock-first-dmesg-call/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived=$(mktemp "$script_dir/.derived-install-boot2-a72-physical-source.XXXXXXXX")
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
        "# Source-pin the guarded installer and retarget only its exact one-read\n"
        "# candidate, evidence names, and experiment identity.",
        "# Source-pin the guarded two-record installer and retarget only its exact\n"
        "# physical-source candidate, evidence names, and experiment identity.",
        1,
    ),
    (
        ".derived-install-boot2-protected-clock.XXXXXXXX",
        ".derived-install-boot2-a72-physical-source.XXXXXXXX",
        2,
    ),
    ("exact one-read protected-clock", "exact A72 physical-source", 1),
    (
        "3892e776c183027851d73bec8bf938732c43ddad030a80ddee42240537ba35f6",
        "aa02ab666e63e7011139c1057bda99cdbab89245d41f9cad59dae30743b41246",
        1,
    ),
    (
        "649175a1d5c80c6d7b44e8b3f009c157dc9f017dbbd746f047fb1075a60dc93a",
        "683adfea30e7b7c82eb304705fe699b579ebbb0525c38ee57b296df75f0652ed",
        1,
    ),
    (
        "candidate-protected-clock-first-dmesg-d71c1f7e",
        "candidate-a72-physical-source-1d0c1420",
        1,
    ),
    (
        "protected-clock-first-dmesg-deployment-",
        "a72-physical-source-deployment-",
        1,
    ),
    (
        r"\.gemini-protected-clock-first-dmesg\.",
        r"\.gemini-a72-physical-source\.",
        1,
    ),
    (
        "/home/gemini/.gemini-protected-clock-first-dmesg.XXXXXXXX",
        "/home/gemini/.gemini-a72-physical-source.XXXXXXXX",
        1,
    ),
    (
        "experiment=2026-08-23-mainline-protected-clock-first-dmesg-call",
        "experiment=2026-08-24-mainline-a72-physical-source-observer",
        1,
    ),
    (
        "unsafe protected-clock installer derivation",
        "unsafe A72 physical-source installer derivation",
        2,
    ),
    (
        "live protected-clock preflight failed",
        "live A72 physical-source preflight failed",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe physical-source installer derivation: expected {count}, "
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
