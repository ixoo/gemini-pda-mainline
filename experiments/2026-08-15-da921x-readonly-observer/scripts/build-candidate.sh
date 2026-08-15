#!/usr/bin/env bash

# Assemble the exact read-only observer Android-v0/LK candidate offline.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'Usage: %s --package DIR --ramdisk FILE --output-parent DIR\n' "$0"
}

package=
ramdisk=
output_parent=
while [[ "$#" -gt 0 ]]; do
	case "$1" in
	--package) package=${2:-}; shift 2 ;;
	--ramdisk) ramdisk=${2:-}; shift 2 ;;
	--output-parent) output_parent=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$package" && -n "$ramdisk" && -n "$output_parent" ]] || {
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
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent/" in
"$repo_root/artifacts/"*) ;;
*) die 'output parent must be below the ignored artifacts root' ;;
esac

readonly REPOSITORY_COMMIT=d0d511e60af343bdcc880b41b50acd2be877fa2b
readonly PROFILE=da921x-readonly-observer
readonly RELEASE=7.1.3-gemini-da921x-observer
readonly IMAGE_SHA256=3483fb980c8c59ea0a10bf356737391aaa6b49969e39b4a3cee3831774f5fbf9
readonly IMAGE_GZIP_SHA256=5609a9a30b2959fd93144900461e4a07ba274adda04454ef534a2961d6a8c1b1
readonly DTB_SHA256=61ea34a4f780afe04da1257f8c3655be7f8490a7c3af2df727dd8592bb6e6285
readonly CONFIG_SHA256=0d707f8483ce7a5599625bb2a09889c642b3ee945d2ad3fa6cf6f7289363581a
readonly SYSTEM_MAP_SHA256=665d70c58f771abc43d39b2b9b7244a28df9ae7ad4eb8856e4fbf678dd7e88dc
readonly BUILD_JSON_SHA256=1643441936f8f88d8a7dc221007c4d5fc0616a9c697cda8fcb0b4eb380e61b4e
readonly PACKAGE_MANIFEST_SHA256=dcebb9929993b8e8affb86f37470d4b33ace97f7ef17eaee0247b3ad5e9439bf
readonly RAMDISK_SHA256=e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f
readonly SERIALIZER_SHA256=569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95
readonly RAW_SHA256=1a55a25b7d6bff448802db3259ba65371c34657b341f0e621dc134bd700e7b14
readonly PADDED_SHA256=7a3ce120de99d7c5ad26dce618f81d50bfeb1ca95b5f2a0bdb9fbf4acba1f564
readonly RAW_SIZE=7761920
readonly BOOT2_SIZE=16777216
readonly BOOT_NAME=gemini-daobs
readonly BOOT_CMDLINE=bootopt=64S3,32N2,64N2
readonly BOOT_FILE=gemini-mt6797-da921x-readonly-observer.boot.img

image="$package/Image"
image_gz="$package/Image.gz"
dtb="$package/dtbs/mediatek/mt6797-gemini-pda.dtb"
config="$package/kernel.config"
system_map="$package/System.map"
build_json="$package/provenance/build.json"
manifest="$package/SHA256SUMS"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for input in "$image" "$image_gz" "$dtb" "$config" "$system_map" \
	"$build_json" "$manifest" "$ramdisk" "$serializer" "$analyzer"; do
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
check_hash "$dtb" "$DTB_SHA256" 'Gemini DTB'
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
grep -qx 'CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER=y' "$config" ||
	die 'observer is not built in'
grep -qx '# CONFIG_KUNIT is not set' "$config" || die 'KUnit leaked into runtime image'
grep -q ' da9213_legacy_observer_collect$' "$system_map" || die 'observer symbol missing'
! grep -q 'da9213_legacy_observer_test_suite' "$system_map" ||
	die 'observer test symbol leaked into runtime image'

workdir="$(mktemp -d "$output_parent/.da921x-observer-candidate.XXXXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

{
	printf 'validation=portable-fetched-kernel-package\n'
	printf 'repository_commit=%s\nprofile=%s\nkernel_release=%s\n' \
		"$REPOSITORY_COMMIT" "$PROFILE" "$RELEASE"
	printf 'package_manifest_sha256=%s\nsha256sums=passed\n' \
		"$PACKAGE_MANIFEST_SHA256"
	printf 'image_sha256=%s\nimage_gzip_sha256=%s\ndtb_sha256=%s\n' \
		"$IMAGE_SHA256" "$IMAGE_GZIP_SHA256" "$DTB_SHA256"
	printf 'config_sha256=%s\nsystem_map_sha256=%s\nresult=pass\n' \
		"$CONFIG_SHA256" "$SYSTEM_MAP_SHA256"
} >"$stage/package-validation.txt"
for root in "$stage" "$replica"; do
	python3 "$serializer" --kernel "$image_gz" --ramdisk "$ramdisk" --dtb "$dtb" \
		--output "$root/$BOOT_FILE" --name "$BOOT_NAME" --cmdline "$BOOT_CMDLINE" \
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
	--expected-ramdisk "$ramdisk" --expected-dtb "$dtb" \
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
	printf 'experiment=2026-08-15-da921x-readonly-observer\n'
	printf 'repository_commit=%s\nprofile=%s\nkernel_release=%s\n' \
		"$REPOSITORY_COMMIT" "$PROFILE" "$RELEASE"
	printf 'image_sha256=%s\nimage_gzip_sha256=%s\ndtb_sha256=%s\n' \
		"$IMAGE_SHA256" "$IMAGE_GZIP_SHA256" "$DTB_SHA256"
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
	printf 'runtime_hypothesis=one-attributable-read-only-provider-observation\n'
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

output_name="candidate-da921x-readonly-observer-${RAW_SHA256:0:8}"
artifact="$workdir/$output_name"
mv "$stage" "$artifact"
stage=
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv "$artifact" "$output"
rm -rf -- "$replica"
rmdir "$workdir"
workdir=
trap - EXIT
printf 'validation=da921x-readonly-observer-candidate-build\n'
printf 'artifact=%s\ncandidate_sha256=%s\npadded_sha256=%s\n' \
	"$output" "$RAW_SHA256" "$PADDED_SHA256"
printf 'device_access=none\nhardware_write=none\n'
