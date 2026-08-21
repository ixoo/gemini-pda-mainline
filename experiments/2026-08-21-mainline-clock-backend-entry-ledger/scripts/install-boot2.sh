#!/usr/bin/env bash

# Source-pin the guarded probe/gate installer for the exact clock-backend
# entry-ledger candidate and retain its bounded live empty-slot preflight.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=d5bf8cb064c5937adc622c723d3650fd79826baca11f13b08e9ac179e9122703

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-21-mainline-protected-readback-probe-gate-ledger/scripts/install-boot2.sh"
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
        "# Source-pin the guarded call-ledger installer for the exact probe/gate-ledger\n"
        "# candidate and retain its bounded live empty-slot preflight before delegation.",
        "# Source-pin the guarded call-ledger installer for the exact clock-backend\n"
        "# entry-ledger candidate and retain its bounded live empty-slot preflight.",
        1,
    ),
    (
        "6cb729efacea914b993221f0f85a1ab7e67eb6bca915802a8236bb31edab2e62",
        "444ffc4a3631e75d05e567f6304fdd1607695adbd1f3c8b5654714633e6278de",
        1,
    ),
    (
        "57144fa24ad69a6b2b69817fad86c66c0dda0eed1bf1b005db13cfa01748854a",
        "59cfa6fcaf511a7ec0889861c981c4c679e11cea2b239f336b3eaa3bc1b6bd66",
        1,
    ),
    (
        "candidate-protected-readback-probe-gate-c04de416",
        "candidate-clock-backend-entry-1c5a410b",
        1,
    ),
    (
        "protected-readback-probe-gate-ledger-deployment-",
        "clock-backend-entry-ledger-deployment-",
        1,
    ),
    (
        r"\.gemini-protected-readback-probe-gate\.",
        r"\.gemini-clock-backend-entry\.",
        1,
    ),
    (
        "/home/gemini/.gemini-protected-readback-probe-gate.XXXXXXXX",
        "/home/gemini/.gemini-clock-backend-entry.XXXXXXXX",
        1,
    ),
    (
        "experiment=2026-08-21-mainline-protected-readback-probe-gate-ledger",
        "experiment=2026-08-21-mainline-clock-backend-entry-ledger",
        1,
    ),
    (
        ".derived-install-boot2-probe-gate-ledger.XXXXXXXX",
        ".derived-install-boot2-clock-entry-inner.XXXXXXXX",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe clock-entry installer derivation: expected {count} occurrences, "
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
