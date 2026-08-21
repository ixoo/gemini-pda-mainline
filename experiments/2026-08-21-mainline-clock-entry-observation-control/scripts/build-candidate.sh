#!/usr/bin/env bash

# Source-pin the clock-entry candidate builder and select the exact package's
# base DTB as the live driver-registration observation control.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=91acbc5977cb361ce835f6f609775dab84649ec57d320ca9473b663f4b531a6d

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-21-mainline-clock-backend-entry-ledger/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] ||
	die 'source builder missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] ||
	die 'source builder identity changed'

derived="$(mktemp "$script_dir/.clock-entry-control-builder.XXXXXXXX")"
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    (
        "readonly DTB_SHA256=d93cba886584ebf3f9b30a9341f4dbea8f90fb35745200464265449a7811c920",
        "readonly DTB_SHA256=dad6997c565d10dcacab23dea46166ac45f6594da2aab697b105b3fb2dcc474e",
        1,
    ),
    (
        "readonly RAW_SHA256=1c5a410b07b0fd971b2105f14cb97dea05168c5d5cf73dc67a47c2892a171768",
        "readonly RAW_SHA256=a36425f3e9cec23ff9281d9151e54ce780ff5abc8d98aa8df190a300a786eb4e",
        1,
    ),
    (
        "readonly PADDED_SHA256=444ffc4a3631e75d05e567f6304fdd1607695adbd1f3c8b5654714633e6278de",
        "readonly PADDED_SHA256=fc2a9a1a53de1373cf75d14f163a5b9921219996882f58e0b5395595872230bf",
        1,
    ),
    (
        "readonly BOOT_FILE=gemini-mt6797-clock-backend-entry.boot.img",
        "readonly BOOT_FILE=gemini-mt6797-clock-entry-control.boot.img",
        1,
    ),
    (
        'dtb="$package/dtbs/mediatek/mt6797-gemini-pda-clock-backend-entry.dtb"',
        'dtb="$package/dtbs/mediatek/mt6797-gemini-pda.dtb"',
        1,
    ),
    ("'clock-backend entry candidate DTB'", "'clock-entry observation-control DTB'", 1),
    (".clock-backend-entry-candidate.", ".clock-entry-control-candidate.", 1),
    (
        "validation=portable-fetched-clock-backend-entry-kernel-package",
        "validation=portable-fetched-clock-entry-observation-control-package",
        1,
    ),
    (
        "experiment=2026-08-21-mainline-clock-backend-entry-ledger",
        "experiment=2026-08-21-mainline-clock-entry-observation-control",
        1,
    ),
    (
        "runtime_hypothesis=clock-driver-init-and-probe-entry-retained-records",
        "runtime_hypothesis=driver-init-live-registration-control-with-clock-node-disabled",
        1,
    ),
    (
        'output_name="candidate-clock-backend-entry-${RAW_SHA256:0:8}"',
        'output_name="candidate-clock-entry-control-${RAW_SHA256:0:8}"',
        1,
    ),
    (
        "validation=clock-backend-entry-ledger-candidate-build",
        "validation=clock-entry-observation-control-candidate-build",
        1,
    ),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe control builder derivation: expected {count} occurrences, "
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
