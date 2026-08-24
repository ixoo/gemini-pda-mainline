#!/usr/bin/env bash

# Assemble the exact guarded A72 physical-source candidate from the fetched
# Buildbox package and the runtime-proven serviceability ramdisk.
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
for command in awk chmod cmp cp dd fdtget find grep jq mkdir mktemp mv \
	python3 rm rmdir sha256sum sort tr truncate wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
package=$(cd -- "$package" && pwd -P)
ramdisk_parent=$(cd -- "$(dirname -- "$ramdisk")" && pwd -P)
ramdisk="$ramdisk_parent/$(basename -- "$ramdisk")"
output_parent=$(cd -- "$output_parent" && pwd -P)
case "$output_parent/" in
"$repo_root/artifacts/"*) ;;
*) die 'output parent must be below the ignored artifacts root' ;;
esac

readonly REPOSITORY_COMMIT=f3bf03f4c2515e9c1ac5049c6544c618aaeb8af1
readonly PROFILE=a72-physical-source-candidate
readonly RELEASE=7.1.3-gemini-a72-physical-source
readonly IMAGE_SHA256=1cde8722a28029de498436315eee61027596db19cdee4a2a7224ece079bd7079
readonly IMAGE_GZIP_SHA256=9ecefb990bd0cf136d32f443ebb59597de48a814df84e2dccf3669c600aac3b9
readonly DTB_SHA256=fe67420ca4e2955a73a4a3f2e442af3534b621820cf77ae035be9bf98756425d
readonly CONFIG_SHA256=39a5a007937d10f50e79da865feda843a06c0ed98301333b9f5c24bbd1808f99
readonly SYSTEM_MAP_SHA256=f139629d79deb15726381c898c79ca4e57973da8188e6d4addab9a0ffd9008ef
readonly BUILD_JSON_SHA256=92120e48a478bdbd3aac78f69c3ea00dbc82b86111bebcf022f3d6493c3f180f
readonly PACKAGE_MANIFEST_SHA256=9bcc4a90075f659e4ab423bd6bbcf0eefb1a9f2fe4a9929f44701021d642e52c
readonly RAMDISK_SHA256=e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f
readonly SERIALIZER_SHA256=569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95
readonly RAW_SHA256=1d0c1420ca2a1ea7c88d22ffeda44c2fa14d238ebceeb73ce7d56133bac4f005
readonly PADDED_SHA256=aa02ab666e63e7011139c1057bda99cdbab89245d41f9cad59dae30743b41246
readonly RAW_SIZE=6912000
readonly BOOT2_SIZE=16777216
readonly BOOT_NAME=gemini-a72src
readonly BOOT_CMDLINE=bootopt=64S3,32N2,64N2
readonly BOOT_FILE=gemini-mt6797-a72-physical-source.boot.img

image="$package/Image"
image_gz="$package/Image.gz"
config="$package/kernel.config"
system_map="$package/System.map"
dtb="$package/dtbs/mediatek/mt6797-gemini-pda-a72-physical-source.dtb"
build_json="$package/provenance/build.json"
manifest="$package/SHA256SUMS"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for input in "$image" "$image_gz" "$config" "$system_map" "$dtb" \
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
check_hash "$dtb" "$DTB_SHA256" 'physical-source DTB'
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
	'CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR=y' \
	'CONFIG_MTK_MT6797_A72_PLATFORM_STATE=y' \
	'CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y' \
	'CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y' \
	'CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y' \
	'CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y' \
	'CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER=y' \
	'# CONFIG_KUNIT is not set' \
	'CONFIG_LOCALVERSION="-gemini-a72-physical-source"'; do
	grep -Fqx "$gate" "$config" || die "configuration gate changed: $gate"
done
for symbol in \
	PSTORE_GEMINI_PRE_RAMOOPS_LEDGER \
	PSTORE_GEMINI_ARM64_ENTRY_LEDGER \
	PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER \
	PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL \
	PSTORE_GEMINI_PROTECTED_READBACK_RAW_ENTRY_LEDGER \
	PSTORE_GEMINI_PROTECTED_READBACK_FIRST_DMESG_WRITE_QUALIFICATION \
	PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER \
	PSTORE_GEMINI_CLOCK_BACKEND_FIRST_DMESG_ENTRY_QUALIFICATION \
	PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION \
	MTK_MT6797_PROTECTED_READBACK_OBSERVER \
	ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR \
	ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER \
	REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION \
	MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW \
	REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE; do
	! grep -Fqx "CONFIG_${symbol}=y" "$config" ||
		die "forbidden action or ledger enabled: $symbol"
done
grep -Eq '^CONFIG_CMDLINE=".*maxcpus=8( |")' "$config" ||
	die 'maxcpus=8 closure is absent'

for symbol in \
	mt6797_a72_physical_source_capture \
	mt6797_a72_physical_source_run \
	mt6797_a72_direct_source_register \
	mt6797_a72_direct_state_snapshot \
	mt6797_a72_direct_source_unregister \
	mt6797_a72_provider_snapshot \
	mt6797_a72_platform_state_snapshot \
	mt6797_dvfsp_clock_backend_read \
	mt6797_bigidvfs_backend_read \
	gemini_protected_readback_ledger_checkpoint; do
	grep -q " ${symbol}$" "$system_map" || die "required symbol absent: $symbol"
done
for symbol in \
	mt6797_a72_a34_evaluate \
	mt6797_a72_atomic_publish \
	da9213_legacy_provider_transaction_acquire \
	da9213_legacy_provider_transaction_release \
	da9213_legacy_same_value_write; do
	! grep -q " ${symbol}$" "$system_map" || die "forbidden symbol linked: $symbol"
done

for marker in \
	'GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A checkpoint=before-bigidvfs slot=1 crc32=47eaad49' \
	'GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A checkpoint=after-bigidvfs slot=2 crc32=d03ca6dc' \
	'GEMINI_A72_PHYSICAL_SOURCE_V1 state=complete registrations=1 callbacks=1 unregisters=1 platform_calls=1 provider_snapshots=1 clock_calls=1 retained_writes=2 bigidvfs_calls=1 bigidvfs_smc_reads=8 compositor_retries=0 provider_acquires=0 provider_releases=0 publisher_calls=0 owner_mutations=0 cpu_requests=0'; do
	[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d ' ')" == 1 ]] ||
		die "record or runtime marker is not unique: $marker"
done
for forbidden in \
	'GEMINI_PROTECTED_CLOCK_FIRST_DMESG_V1 token=GPCF-20260823-A' \
	'GEMINI_CLOCK_BACKEND_FIRST_DMESG_V1 token=GCBF-20260823-A' \
	'GEMINI_FIRST_DMESG_RAW_WRITE_QUALIFICATION_LIVE_V1' \
	'run-same-value-write-20260819-a' 'GAEL-20260816-A'; do
	! grep -aFq "$forbidden" "$image" || die "forbidden Image token returned: $forbidden"
done

fdt_string() { fdtget -t s "$dtb" "$1" "$2"; }
fdt_hex() { fdtget -t x "$dtb" "$1" "$2"; }
observer=/a72-physical-source-observer
platform=/a72-platform-state@10222000
clock=/dvfsp-clock-backend@1001a000
bigidvfs=/dvfsp-bigidvfs-backend
[[ "$(fdt_string "$observer" compatible)" == mediatek,mt6797-a72-physical-source-observer ]] ||
	die 'observer compatible changed'
for node in "$observer" "$platform" "$clock" "$bigidvfs"; do
	[[ "$(fdt_string "$node" status)" == okay ]] || die "candidate node is not okay: $node"
done
[[ "$(fdt_string "$bigidvfs" method)" == smc ]] || die 'BigiDVFS method changed'
[[ "$(fdt_string /dvfsp-resource-owner status)" == disabled ]] ||
	die 'unrelated DVFSP resource owner became active'
[[ "$(fdt_hex "$observer" mediatek,platform-state)" == "$(fdt_hex "$platform" phandle)" ]] ||
	die 'platform phandle changed'
[[ "$(fdt_hex "$observer" mediatek,clock-backend)" == "$(fdt_hex "$clock" phandle)" ]] ||
	die 'clock phandle changed'
[[ "$(fdt_hex "$observer" mediatek,bigidvfs-backend)" == "$(fdt_hex "$bigidvfs" phandle)" ]] ||
	die 'BigiDVFS phandle changed'

workdir=$(mktemp -d "$output_parent/.a72-physical-source.XXXXXXXX")
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

for root in "$stage" "$replica"; do
	python3 "$serializer" --kernel "$image_gz" --ramdisk "$ramdisk" \
		--dtb "$dtb" --output "$root/$BOOT_FILE" \
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
	--expected-ramdisk "$ramdisk" --expected-dtb "$dtb" \
	--expected-name "$BOOT_NAME" --expected-cmdline "$BOOT_CMDLINE" \
	"$stage/$BOOT_FILE" >"$stage/container-analysis.txt"
[[ "$(grep -c '^gate_.*=yes$' "$stage/container-analysis.txt")" == 32 ]] ||
	die 'LK analyzer did not pass all 32 gates'
grep -qx 'lk_validation=passed' "$stage/container-analysis.txt" ||
	die 'LK validation failed'

raw_size=$(wc -c <"$stage/$BOOT_FILE" | tr -d ' ')
raw_sha256=$(sha256sum "$stage/$BOOT_FILE" | awk '{print $1}')
padded_sha256=$(sha256sum "$stage/boot2-padded.img" | awk '{print $1}')
[[ "$raw_size" == "$RAW_SIZE" && "$raw_sha256" == "$RAW_SHA256" ]] ||
	die 'raw candidate identity changed'
[[ "$(wc -c <"$stage/boot2-padded.img" | tr -d ' ')" == "$BOOT2_SIZE" &&
	"$padded_sha256" == "$PADDED_SHA256" ]] || die 'padded candidate identity changed'
grep -v '^output=' "$stage/serializer.txt" >"$stage/serializer.normalized"
mv "$stage/serializer.normalized" "$stage/serializer.txt"

{
	printf 'validation=portable-fetched-a72-physical-source-package\n'
	printf 'repository_commit=%s\nprofile=%s\nkernel_release=%s\n' \
		"$REPOSITORY_COMMIT" "$PROFILE" "$RELEASE"
	printf 'package_manifest_sha256=%s\nsha256sums=passed\n' "$PACKAGE_MANIFEST_SHA256"
	printf 'image_sha256=%s\nimage_gzip_sha256=%s\ndtb_sha256=%s\n' \
		"$IMAGE_SHA256" "$IMAGE_GZIP_SHA256" "$DTB_SHA256"
	printf 'config_sha256=%s\nsystem_map_sha256=%s\nresult=pass\n' \
		"$CONFIG_SHA256" "$SYSTEM_MAP_SHA256"
} >"$stage/package-validation.txt"
{
	printf 'experiment=2026-08-24-mainline-a72-physical-source-observer\n'
	printf 'repository_commit=%s\nprofile=%s\nkernel_release=%s\n' \
		"$REPOSITORY_COMMIT" "$PROFILE" "$RELEASE"
	printf 'image_sha256=%s\nimage_gzip_sha256=%s\ndtb_sha256=%s\n' \
		"$IMAGE_SHA256" "$IMAGE_GZIP_SHA256" "$DTB_SHA256"
	printf 'config_sha256=%s\nsystem_map_sha256=%s\n' "$CONFIG_SHA256" "$SYSTEM_MAP_SHA256"
	printf 'ramdisk_sha256=%s\nramdisk_baseline=exact-da921x-serviceability\n' "$RAMDISK_SHA256"
	printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$RAW_SHA256" "$RAW_SIZE"
	printf 'padded_sha256=%s\npadded_size=%s\n' "$PADDED_SHA256" "$BOOT2_SIZE"
	printf 'lk_name=%s\nlk_cmdline=%s\nlk_gates=32-of-32\n' "$BOOT_NAME" "$BOOT_CMDLINE"
	printf 'independent_raw_assemblies=byte-identical\n'
	printf 'independent_padding_constructions=byte-identical\n'
	printf 'runtime_hypothesis=one-all-or-zero-direct-physical-source-snapshot\n'
	printf 'retained_record_commits_expected=maximum-2\n'
	printf 'platform_calls_expected=1\nprovider_snapshots_expected=1\n'
	printf 'protected_clock_reads_expected=1\nbigidvfs_calls_expected=1\n'
	printf 'bigidvfs_smc_reads_expected=8\nprovider_transactions_expected=0\n'
	printf 'publisher_calls_expected=0\nowner_mutations_expected=0\n'
	printf 'cpu8_cpu9_requests_expected=0\n'
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

output_name="candidate-a72-physical-source-${RAW_SHA256:0:8}"
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
printf 'validation=a72-physical-source-candidate-build\n'
printf 'artifact=%s\ncandidate_sha256=%s\npadded_sha256=%s\n' \
	"$output" "$RAW_SHA256" "$PADDED_SHA256"
printf 'device_access=none\nhardware_write=none\n'
printf 'boot_candidate=pending-independent-validation\n'
