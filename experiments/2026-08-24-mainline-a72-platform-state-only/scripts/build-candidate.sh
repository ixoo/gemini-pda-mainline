#!/usr/bin/env bash

# Source-pin the exact current-kernel live-control builder and specialize its
# DTB, names, hypothesis, and candidate identities for platform-state only.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=168d7ab304bb508f25ac7d0d8c3f2421ac2ae487556643ce3b8ab88ac633304a
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
for command in chmod mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
source_builder="$repo_root/experiments/2026-08-24-mainline-a72-early-live-control/scripts/build-candidate.sh"
[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is missing or unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'source builder changed'

derived=$(mktemp "$script_dir/.derived-build-a72-platform-only.XXXXXXXX")
cleanup() { [[ ! -e "${derived:-}" ]] || rm -f -- "$derived"; }
trap cleanup EXIT HUP INT TERM
python3 - "$source_builder" "$derived" <<'PY'
from pathlib import Path
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")
gzip_tuple = '    ("539f83bf4e6f31e21edacde26399ea285c1e87cdf4df25fb2896d364822a89fe", "00992be8c2ccb222c42eecfd92c43b81305f12d756cc2e2a7fc533299e2ce293", 1),'
inserted = gzip_tuple + '\n    ("7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806", "8e806c5305b6a2808fab59d3a25739d39cd3196a3498a1af21136dd7221923e1", 1),'
replacements = (
    (gzip_tuple, inserted, 1),
    ("32ff42b3e8ba07e5b0267b521118f906aa27bd737613ae76a119961d3acc9e0d", "f3210fb38f9d3d5a61e23d60dc7f9d65b05b0a08cd5ef15033786a4f1bc50aff", 1),
    ("070e0ff4b019dd35e91ba91413b9ae958cf5e71e3573ed81bc9dd7d1cf3cc4ef", "012f7eac6884e65baab075ef286929f610a63f2ea065eba45865bd046492a23f", 1),
    ("readonly BOOT_NAME=gemini-a72live", "readonly BOOT_NAME=gemini-a72plat", 1),
    ("readonly BOOT_FILE=gemini-mt6797-a72-early-live-control.boot.img", "readonly BOOT_FILE=gemini-mt6797-a72-platform-only.boot.img", 1),
    (".a72-early-live-control.XXXXXXXX", ".a72-platform-state-only.XXXXXXXX", 1),
    ("portable-fetched-a72-early-package-with-runtime-proven-dtb-control", "portable-fetched-a72-early-package-with-platform-state-only-dtb", 1),
    ("experiment=2026-08-24-mainline-a72-early-live-control", "experiment=2026-08-24-mainline-a72-platform-state-only", 1),
    ("runtime_hypothesis=exact-current-kernel-reaches-live-usb-with-runtime-proven-stage27-dtb", "runtime_hypothesis=first-read-only-platform-state-source-probes-with-serviceability", 1),
    ("kernel_delta_from_retired_early_initcall=none", "kernel_delta_from_positive_stage27_control=none", 1),
    ("dtb_delta_from_retired_early_initcall=exact-runtime-proven-stage27-dtb", "dtb_delta_from_failed_physical_source=disable-clock-bigidvfs-observer", 1),
    ('output_name="candidate-a72-early-live-control-${RAW_SHA256:0:8}"', 'output_name="candidate-a72-platform-state-only-${RAW_SHA256:0:8}"', 1),
    ("validation=a72-early-live-control-candidate-build", "validation=a72-platform-state-only-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe platform-only builder derivation: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
needle = '    ("validation=portable-fetched-kernel-package-with-runtime-proven-dtb-control", "validation=portable-fetched-a72-early-package-with-platform-state-only-dtb", 1),'
addition = needle + '\n    ("control_dtb_source=runtime-proven-stage27-lifecycle", "control_dtb_source=exact-current-physical-source-with-only-platform-state-enabled", 2),'
if text.count(needle) != 1:
    raise SystemExit("unsafe platform-only builder provenance insertion")
text = text.replace(needle, addition)
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
