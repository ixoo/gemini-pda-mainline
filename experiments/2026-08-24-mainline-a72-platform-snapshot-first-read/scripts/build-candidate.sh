#!/usr/bin/env bash

# Assemble the exact Buildbox candidate with the exact validated observer DTB.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'Usage: %s --package DIR --ramdisk FILE --candidate-dtb FILE --output-parent DIR\n' "$0"
}

package=
ramdisk=
candidate_dtb=
output_parent=
while [[ "$#" -gt 0 ]]; do
	case "$1" in
	--package) package=${2:-}; shift 2 ;;
	--ramdisk) ramdisk=${2:-}; shift 2 ;;
	--candidate-dtb) candidate_dtb=${2:-}; shift 2 ;;
	--output-parent) output_parent=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$package" && -n "$ramdisk" && -n "$candidate_dtb" && -n "$output_parent" ]] || {
	usage >&2
	exit 2
}
for command in awk chmod cmp cp dd find grep jq mkdir mktemp mv python3 rm \
	rmdir sha256sum sort tr truncate wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
package=$(cd -- "$package" && pwd -P)
ramdisk=$(cd -- "$(dirname -- "$ramdisk")" && pwd -P)/$(basename -- "$ramdisk")
candidate_dtb=$(cd -- "$(dirname -- "$candidate_dtb")" && pwd -P)/$(basename -- "$candidate_dtb")
output_parent=$(cd -- "$output_parent" && pwd -P)
case "$output_parent/" in "$repo_root/artifacts/"*) ;; *) die 'output must remain below artifacts' ;; esac

readonly REPOSITORY_COMMIT=2dd7b176a2e54e086a0d7acd689e1aa330a4c358
readonly PROFILE=a72-platform-snapshot-candidate
readonly RELEASE=7.1.3-gemini-a72-platform-read
readonly IMAGE_SHA256=64ec89795d90245f65c62cc1d389715a4feacae51ab7e2096c467f10411977b1
readonly IMAGE_GZIP_SHA256=3ec18e139078b38b0ee354461d8035388535065598ea4b80f7e7a74209681784
readonly CANDIDATE_DTB_SHA256=3c6c54ff07dde1ee3ea234feb39a0ceef72101414f16679e3881a5461570f284
readonly CONFIG_SHA256=972d871f1c3c138b328f2c4438189aea4229331452655c8252b4f26694b0f38f
readonly SYSTEM_MAP_SHA256=5904070bff14da0ff82afb441078497bcbf9d4145d6ce961aa0a9d2281725231
readonly BUILD_JSON_SHA256=9c6100ebd61bf059abe4719095b85a13357b2ca215df3be5531789c9fb3cf54b
readonly PACKAGE_MANIFEST_SHA256=9645c8e7a9f85e0f9550223937b43832b2496bcd1a864f7d3fa7c20ad2cfb526
readonly RAMDISK_SHA256=e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f
readonly SERIALIZER_SHA256=569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95
readonly RAW_SHA256=7d87638c9626469d78e643ac3d7daf7fab5b42f11c54b3ab42df7e834d6ab9f8
readonly PADDED_SHA256=39f801f713a76c616ed8d9282fc0a662fb34c5a766d6839e4c47c757638bae43
readonly RAW_SIZE=6909952
readonly BOOT2_SIZE=16777216
readonly BOOT_NAME=gemini-a72snap
readonly BOOT_CMDLINE=bootopt=64S3,32N2,64N2
readonly BOOT_FILE=gemini-mt6797-a72-platform-snapshot-first-read.boot.img

image="$package/Image"
image_gz="$package/Image.gz"
config="$package/kernel.config"
system_map="$package/System.map"
build_json="$package/provenance/build.json"
manifest="$package/SHA256SUMS"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for input in "$image" "$image_gz" "$config" "$system_map" "$build_json" \
	"$manifest" "$ramdisk" "$candidate_dtb" "$serializer" "$analyzer"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] ||
		die "missing, empty, or unsafe input: $input"
done

check_hash() {
	local path=$1 expected=$2 label=$3
	[[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || die "$label changed"
}
check_hash "$image" "$IMAGE_SHA256" Image
check_hash "$image_gz" "$IMAGE_GZIP_SHA256" Image.gz
check_hash "$candidate_dtb" "$CANDIDATE_DTB_SHA256" 'candidate DTB'
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
[[ "$(jq -er '.repository_dirty' "$build_json")" == false ]] || die 'package was dirty'
[[ "$(jq -er '.build_profile' "$build_json")" == "$PROFILE" ]] || die 'profile changed'
[[ "$(jq -er '.kernel_release' "$build_json")" == "$RELEASE" ]] || die 'release changed'
[[ "$(jq -er '.modules_built' "$build_json")" == false ]] || die 'modules were built'

for token in \
	'CONFIG_LOCALVERSION="-gemini-a72-platform-read"' \
	'CONFIG_MODULES=y' \
	'CONFIG_MTK_MT6797_A72_PLATFORM_STATE=y' \
	'CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y' \
	'CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y' \
	'CONFIG_MTK_MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER=y' \
	'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y' \
	'CONFIG_PSTORE_GEMINI_A72_PLATFORM_SNAPSHOT_LEDGER=y' \
	'# CONFIG_KUNIT is not set'; do
	grep -Fx "$token" "$config" >/dev/null || die "configuration missing: $token"
done
grep -q '^CONFIG_CMDLINE=".*maxcpus=8.*"$' "$config" || die 'exact maxcpus=8 closure absent'
for token in \
	CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER \
	CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER \
	CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR \
	CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER \
	CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION \
	CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW \
	CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE; do
	! grep -qx "$token=y" "$config" || die "later path enabled: $token"
done
for symbol in mt6797_a72_platform_state_snapshot mt6797_platform_snapshot_capture \
	mt6797_a72_platform_snapshot_probe mt6797_dvfsp_clock_backend_probe \
	mt6797_bigidvfs_backend_probe; do
	grep -q " ${symbol}$" "$system_map" || die "required symbol absent: $symbol"
done
for symbol in da9213_legacy_same_value_write mt6797_a72_atomic_publish \
	mt6797_a72_a34_evaluate; do
	! grep -q " ${symbol}$" "$system_map" || die "later symbol linked: $symbol"
done
for marker in \
	'GEMINI_A72_PLATFORM_SNAPSHOT_V1 token=GAPS-20260824-A checkpoint=before-platform slot=1 crc32=a8bf2262' \
	'GEMINI_A72_PLATFORM_SNAPSHOT_V1 token=GAPS-20260824-A checkpoint=after-platform slot=2 crc32=ca566ccf' \
	'GEMINI_A72_PLATFORM_SNAPSHOT_V1 state=complete platform_calls=1 stable_samples=2 register_observations=26 retained_writes=2 retries=0 provider_snapshots=0 protected_clock_reads=0 bigidvfs_reads=0 secure_calls=0 publisher_calls=0 owner_mutations=0 cpu_requests=0'; do
	[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d ' ')" == 1 ]] ||
		die "candidate marker is not unique: $marker"
done

workdir=$(mktemp -d "$output_parent/.a72-platform-snapshot-candidate.XXXXXXXX")
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

{
	printf 'validation=portable-fetched-a72-platform-snapshot-candidate\n'
	printf 'repository_commit=%s\nprofile=%s\nkernel_release=%s\n' \
		"$REPOSITORY_COMMIT" "$PROFILE" "$RELEASE"
	printf 'package_manifest_sha256=%s\nsha256sums=passed\n' "$PACKAGE_MANIFEST_SHA256"
	printf 'image_sha256=%s\nimage_gzip_sha256=%s\ncandidate_dtb_sha256=%s\n' \
		"$IMAGE_SHA256" "$IMAGE_GZIP_SHA256" "$CANDIDATE_DTB_SHA256"
	printf 'config_sha256=%s\nsystem_map_sha256=%s\nresult=pass\n' \
		"$CONFIG_SHA256" "$SYSTEM_MAP_SHA256"
} >"$stage/package-validation.txt"
for root in "$stage" "$replica"; do
	python3 "$serializer" --kernel "$image_gz" --ramdisk "$ramdisk" \
		--dtb "$candidate_dtb" --output "$root/$BOOT_FILE" \
		--name "$BOOT_NAME" --cmdline "$BOOT_CMDLINE" \
		--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
		--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 \
		>"$root/serializer.txt"
done
cmp -s "$stage/$BOOT_FILE" "$replica/$BOOT_FILE" || die 'raw assemblies differ'
cp "$stage/$BOOT_FILE" "$stage/boot2-padded.img"
truncate -s "$BOOT2_SIZE" "$stage/boot2-padded.img"
dd if=/dev/zero of="$replica/boot2-padded.img" bs=1048576 count=16 status=none
dd if="$replica/$BOOT_FILE" of="$replica/boot2-padded.img" \
	bs=1048576 conv=notrunc status=none
cmp -s "$stage/boot2-padded.img" "$replica/boot2-padded.img" ||
	die 'padding constructions differ'

python3 "$analyzer" --validate-lk --expected-image-gz "$image_gz" \
	--expected-ramdisk "$ramdisk" --expected-dtb "$candidate_dtb" \
	--expected-name "$BOOT_NAME" --expected-cmdline "$BOOT_CMDLINE" \
	"$stage/$BOOT_FILE" >"$stage/container-analysis.txt"
[[ "$(grep -c '^gate_.*=yes$' "$stage/container-analysis.txt")" == 32 ]] ||
	die 'LK analyzer did not pass all 32 gates'
grep -qx 'lk_validation=passed' "$stage/container-analysis.txt" || die 'LK validation failed'

raw_size=$(wc -c <"$stage/$BOOT_FILE" | tr -d ' ')
raw_sha256=$(sha256sum "$stage/$BOOT_FILE" | awk '{print $1}')
padded_sha256=$(sha256sum "$stage/boot2-padded.img" | awk '{print $1}')
[[ "$raw_size" == "$RAW_SIZE" && "$raw_sha256" == "$RAW_SHA256" ]] ||
	die 'raw candidate identity changed'
[[ "$(wc -c <"$stage/boot2-padded.img" | tr -d ' ')" == "$BOOT2_SIZE" &&
	"$padded_sha256" == "$PADDED_SHA256" ]] || die 'padded identity changed'
grep -v '^output=' "$stage/serializer.txt" >"$stage/serializer.normalized"
mv "$stage/serializer.normalized" "$stage/serializer.txt"

{
	printf 'experiment=2026-08-24-mainline-a72-platform-snapshot-first-read\n'
	printf 'repository_commit=%s\nprofile=%s\nkernel_release=%s\n' \
		"$REPOSITORY_COMMIT" "$PROFILE" "$RELEASE"
	printf 'image_sha256=%s\nimage_gzip_sha256=%s\ncandidate_dtb_sha256=%s\n' \
		"$IMAGE_SHA256" "$IMAGE_GZIP_SHA256" "$CANDIDATE_DTB_SHA256"
	printf 'config_sha256=%s\nsystem_map_sha256=%s\n' "$CONFIG_SHA256" "$SYSTEM_MAP_SHA256"
	printf 'ramdisk_sha256=%s\nramdisk_baseline=exact-da921x-serviceability\n' "$RAMDISK_SHA256"
	printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$RAW_SHA256" "$RAW_SIZE"
	printf 'padded_sha256=%s\npadded_size=%s\n' "$PADDED_SHA256" "$BOOT2_SIZE"
	printf 'lk_name=%s\nlk_cmdline=%s\nlk_gates=32-of-32\n' "$BOOT_NAME" "$BOOT_CMDLINE"
	printf 'independent_raw_assemblies=byte-identical\n'
	printf 'independent_padding_constructions=byte-identical\n'
	printf 'runtime_hypothesis=one-stable-platform-snapshot-on-passed-three-backend-baseline\n'
	printf 'dtb_delta_from_passed_bigidvfs=observer-node-plus-source-phandle\n'
	printf 'platform_snapshot_calls=1\nregister_observations=26\nretries=0\n'
	printf 'provider_snapshots=0\nprotected_clock_reads=0\nbigidvfs_reads=0\nsecure_calls=0\n'
	printf 'publisher_calls=0\nowner_mutations=0\ncpu_requests=0\nmaxcpus=8\n'
	printf 'device_access=none\nhardware_write=none\nboot_candidate=pending-independent-validation\n'
} >"$stage/provenance.txt"
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) ||
	die 'candidate manifest failed'
chmod 0600 "$stage"/*

output="$output_parent/candidate-a72-platform-snapshot-${RAW_SHA256:0:8}"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv "$stage" "$output"
rm -rf -- "$replica"
rmdir "$workdir"
workdir=
trap - EXIT HUP INT TERM
printf 'validation=a72-platform-snapshot-candidate-build\n'
printf 'artifact=%s\ncandidate_sha256=%s\npadded_sha256=%s\n' \
	"$output" "$RAW_SHA256" "$PADDED_SHA256"
printf 'device_access=none\nhardware_write=none\n'
