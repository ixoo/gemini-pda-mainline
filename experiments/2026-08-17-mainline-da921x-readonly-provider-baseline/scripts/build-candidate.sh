#!/usr/bin/env bash

# Assemble the source-pinned read-only DA921x provider candidate.
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
while (($#)); do
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
for command in awk chmod find grep install jq mkdir mktemp python3 rm sha256sum sort xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent/" in
"$repo_root/artifacts/"*) ;;
*) die 'output parent must be below the ignored artifacts root' ;;
esac

readonly SOURCE_BUILDER="$repo_root/experiments/2026-08-16-mainline-lk-handoff-dtb-control/scripts/build-candidate.sh"
readonly SOURCE_BUILDER_SHA256=cb653690a9ab76d52fc40ea808d2df1bce107b19987616857f81b4f20abf3771
readonly DTB_BUILDER="$script_dir/build-provider-dtb.sh"
readonly DTB_BUILDER_SHA256=b40340ee88a0346959da9a145530971fdfaad781611a6603154a98f8536c5cd5
readonly REPOSITORY_COMMIT=7199e8229c6a805a941e33a6862956949dfebd3a
readonly PROFILE=da921x-lk-clock-readonly-provider
readonly RELEASE=7.1.3-gemini-da921x-lkro
readonly BASE_DTB_SHA256=380205e0546c1b87f4ce6b4c34fcd734a22dc42e3b1c3145044d396a16e00709
readonly PROVIDER_DTB_SHA256=d7dba05efa272c8264c8ea15c776fb88c21a0012603214b49dfd9e2893e87d48
readonly RAW_SHA256=ab86ce3950a335cc863f4d0a5921b17348cb1c184fcc69f3efa326f8ed22a321
readonly PADDED_SHA256=eeee7adea53134c8146e10591708725649a8331bdef7ad418a847b5d04c8e854
readonly OUTPUT_NAME="candidate-mainline-da921x-lkro-provider-${RAW_SHA256:0:8}"
readonly DTB_MEMBER=mt6797-gemini-pda-da921x-lkro-provider.dtb

for input in "$SOURCE_BUILDER" "$DTB_BUILDER"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "source input is missing, empty, or unsafe: $input"
done
[[ "$(sha256sum "$SOURCE_BUILDER" | awk '{print $1}')" == \
	"$SOURCE_BUILDER_SHA256" ]] || die 'source candidate builder changed'
[[ "$(sha256sum "$DTB_BUILDER" | awk '{print $1}')" == "$DTB_BUILDER_SHA256" ]] ||
	die 'provider DTB builder changed'
[[ "$(sha256sum "$base_dtb" | awk '{print $1}')" == "$BASE_DTB_SHA256" ]] ||
	die 'package DTB changed'

config="$package/kernel.config"
build_json="$package/provenance/build.json"
[[ -f "$config" && ! -L "$config" && -f "$build_json" && ! -L "$build_json" ]] ||
	die 'package configuration or provenance is unsafe'
[[ "$(jq -er '.repository_commit' "$build_json")" == "$REPOSITORY_COMMIT" ]] ||
	die 'package repository commit changed'
[[ "$(jq -er '.build_profile' "$build_json")" == "$PROFILE" ]] || die 'package profile changed'
[[ "$(jq -er '.kernel_release' "$build_json")" == "$RELEASE" ]] || die 'kernel release changed'
for gate in \
	'CONFIG_MODULES=y' \
	'CONFIG_NVMEM=y' \
	'CONFIG_NVMEM_MTK_ATAG_DEVINFO=y' \
	'CONFIG_REGULATOR_DA9213_LEGACY=y' \
	'CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER=y' \
	'CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER=y' \
	'# CONFIG_KUNIT is not set' \
	'# CONFIG_MTK_MT6797_A72_POWER is not set' \
	'# CONFIG_MTK_MT6797_DVFSP_RESOURCE_OWNER is not set' \
	'# CONFIG_ARM64_MT6797_A72_CAPABILITY_PROFILE is not set' \
	'CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER=y'; do
	grep -Fqx "$gate" "$config" || die "configuration gate missing: $gate"
done
grep -Eq '^CONFIG_CMDLINE=".*maxcpus=8( |")' "$config" || die 'maxcpus=8 closure is absent'

workdir="$(mktemp -d "$output_parent/.da921x-lkro-provider-wrapper.XXXXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
provider_dtb="$workdir/$DTB_MEMBER"
dtb_validation="$workdir/dtb-validation.txt"
"$DTB_BUILDER" --base-dtb "$base_dtb" --output "$provider_dtb" >"$dtb_validation"
[[ "$(sha256sum "$provider_dtb" | awk '{print $1}')" == "$PROVIDER_DTB_SHA256" ]] ||
	die 'provider DTB changed'

derived_builder="$workdir/build-candidate-derived.sh"
python3 - "$SOURCE_BUILDER" "$derived_builder" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
output = Path(sys.argv[2])
text = source.read_text(encoding="utf-8")
replacements = (
    ("# Assemble the exact GAEL kernel with the runtime-proven Stage-27 DTB.",
     "# Assemble the exact read-only DA921x provider candidate.", 1),
    ("98996fdfbf09f8de2a6b86e488defef22fcc7968",
     "7199e8229c6a805a941e33a6862956949dfebd3a", 1),
    ("da921x-modules-arm64-entry-ledger", "da921x-lk-clock-readonly-provider", 1),
    ("7.1.3-gemini-entryled-a", "7.1.3-gemini-da921x-lkro", 1),
    ("37f3897cee5a7eb899273878938b3c98522a98dd2fac64d2f0f72235d2c10d84",
     "c5d73e077165f0f22b0d8ff109661edc29763c12f4ed6fbd64b2d0fef910e1cc", 1),
    ("539f83bf4e6f31e21edacde26399ea285c1e87cdf4df25fb2896d364822a89fe",
     "086d109464533194abed2c19fa56e647033edd957dafb2ee2512acd3100ed9f1", 1),
    ("7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806",
     "d7dba05efa272c8264c8ea15c776fb88c21a0012603214b49dfd9e2893e87d48", 1),
    ("e622eb1a3acde5c8e351227e7044e34cd894091b2f3b9c210c37e42cced0b323",
     "4ea4743024f6e8f10beeaf7db837af153d1bada99c704835143d9d5e691e9326", 1),
    ("dcdfb20bd9102c882366885ffb879885e58b8d88d73e9822a6049c9d5fc7d4ec",
     "12b760eee8c704cfd968a084d4a81a293ebeb95edbfa6504c56a2c8e14c684c1", 1),
    ("88ab3409c4026f140cd4a8daa0682799a6e0420b50dd8b30010e14573017fcee",
     "5732eff6428a1dbc983ed2dc096209693fef752919e13d196d8bb97701a1a82d", 1),
    ("a9d2f7d81b61eab7dd3afbaba715778ea2785088bf4d7b098043a803c8e86ce5",
     "c0cb589e35ca1b49860317bd343fa0fbf195e456469b4eff3b193ecaa0fe3566", 1),
    ("e96d0cc2670bf4de6e0cc88d35d8814c5c3aa05442d0a5bd83818fa078ca2086",
     "ab86ce3950a335cc863f4d0a5921b17348cb1c184fcc69f3efa326f8ed22a321", 1),
    ("68515e0ecbb073b4ee18b318bd869fd5b7dea1c3ac838681ceb42b7451dc1c67",
     "eeee7adea53134c8146e10591708725649a8331bdef7ad418a847b5d04c8e854", 1),
    ("readonly RAW_SIZE=6879232", "readonly RAW_SIZE=6891520", 1),
    ("readonly BOOT_NAME=gemini-dtbctl", "readonly BOOT_NAME=gemini-lkro", 1),
    ("readonly BOOT_FILE=gemini-mt6797-arm64-entry-ledger-stage27-dtb.boot.img",
     "readonly BOOT_FILE=gemini-mt6797-da921x-lkro-provider.boot.img", 1),
    ("Stage-27 control DTB", "read-only provider DTB", 1),
    (".lk-handoff-dtb-control.XXXXXXXX", ".da921x-lkro-provider.XXXXXXXX", 1),
    ("portable-fetched-kernel-package-with-runtime-proven-dtb-control",
     "portable-fetched-kernel-package-with-read-only-DA921x-provider", 1),
    ("control_dtb_source=runtime-proven-stage27-lifecycle",
     "control_dtb_source=package-LK-clocks-plus-exact-serviceability-group", 2),
    ("experiment=2026-08-16-mainline-lk-handoff-dtb-control",
     "experiment=2026-08-17-mainline-da921x-readonly-provider-baseline", 1),
    ("runtime_hypothesis=stage27_dtb_distinguishes_lk_dtb_processing_from_image_entry",
     "runtime_hypothesis=LK-devinfo-releases-handoff-and-DA921x-binds-read-only", 1),
    ("kernel_delta_from_stopped_gael=none",
     "kernel_delta_from-proven-entry-ledger=LK-devinfo-NVMEM-plus-DA921x-observer", 1),
    ("dtb_delta_from_stopped_gael=exact-runtime-proven-stage27-dtb",
     "dtb_delta_from-package=exact-proven-serviceability-group-only", 1),
    ("candidate-lk-handoff-dtb-control-${RAW_SHA256:0:8}",
     "candidate-mainline-da921x-lkro-provider-${RAW_SHA256:0:8}", 1),
    ("validation=lk-handoff-dtb-control-candidate-build",
     "validation=mainline-da921x-readonly-provider-candidate-build", 1),
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
	--control-dtb "$provider_dtb" --output-parent "$output_parent"

candidate="$output_parent/$OUTPUT_NAME"
[[ -d "$candidate" && ! -L "$candidate" ]] || die 'derived candidate is absent or unsafe'
install -m 0600 "$provider_dtb" "$candidate/$DTB_MEMBER"
install -m 0600 "$dtb_validation" "$candidate/dtb-validation.txt"
python3 - "$candidate/provenance.txt" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="ascii")
replacements = (
    ("register_data_writes_expected=0\ncpu8_cpu9_admission=closed",
     "register_data_writes_expected=AW9523-serviceability-probe-and-keyboard-only\n"
     "DA921x_register_data_writes_expected=0\n"
     "DA921x_provider_operations=get_voltage_sel,list_voltage,is_enabled\n"
     "cpu8_cpu9_admission=closed", 1),
    ("hardware_write=none\nboot_candidate=pending-independent-validation",
     "hardware_write=AW9523-serviceability-probe-and-keyboard-only\n"
     "boot_candidate=pending-independent-validation", 1),
)
for old, new, count in replacements:
    actual = text.count(old)
    if actual != count:
        raise SystemExit(f"unsafe provenance correction: expected {count}, found {actual}: {old}")
    text = text.replace(old, new)
path.write_text(text, encoding="ascii")
PY
(
	cd "$candidate"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$candidate/SHA256SUMS"
(cd "$candidate" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'extended candidate manifest failed'

rm -rf -- "$workdir"
workdir=
trap - EXIT HUP INT TERM
printf 'validation=mainline-da921x-readonly-provider-wrapper\n'
printf 'artifact=%s\ndtb_sha256=%s\ncandidate_sha256=%s\npadded_sha256=%s\n' \
	"$candidate" "$PROVIDER_DTB_SHA256" "$RAW_SHA256" "$PADDED_SHA256"
printf 'DA921x_register_data_writes_expected=0\nCPU8_CPU9_admission=closed\n'
printf 'runtime_hardware_write=AW9523-serviceability-probe-and-keyboard-only\n'
printf 'device_access=none\nhardware_write=none\nresult=pass\n'
