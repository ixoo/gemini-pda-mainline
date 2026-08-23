#!/usr/bin/env bash

# Assemble the exact read-free clock-entry kernel with the serviceability DT
# whose only additional change enables the clock-backend platform node.
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

readonly REPOSITORY_COMMIT=2c89888e72ebd62ae3832ccbb4916cb9d9648358
readonly PROFILE=da921x-clock-entry-first-dmesg
readonly RELEASE=7.1.3-gemini-clock-entry-first-dmesg
readonly IMAGE_SHA256=984acb29964a7e111da333d457d1bea48c6952cad2fd95c61b9bedf89d1d0c0e
readonly IMAGE_GZIP_SHA256=fd5e77c8194834b5da39f397bea2d4873ad8372e2802c8b6ec640518407b430e
readonly CONTROL_DTB_SHA256=7c1d5f69924a8280e36ff111b411c4fbecd32243e8d0da9e9f6f4b333a21e100
readonly CONFIG_SHA256=0a19f77a527e15997430311358e5ae499271eb03573cf6785b2dffdaf52427a7
readonly SYSTEM_MAP_SHA256=df7f396405c06aca97b8ebe866bb86cd17459636a83affd8f35220d28c0af099
readonly BUILD_JSON_SHA256=aa0277eef4ca7e21728466d810ea8cd68d326ed1481e98deeb7464dd250a1e99
readonly PACKAGE_MANIFEST_SHA256=f30872001d864d8466ac42311ce531defe1a88329f3f5afdd8281ca803e843c0
readonly RAMDISK_SHA256=e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f
readonly SERIALIZER_SHA256=569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95
readonly RAW_SHA256=251e792573bd9961d3f2b90563cff85d851c6502008d97e1ae502fbacda49b83
readonly PADDED_SHA256=40b7c663b835bcf4c48f4149f14aa416343e3e322ab78a0aa38448afff9455b4
readonly RAW_SIZE=6899712
readonly BOOT2_SIZE=16777216
readonly BOOT_NAME=gemini-clkfdm
readonly BOOT_CMDLINE=bootopt=64S3,32N2,64N2
readonly BOOT_FILE=gemini-mt6797-clock-entry-first-dmesg.boot.img

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
check_hash "$control_dtb" "$CONTROL_DTB_SHA256" 'clock-entry serviceability DTB'
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
[[ "$(jq -er '.repository_dirty' "$build_json")" == false ]] ||
	die 'Buildbox checkout was dirty'

for gate in \
	'CONFIG_MODULES=y' \
	'CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y' \
	'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y' \
	'CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER=y' \
	'CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION=y' \
	'# CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND is not set' \
	'# CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE is not set' \
	'# CONFIG_MTK_MT6797_A72_POWER is not set' \
	'# CONFIG_MTK_MT6797_A72_PLATFORM_STATE is not set' \
	'# CONFIG_KUNIT is not set' \
	'CONFIG_LOCALVERSION="-gemini-clock-entry-first-dmesg"'; do
	grep -Fqx "$gate" "$config" || die "configuration gate changed: $gate"
done
for symbol in PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_RAW_WRITE_QUALIFICATION \
	PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION \
	PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER \
	MTK_MT6797_PROTECTED_READBACK_OBSERVER; do
	! grep -q "^CONFIG_${symbol}=y$" "$config" ||
		die "forbidden retained-write mode enabled: $symbol"
done
grep -Eq '^CONFIG_CMDLINE=".*maxcpus=8( |")' "$config" ||
	die 'maxcpus=8 closure is absent'
for marker in \
	'GEMINI_CLOCK_BACKEND_FIRST_DMESG_V1 token=GCBF-20260823-A checkpoint=driver-init slot=1 crc32=6197fd57' \
	'GEMINI_CLOCK_BACKEND_FIRST_DMESG_V1 token=GCBF-20260823-A checkpoint=probe-enter slot=2 crc32=61636940'; do
	[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d ' ')" == 1 ]] ||
		die "record marker is not unique: $marker"
done
[[ "$(grep -aFo 'GEMINI_CLOCK_BACKEND_FIRST_DMESG_LIVE_V1' "$image" |
	wc -l | tr -d ' ')" == 3 ]] || die 'live marker count changed'
for forbidden in 'GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1 token=GCBE-20260821-A' \
	'GEMINI_FIRST_DMESG_RAW_WRITE_QUALIFICATION_LIVE_V1' \
	'run-same-value-write-20260819-a' 'GAEL-20260816-A'; do
	! grep -aFq "$forbidden" "$image" || die "forbidden Image token returned: $forbidden"
done

workdir="$(mktemp -d "$output_parent/.clock-entry-first-dmesg.XXXXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

{
	printf 'validation=portable-fetched-clock-entry-first-dmesg-package\n'
	printf 'repository_commit=%s\nprofile=%s\nkernel_release=%s\n' \
		"$REPOSITORY_COMMIT" "$PROFILE" "$RELEASE"
	printf 'package_manifest_sha256=%s\nsha256sums=passed\n' "$PACKAGE_MANIFEST_SHA256"
	printf 'image_sha256=%s\nimage_gzip_sha256=%s\ncontrol_dtb_sha256=%s\n' \
		"$IMAGE_SHA256" "$IMAGE_GZIP_SHA256" "$CONTROL_DTB_SHA256"
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
grep -qx 'lk_validation=passed' "$stage/container-analysis.txt" || die 'LK validation failed'

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
	printf 'experiment=2026-08-23-mainline-clock-backend-first-dmesg-entry\n'
	printf 'repository_commit=%s\nprofile=%s\nkernel_release=%s\n' \
		"$REPOSITORY_COMMIT" "$PROFILE" "$RELEASE"
	printf 'image_sha256=%s\nimage_gzip_sha256=%s\ncontrol_dtb_sha256=%s\n' \
		"$IMAGE_SHA256" "$IMAGE_GZIP_SHA256" "$CONTROL_DTB_SHA256"
	printf 'control_dtb_source=runtime-proven-serviceability-plus-clock-status-okay\n'
	printf 'config_sha256=%s\nsystem_map_sha256=%s\n' "$CONFIG_SHA256" "$SYSTEM_MAP_SHA256"
	printf 'ramdisk_sha256=%s\nramdisk_baseline=exact-da921x-serviceability\n' "$RAMDISK_SHA256"
	printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$RAW_SHA256" "$RAW_SIZE"
	printf 'padded_sha256=%s\npadded_size=%s\n' "$PADDED_SHA256" "$BOOT2_SIZE"
	printf 'lk_name=%s\nlk_cmdline=%s\nlk_gates=32-of-32\n' "$BOOT_NAME" "$BOOT_CMDLINE"
	printf 'independent_raw_assemblies=byte-identical\n'
	printf 'independent_padding_constructions=byte-identical\n'
	printf 'runtime_hypothesis=clock-driver-registration-and-read-free-probe-entry\n'
	printf 'retained_record_commits_expected=maximum-2\n'
	printf 'protected_clock_reads_expected=0\nbigidvfs_reads_expected=0\n'
	printf 'mapped_mmio_transactions_expected=0\nclock_enables_expected=0\n'
	printf 'DA921x_register_data_writes_expected=0\ncpu8_cpu9_admission=closed\n'
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

output_name="candidate-clock-entry-first-dmesg-${RAW_SHA256:0:8}"
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
printf 'validation=clock-backend-first-dmesg-candidate-build\n'
printf 'artifact=%s\ncandidate_sha256=%s\npadded_sha256=%s\n' \
	"$output" "$RAW_SHA256" "$PADDED_SHA256"
printf 'device_access=none\nhardware_write=none\n'
