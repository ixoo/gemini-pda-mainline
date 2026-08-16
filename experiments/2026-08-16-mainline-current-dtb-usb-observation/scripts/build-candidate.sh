#!/usr/bin/env bash

# Reuse the exact validated GAEL assembler with a three-property USB DT.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'Usage: %s --package DIR --ramdisk FILE --base-dtb FILE --output-parent DIR\n' "$0"
}

package=
ramdisk=
base_dtb=
output_parent=
while [[ "$#" -gt 0 ]]; do
	case "$1" in
	--package) package=${2:-}; shift 2 ;;
	--ramdisk) ramdisk=${2:-}; shift 2 ;;
	--base-dtb) base_dtb=${2:-}; shift 2 ;;
	--output-parent) output_parent=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$package" && -n "$ramdisk" && -n "$base_dtb" && -n "$output_parent" ]] || {
	usage >&2
	exit 2
}
for command in awk chmod find install mktemp python3 rm sha256sum sort xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent/" in
"$repo_root/artifacts/"*) ;;
*) die 'output parent must be below the ignored artifacts root' ;;
esac

readonly SOURCE_BUILDER_SHA256=cb653690a9ab76d52fc40ea808d2df1bce107b19987616857f81b4f20abf3771
readonly DTB_BUILDER_SHA256=dbf8a99fc99f2f7cbd256495bb3d295b2c5bed9b627a9c60a338cfa518303efb
readonly OUTPUT_DTB_SHA256=e93264b32e0a42098fa6556e454abc99b75373e92e1e3b6eef50285542251331
readonly RAW_SHA256=a9d4f9516d761bfb30faf95e8b3d3f9e9d19282bc67d508fbc5ff308e84954be
readonly SOURCE_BUILDER="$repo_root/experiments/2026-08-16-mainline-lk-handoff-dtb-control/scripts/build-candidate.sh"
readonly DTB_BUILDER="$script_dir/build-usb-observation-dtb.sh"
readonly OUTPUT_NAME="candidate-current-dtb-usb-observation-${RAW_SHA256:0:8}"
readonly DTB_MEMBER=mt6797-gemini-pda-usb-observation.dtb

for input in "$SOURCE_BUILDER" "$DTB_BUILDER"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "source input is missing, empty, or unsafe: $input"
done
[[ "$(sha256sum "$SOURCE_BUILDER" | awk '{print $1}')" == \
	"$SOURCE_BUILDER_SHA256" ]] || die 'source candidate builder changed'
[[ "$(sha256sum "$DTB_BUILDER" | awk '{print $1}')" == \
	"$DTB_BUILDER_SHA256" ]] || die 'DTB builder changed'

workdir="$(mktemp -d "$output_parent/.current-dtb-usb-observation-wrapper.XXXXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
derived_dtb="$workdir/$DTB_MEMBER"
dtb_validation="$workdir/dtb-validation.txt"
"$DTB_BUILDER" --base-dtb "$base_dtb" --output "$derived_dtb" >"$dtb_validation"
[[ "$(sha256sum "$derived_dtb" | awk '{print $1}')" == "$OUTPUT_DTB_SHA256" ]] ||
	die 'derived DTB changed'

derived_builder="$workdir/build-candidate-derived.sh"
python3 - "$SOURCE_BUILDER" "$derived_builder" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("# Assemble the exact GAEL kernel with the runtime-proven Stage-27 DTB.",
     "# Assemble the exact GAEL kernel with the minimal current-DT USB observation path.", 1),
    ("readonly CONTROL_DTB_SHA256=7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806",
     "readonly CONTROL_DTB_SHA256=e93264b32e0a42098fa6556e454abc99b75373e92e1e3b6eef50285542251331", 1),
    ("readonly RAW_SHA256=e96d0cc2670bf4de6e0cc88d35d8814c5c3aa05442d0a5bd83818fa078ca2086",
     "readonly RAW_SHA256=a9d4f9516d761bfb30faf95e8b3d3f9e9d19282bc67d508fbc5ff308e84954be", 1),
    ("readonly PADDED_SHA256=68515e0ecbb073b4ee18b318bd869fd5b7dea1c3ac838681ceb42b7451dc1c67",
     "readonly PADDED_SHA256=fa107a988d860f017905c61a4b52110bc8dc3cc1ce5f407424fa3dd47c9b8b87", 1),
    ("readonly BOOT_NAME=gemini-dtbctl", "readonly BOOT_NAME=gemini-usbobs", 1),
    ("readonly BOOT_FILE=gemini-mt6797-arm64-entry-ledger-stage27-dtb.boot.img",
     "readonly BOOT_FILE=gemini-mt6797-arm64-entry-ledger-usb-observation.boot.img", 1),
    ("Stage-27 control DTB", "USB-observation DTB", 1),
    (".lk-handoff-dtb-control.XXXXXXXX", ".current-dtb-usb-observation.XXXXXXXX", 1),
    ("portable-fetched-kernel-package-with-runtime-proven-dtb-control",
     "portable-fetched-kernel-package-with-current-dtb-usb-observation", 1),
    ("control_dtb_sha256", "usb_observation_dtb_sha256", 2),
    ("control_dtb_source=runtime-proven-stage27-lifecycle",
     "usb_observation_dtb_source=current-package-plus-three-status-properties", 2),
    ("experiment=2026-08-16-mainline-lk-handoff-dtb-control",
     "experiment=2026-08-16-mainline-current-dtb-usb-observation", 1),
    ("runtime_hypothesis=stage27_dtb_distinguishes_lk_dtb_processing_from_image_entry",
     "runtime_hypothesis=three_status_properties_restore_live_usb_oracle_to_current_dtb", 1),
    ("dtb_delta_from_stopped_gael=exact-runtime-proven-stage27-dtb",
     "dtb_delta_from_stopped_gael=three-usb-status-properties-only", 1),
    ("candidate-lk-handoff-dtb-control-", "candidate-current-dtb-usb-observation-", 1),
    ("validation=lk-handoff-dtb-control-candidate-build",
     "validation=current-dtb-usb-observation-candidate-build", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(
            f"unsafe candidate derivation: expected {count}, found {actual}: {old}"
        )
    text = text.replace(old, new)
output.write_text(text, encoding="utf-8")
PY
chmod 0700 "$derived_builder"
"$derived_builder" --package "$package" --ramdisk "$ramdisk" \
	--control-dtb "$derived_dtb" --output-parent "$output_parent"

candidate="$output_parent/$OUTPUT_NAME"
[[ -d "$candidate" && ! -L "$candidate" ]] || die 'derived candidate is absent or unsafe'
install -m 0600 "$derived_dtb" "$candidate/$DTB_MEMBER"
install -m 0600 "$dtb_validation" "$candidate/dtb-validation.txt"
(
	cd "$candidate"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$candidate/SHA256SUMS"
(cd "$candidate" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'extended candidate manifest failed'

rm -rf -- "$workdir"
workdir=
trap - EXIT HUP INT TERM
printf 'validation=current-dtb-usb-observation-wrapper\n'
printf 'artifact=%s\ndtb_sha256=%s\ncandidate_sha256=%s\n' \
	"$candidate" "$OUTPUT_DTB_SHA256" "$RAW_SHA256"
printf 'semantic_delta_count=3\ndevice_access=none\nhardware_write=none\n'
