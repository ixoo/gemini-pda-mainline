#!/usr/bin/env bash

# Source-pin the reviewed platform-state-only builder and retarget it to the
# exact Stage-27 DT plus minimum provider-contract derivative.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=a3f15ca3a29d41ceafde524ff7beff671c9587cb24fd383fb6473985b3b55b9d
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-24-mainline-a72-platform-state-only/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-platform-stage27.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
replacements = (
    ("8e806c5305b6a2808fab59d3a25739d39cd3196a3498a1af21136dd7221923e1", "57e11e4392edfdb9fa695ac3f87b82aad4043bc2a61b78646bf97344bae101fd", 1),
    ("f3210fb38f9d3d5a61e23d60dc7f9d65b05b0a08cd5ef15033786a4f1bc50aff", "70ca589dbfc7649c38648a008e5197702295f396610ee2336fef5325f31b9546", 1),
    ("012f7eac6884e65baab075ef286929f610a63f2ea065eba45865bd046492a23f", "662e86846e783cf29b13c388f9e88217fe7bd32933eef4f32df86e44def0b16b", 1),
    ("readonly BOOT_NAME=gemini-a72plat", "readonly BOOT_NAME=gemini-a72min", 1),
    ("gemini-mt6797-a72-platform-only.boot.img", "gemini-mt6797-a72-platform-state-stage27-control.boot.img", 1),
    (".a72-platform-state-only.XXXXXXXX", ".a72-platform-state-stage27.XXXXXXXX", 1),
    ("portable-fetched-a72-early-package-with-platform-state-only-dtb", "portable-fetched-a72-early-package-with-stage27-minimum-platform-state-dtb", 2),
    ("experiment=2026-08-24-mainline-a72-platform-state-only", "experiment=2026-08-24-mainline-a72-platform-state-stage27-control", 1),
    ("runtime_hypothesis=first-read-only-platform-state-source-probes-with-serviceability", "runtime_hypothesis=minimum-platform-state-contract-probes-on-exact-stage27-serviceability-baseline", 1),
    ("dtb_delta_from_failed_physical_source=disable-clock-bigidvfs-observer", "dtb_delta_from_positive_stage27_control=add-only-platform-state-spm-syscon-watchdog-reset-contracts", 1),
    ('output_name="candidate-a72-platform-state-only-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-platform-state-stage27-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-platform-state-only-candidate-build", "validation=a72-platform-state-stage27-candidate-build", 1),
    ("control_dtb_source=exact-current-physical-source-with-only-platform-state-enabled", "control_dtb_source=exact-stage27-plus-minimum-platform-state-contracts", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe Stage-27 provider builder derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
Path(sys.argv[2]).write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived"
set +e
/bin/bash "$derived" "$@"
status=$?
set -e
cleanup
trap - EXIT HUP INT TERM
exit "$status"
