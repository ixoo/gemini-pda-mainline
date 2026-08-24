#!/usr/bin/env bash

# Source-pin the exact passed platform-state builder and add only the isolated
# read-free clock-backend DT identity.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=fe6d84bed40362b0cc04077a60af6f129fca2914f74afdaaba7098b16d4c5ecc
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-24-mainline-a72-platform-state-stage27-control/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-clock-stage27.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("57e11e4392edfdb9fa695ac3f87b82aad4043bc2a61b78646bf97344bae101fd", "5f5cd8b8af73cc1ae77887bb5761b8f1cc6b62e7028a6da24d6f9a3d0f22ab4f", 1),
    ("70ca589dbfc7649c38648a008e5197702295f396610ee2336fef5325f31b9546", "2ec5bd0751b71ba250a0b0e0e6d519d32375d6c445cc51a514d452fac51c995c", 1),
    ("662e86846e783cf29b13c388f9e88217fe7bd32933eef4f32df86e44def0b16b", "4c5276ecf3fe60d7df55fd1fe44235432fcd928d2174704e5928bae7d84056e4", 1),
    ("readonly BOOT_NAME=gemini-a72min", "readonly BOOT_NAME=gemini-a72clk", 1),
    ("gemini-mt6797-a72-platform-state-stage27-control.boot.img", "gemini-mt6797-a72-clock-backend-stage27-control.boot.img", 1),
    (".a72-platform-state-stage27.XXXXXXXX", ".a72-clock-backend-stage27.XXXXXXXX", 1),
    ("portable-fetched-a72-early-package-with-stage27-minimum-platform-state-dtb", "portable-fetched-a72-early-package-with-stage27-platform-and-clock-probes", 1),
    ("experiment=2026-08-24-mainline-a72-platform-state-stage27-control", "experiment=2026-08-24-mainline-a72-clock-backend-stage27-control", 1),
    ("runtime_hypothesis=minimum-platform-state-contract-probes-on-exact-stage27-serviceability-baseline", "runtime_hypothesis=read-free-clock-backend-probes-on-passed-stage27-platform-baseline", 1),
    ("dtb_delta_from_positive_stage27_control=add-only-platform-state-spm-syscon-watchdog-reset-contracts", "dtb_delta_from_positive_platform_state=add-only-clock-backend-resource-node", 1),
    ('output_name="candidate-a72-platform-state-stage27-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-clock-backend-stage27-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-platform-state-stage27-candidate-build", "validation=a72-clock-backend-stage27-candidate-build", 1),
    ("control_dtb_source=exact-stage27-plus-minimum-platform-state-contracts", "control_dtb_source=passed-stage27-platform-plus-read-free-clock-backend", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe clock-backend builder derivation: expected {count}, found {actual}: {old}")
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
