#!/usr/bin/env bash

# Source-pin the guarded clock-entry installer for the exact base-DTB live
# driver-registration control and retain its bounded empty-slot preflight.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=1b56a3ec721c94d97f9f70e3b7eafd6e30677911ef1a20d9d6c94a35dbed0b9e

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_installer="$repo_root/experiments/2026-08-21-mainline-clock-backend-entry-ledger/scripts/install-boot2.sh"
[[ -f "$source_installer" && ! -L "$source_installer" ]] ||
	die 'source installer is missing or unsafe'
[[ "$(sha256sum "$source_installer" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source installer identity changed'

derived="$(mktemp "$script_dir/.derived-install-boot2-clock-entry-control.XXXXXXXX")"
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
        "444ffc4a3631e75d05e567f6304fdd1607695adbd1f3c8b5654714633e6278de",
        "fc2a9a1a53de1373cf75d14f163a5b9921219996882f58e0b5395595872230bf",
        1,
    ),
    (
        "59cfa6fcaf511a7ec0889861c981c4c679e11cea2b239f336b3eaa3bc1b6bd66",
        "5932e3dd90903b48342126131ddd433107ed8d6b10c9d49b285cc9ccc383e9c3",
        1,
    ),
    (
        "candidate-clock-backend-entry-1c5a410b",
        "candidate-clock-entry-control-a36425f3",
        1,
    ),
    (
        "clock-backend-entry-ledger-deployment-",
        "clock-entry-observation-control-deployment-",
        1,
    ),
    (r"\.gemini-clock-backend-entry\.", r"\.gemini-clock-entry-control\.", 1),
    (
        "/home/gemini/.gemini-clock-backend-entry.XXXXXXXX",
        "/home/gemini/.gemini-clock-entry-control.XXXXXXXX",
        1,
    ),
    (
        "experiment=2026-08-21-mainline-clock-backend-entry-ledger",
        "experiment=2026-08-21-mainline-clock-entry-observation-control",
        1,
    ),
    (
        ".derived-install-boot2-clock-entry-inner.XXXXXXXX",
        ".derived-install-boot2-clock-entry-control-inner.XXXXXXXX",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe control installer derivation: expected {count} occurrences, "
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
