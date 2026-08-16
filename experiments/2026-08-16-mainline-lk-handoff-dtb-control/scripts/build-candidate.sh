#!/usr/bin/env bash

# Assemble the exact GAEL kernel with the runtime-proven Stage-27 DTB.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'Usage: %s --package DIR --ramdisk FILE --control-dtb FILE --output-parent DIR\n' "$0"
}

package=
ramdisk=
control_dtb=
output_parent=
while [[ "$#" -gt 0 ]]; do
	case "$1" in
	--package) package=${2:-}; shift 2 ;;
	--ramdisk) ramdisk=${2:-}; shift 2 ;;
	--control-dtb) control_dtb=${2:-}; shift 2 ;;
	--output-parent) output_parent=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$package" && -n "$ramdisk" && -n "$control_dtb" && -n "$output_parent" ]] || {
	usage >&2
	exit 2
}
for command in awk chmod cmp cp dd find grep jq mkdir mktemp mv python3 rm \
	rmdir sha256sum sort tr truncate wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
ramdisk_parent="$(cd -- "$(dirname -- "$ramdisk")" && pwd -P)"
ramdisk="$ramdisk_parent/$(basename -- "$ramdisk")"
dtb_parent="$(cd -- "$(dirname -- "$control_dtb")" && pwd -P)"
control_dtb="$dtb_parent/$(basename -- "$control_dtb")"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent/" in
"$repo_root/artifacts/"*) ;;
*) die 'output parent must be below the ignored artifacts root' ;;
esac

readonly REPOSITORY_COMMIT=98996fdfbf09f8de2a6b86e488defef22fcc7968
readonly PROFILE=da921x-modules-arm64-entry-ledger
readonly RELEASE=7.1.3-gemini-entryled-a
readonly IMAGE_SHA256=37f3897cee5a7eb899273878938b3c98522a98dd2fac64d2f0f72235d2c10d84
readonly IMAGE_GZIP_SHA256=539f83bf4e6f31e21edacde26399ea285c1e87cdf4df25fb2896d364822a89fe
readonly CONTROL_DTB_SHA256=7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806
readonly CONFIG_SHA256=e622eb1a3acde5c8e351227e7044e34cd894091b2f3b9c210c37e42cced0b323
readonly SYSTEM_MAP_SHA256=dcdfb20bd9102c882366885ffb879885e58b8d88d73e9822a6049c9d5fc7d4ec
readonly BUILD_JSON_SHA256=88ab3409c4026f140cd4a8daa0682799a6e0420b50dd8b30010e14573017fcee
readonly PACKAGE_MANIFEST_SHA256=a9d2f7d81b61eab7dd3afbaba715778ea2785088bf4d7b098043a803c8e86ce5
readonly RAMDISK_SHA256=e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f
readonly SERIALIZER_SHA256=569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95
readonly RAW_SHA256=e96d0cc2670bf4de6e0cc88d35d8814c5c3aa05442d0a5bd83818fa078ca2086
readonly PADDED_SHA256=68515e0ecbb073b4ee18b318bd869fd5b7dea1c3ac838681ceb42b7451dc1c67
readonly RAW_SIZE=6879232
readonly BOOT2_SIZE=16777216
readonly BOOT_NAME=gemini-dtbctl
readonly BOOT_CMDLINE=bootopt=64S3,32N2,64N2
readonly BOOT_FILE=gemini-mt6797-arm64-entry-ledger-stage27-dtb.boot.img

image="$package/Image"
image_gz="$package/Image.gz"
config="$package/kernel.config"
system_map="$package/System.map"
build_json="$package/provenance/build.json"
manifest="$package/SHA256SUMS"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for input in "$image" "$image_gz" "$config" "$system_map" "$build_json" \
	"$manifest" "$ramdisk" "$control_dtb" "$serializer" "$analyzer"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "missing, empty, or unsafe input: $input"
done

check_hash() {
	local path=$1 expected=$2 label=$3
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] ||
		die "$label changed"
}
check_hash "$image" "$IMAGE_SHA256" Image
check_hash "$image_gz" "$IMAGE_GZIP_SHA256" Image.gz
check_hash "$control_dtb" "$CONTROL_DTB_SHA256" 'Stage-27 control DTB'
check_hash "$config" "$CONFIG_SHA256" configuration
check_hash "$system_map" "$SYSTEM_MAP_SHA256" System.map
check_hash "$build_json" "$BUILD_JSON_SHA256" build.json
check_hash "$manifest" "$PACKAGE_MANIFEST_SHA256" 'package manifest'
check_hash "$ramdisk" "$RAMDISK_SHA256" 'serviceability ramdisk'
check_hash "$serializer" "$SERIALIZER_SHA256" serializer
check_hash "$analyzer" "$ANALYZER_SHA256" analyzer
(cd "$package" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'package checksum validation failed'
[[ "$(jq -er '.repository_commit' "$build_json")" == "$REPOSITORY_COMMIT" ]] ||
	die 'repository commit changed'
[[ "$(jq -er '.build_profile' "$build_json")" == "$PROFILE" ]] ||
	die 'build profile changed'
[[ "$(jq -er '.kernel_release' "$build_json")" == "$RELEASE" ]] ||
	die 'kernel release changed'
grep -qx 'CONFIG_MODULES=y' "$config" || die 'module policy changed'
grep -qx '# CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER is not set' "$config" ||
	die 'old ledger leaked into control'
grep -qx 'CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER=y' "$config" ||
	die 'arm64 entry ledger is absent'
grep -qx '# CONFIG_PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT is not set' "$config" ||
	die 'post-ramoops checkpoint leaked into control'
for marker in 'GAEL-20260816-A E0' 'GAEL-20260816-A E1' \
	'GAEL-20260816-A E2' 'GAEL-20260816-A E3'; do
	[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d ' ')" == 1 ]] ||
		die "entry-ledger marker is not unique: $marker"
done

workdir="$(mktemp -d "$output_parent/.lk-handoff-dtb-control.XXXXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

{
	printf 'validation=portable-fetched-kernel-package-with-runtime-proven-dtb-control\n'
	printf 'repository_commit=%s\nprofile=%s\nkernel_release=%s\n' \
		"$REPOSITORY_COMMIT" "$PROFILE" "$RELEASE"
	printf 'package_manifest_sha256=%s\nsha256sums=passed\n' \
		"$PACKAGE_MANIFEST_SHA256"
	printf 'image_sha256=%s\nimage_gzip_sha256=%s\ncontrol_dtb_sha256=%s\n' \
		"$IMAGE_SHA256" "$IMAGE_GZIP_SHA256" "$CONTROL_DTB_SHA256"
	printf 'control_dtb_source=runtime-proven-stage27-lifecycle\n'
	printf 'config_sha256=%s\nsystem_map_sha256=%s\nresult=pass\n' \
		"$CONFIG_SHA256" "$SYSTEM_MAP_SHA256"
} >"$stage/package-validation.txt"
for root in "$stage" "$replica"; do
	python3 "$serializer" --kernel "$image_gz" --ramdisk "$ramdisk" \
		--dtb "$control_dtb" --output "$root/$BOOT_FILE" \
		--name "$BOOT_NAME" --cmdline "$BOOT_CMDLINE" \
		--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
		--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 \
		>"$root/serializer.txt"
done
cmp -s "$stage/$BOOT_FILE" "$replica/$BOOT_FILE" ||
	die 'independent raw assemblies differ'
cp "$stage/$BOOT_FILE" "$stage/boot2-padded.img"
truncate -s "$BOOT2_SIZE" "$stage/boot2-padded.img"
dd if=/dev/zero of="$replica/boot2-padded.img" bs=1048576 count=16 status=none
dd if="$replica/$BOOT_FILE" of="$replica/boot2-padded.img" \
	bs=1048576 conv=notrunc status=none
cmp -s "$stage/boot2-padded.img" "$replica/boot2-padded.img" ||
	die 'independent padding constructions differ'

python3 "$analyzer" --validate-lk --expected-image-gz "$image_gz" \
	--expected-ramdisk "$ramdisk" --expected-dtb "$control_dtb" \
	--expected-name "$BOOT_NAME" --expected-cmdline "$BOOT_CMDLINE" \
	"$stage/$BOOT_FILE" >"$stage/container-analysis.txt"
[[ "$(grep -c '^gate_.*=yes$' "$stage/container-analysis.txt")" == 32 ]] ||
	die 'LK analyzer did not pass all 32 gates'
grep -qx 'lk_validation=passed' "$stage/container-analysis.txt" ||
	die 'LK validation failed'

raw_size="$(wc -c <"$stage/$BOOT_FILE" | tr -d ' ')"
raw_sha256="$(sha256sum "$stage/$BOOT_FILE" | awk '{print $1}')"
padded_sha256="$(sha256sum "$stage/boot2-padded.img" | awk '{print $1}')"
[[ "$raw_size" == "$RAW_SIZE" && "$raw_sha256" == "$RAW_SHA256" ]] ||
	die 'raw candidate identity changed'
[[ "$(wc -c <"$stage/boot2-padded.img" | tr -d ' ')" == "$BOOT2_SIZE" &&
	"$padded_sha256" == "$PADDED_SHA256" ]] || die 'padded candidate identity changed'
grep -v '^output=' "$stage/serializer.txt" >"$stage/serializer.normalized"
mv "$stage/serializer.normalized" "$stage/serializer.txt"

{
	printf 'experiment=2026-08-16-mainline-lk-handoff-dtb-control\n'
	printf 'repository_commit=%s\nprofile=%s\nkernel_release=%s\n' \
		"$REPOSITORY_COMMIT" "$PROFILE" "$RELEASE"
	printf 'image_sha256=%s\nimage_gzip_sha256=%s\ncontrol_dtb_sha256=%s\n' \
		"$IMAGE_SHA256" "$IMAGE_GZIP_SHA256" "$CONTROL_DTB_SHA256"
	printf 'control_dtb_source=runtime-proven-stage27-lifecycle\n'
	printf 'config_sha256=%s\nsystem_map_sha256=%s\n' \
		"$CONFIG_SHA256" "$SYSTEM_MAP_SHA256"
	printf 'ramdisk_sha256=%s\nramdisk_baseline=exact-da921x-serviceability\n' \
		"$RAMDISK_SHA256"
	printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$RAW_SHA256" "$RAW_SIZE"
	printf 'padded_sha256=%s\npadded_size=%s\n' "$PADDED_SHA256" "$BOOT2_SIZE"
	printf 'lk_name=%s\nlk_cmdline=%s\nlk_gates=32-of-32\n' \
		"$BOOT_NAME" "$BOOT_CMDLINE"
	printf 'independent_raw_assemblies=byte-identical\n'
	printf 'independent_padding_constructions=byte-identical\n'
	printf 'runtime_hypothesis=stage27_dtb_distinguishes_lk_dtb_processing_from_image_entry\n'
	printf 'kernel_delta_from_stopped_gael=none\n'
	printf 'dtb_delta_from_stopped_gael=exact-runtime-proven-stage27-dtb\n'
	printf 'register_data_writes_expected=0\ncpu8_cpu9_admission=closed\n'
	printf 'device_access=none\nhardware_write=none\n'
	printf 'boot_candidate=pending-independent-validation\n'
} >"$stage/provenance.txt"
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'candidate manifest failed'
chmod 0600 "$stage"/*

output_name="candidate-lk-handoff-dtb-control-${RAW_SHA256:0:8}"
artifact="$workdir/$output_name"
mv "$stage" "$artifact"
stage=
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv "$artifact" "$output"
rm -rf -- "$replica"
rmdir "$workdir"
workdir=
trap - EXIT HUP INT TERM
printf 'validation=lk-handoff-dtb-control-candidate-build\n'
printf 'artifact=%s\ncandidate_sha256=%s\npadded_sha256=%s\n' \
	"$output" "$RAW_SHA256" "$PADDED_SHA256"
printf 'device_access=none\nhardware_write=none\n'
