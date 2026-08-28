#!/usr/bin/env bash

# Assemble the exact one-shot CPU8 admission candidate from the fetched
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
for command in awk chmod cmp cp dd dtc find grep jq mkdir mktemp mv python3 \
	rm rmdir sha256sum sort tr truncate wc xargs; do
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

readonly REPOSITORY_COMMIT=eb87d46ae9d58df1ff336751103745d58eed59fe
readonly PROFILE=a72-admission-durable-candidate
readonly RELEASE=7.1.3-gemini-a72-admission-trace
readonly PACKAGE_NAME=linux-7.1.3-gemini-a72-admission-durable-candidate-13dd59d3-a15d3567
readonly IMAGE_SHA256=3468c9ccc8c5e965980d283e4e441ab78ca6531a5a44e989ff4d742285f2f3b3
readonly IMAGE_GZIP_SHA256=05c9f1960ac315baf4d20b37f126a7fc700acfc137f5e977650cf916395c3d3b
readonly DTB_SHA256=1bd6ce2ded2e1186503cb0d9d00107964ec27abc48062b9210e1935d38d60509
readonly CONFIG_SHA256=d59b56cfe259fdc4294a3d51c7dcab66ba4b5270bf4b6ea526763fd4dc534c89
readonly SYSTEM_MAP_SHA256=f9d1242a102c4a0e5544991ab8d9f7bd5263e158f0ec5d07d41368fbbc701585
readonly BUILD_JSON_SHA256=d02a8aa8ac144fb590ac4515a1bce4b67d8286fa1bc857bf5135daa4b59d29c5
readonly PACKAGE_MANIFEST_SHA256=27d550c7c88a49331d325ed1cf8dfba64dd6ed2f8fc3ae83c66f7301ea3a0604
readonly RAMDISK_SHA256=e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f
readonly SERIALIZER_SHA256=569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4
readonly ANALYZER_SHA256=aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95
readonly RAW_SHA256=ed6fc5294f5677ed1895bf1157649330c91dd1f6051a6677f2d26972915cd185
readonly PADDED_SHA256=60902c7ba7e5cccd781082d6d17e1bcb273d184751ddc9dde6a64b2e2a58b8d1
readonly RAW_SIZE=6934528
readonly BOOT2_SIZE=16777216
readonly BOOT_NAME=gemini-a72adm
readonly BOOT_CMDLINE=bootopt=64S3,32N2,64N2
readonly BOOT_FILE=gemini-mt6797-a72-admission-trace.boot.img

[[ "$(basename -- "$package")" == "$PACKAGE_NAME" ]] || die 'package directory identity changed'
image="$package/Image"
image_gz="$package/Image.gz"
config="$package/kernel.config"
system_map="$package/System.map"
dtb="$package/dtbs/mediatek/mt6797-gemini-pda-a72-admission.dtb"
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
check_hash "$dtb" "$DTB_SHA256" 'admission DTB'
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
	'CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION=y' \
	'CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR=y' \
	'CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER=y' \
	'CONFIG_MTK_MT6797_A72_PLATFORM_STATE=y' \
	'CONFIG_MTK_MT6797_A72_PLATFORM_EFFECTS=y' \
	'CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y' \
	'CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y' \
	'CONFIG_MTK_MT6797_A72_BIGIDVFS_SRAM_OWNER=y' \
	'CONFIG_MTK_MT6797_A72_TRANSITION_EXECUTOR=y' \
	'CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER=y' \
	'CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y' \
	'CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER=y' \
	'CONFIG_PSTORE_GEMINI_TRANSITION_LEDGER=y' \
	'CONFIG_PSTORE_GEMINI_ADMISSION_TRACE=y' \
	'# CONFIG_KUNIT is not set' \
	'CONFIG_LOCALVERSION="-gemini-a72-admission-trace"'; do
	grep -Fqx "$gate" "$config" || die "configuration gate changed: $gate"
done
! grep -Fqx 'CONFIG_HOTPLUG_SPLIT_STARTUP=y' "$config" ||
	die 'split-startup experiment is enabled'
for symbol in \
	PSTORE_GEMINI_PROTECTED_READBACK_LEDGER \
	PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER \
	PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER \
	PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER \
	PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER; do
	! grep -Fqx "CONFIG_${symbol}=y" "$config" ||
		die "conflicting retained ledger enabled: $symbol"
done
grep -Eq '^CONFIG_CMDLINE=".*maxcpus=8( |")' "$config" ||
	die 'maxcpus=8 closure is absent'

for symbol in \
	mt6797_a72_admission_run \
	mt6797_a72_binder_available \
	mt6797_a72_binder_cpu_boot \
	mt6797_a72_physical_source_capture \
	mt6797_a72_source_register \
	mt6797_a72_membership_derive_cpu8 \
	mt6797_a72_membership_publish_up \
	gemini_transition_ledger_checkpoint \
	gemini_admission_trace_owner_entry \
	gemini_admission_trace_owner_zero_request \
	mt6797_a72_transition_run \
	add_cpu; do
	[[ "$(grep -c " [A-Za-z] ${symbol}$" "$system_map")" == 1 ]] ||
		die "required symbol absent or duplicated: $symbol"
done
! grep -Eq 'mt6797_a72_.*_test' "$system_map" || die 'KUnit symbol linked'

marker='GEMINI_A72_ADMISSION_V1 state=terminal ret=%d consumed=1 requests=%u/0/0 retries=0'
[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d ' ')" == 1 ]] ||
	die 'admission runtime marker is not unique'
for marker in \
	'GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A kind=entry slot=2' \
	'GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A kind=zero-source-register slot=3' \
	'GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A kind=zero-derive slot=3' \
	'GEMINI_A72_ADMISSION_TRACE_V1 token=GAAT-20260828-A kind=zero-publish slot=3'; do
	[[ "$(grep -aFo "$marker" "$image" | wc -l | tr -d ' ')" == 1 ]] ||
		die "durable trace marker is not unique: $marker"
done

workdir=$(mktemp -d "$output_parent/.a72-admission.XXXXXXXX")
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

dtc -I dtb -O dts "$dtb" >"$stage/candidate.dts" 2>"$stage/dtc-warnings.txt"
python3 - "$stage/candidate.dts" <<'PY'
from pathlib import Path
import re
import sys


text = Path(sys.argv[1]).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"DT validation failed: {message}")


def node_block(name: str) -> str:
    match = re.search(
        rf"\n(?P<indent>\t+){re.escape(name)} \{{\n(?P<body>.*?)\n(?P=indent)\}};",
        text,
        re.DOTALL,
    )
    require(match is not None, f"missing node {name}")
    return match.group("body")


def prop(block: str, name: str) -> str:
    match = re.search(rf"^\t+{re.escape(name)} = (.*);$", block, re.MULTILINE)
    require(match is not None, f"missing property {name}")
    return match.group(1)


require(text.count('compatible = "mediatek,mt6797-a72-admission-controller";') == 1,
        "one admission controller")
require(text.count('compatible = "mediatek,mt6797-a72-binder";') == 1,
        "one transition binder")
require('compatible = "mediatek,mt6797-a72-physical-source-observer";' not in text,
        "standalone physical-source observer absent")
nodes = {
    name: node_block(name) for name in (
        "a72-admission-controller", "a72-binder",
        "a72-platform-state@10222000", "dvfsp-clock-backend@1001a000",
        "dvfsp-bigidvfs-backend", "dvfsp-resource-owner",
    )
}
for name in (
    "a72-admission-controller", "a72-binder",
    "a72-platform-state@10222000", "dvfsp-clock-backend@1001a000",
    "dvfsp-bigidvfs-backend",
):
    require(prop(nodes[name], "status") == '"okay"', f"{name} enabled")
require(prop(nodes["dvfsp-resource-owner"], "status") == '"disabled"',
        "unrelated DVFSP owner disabled")
require(prop(nodes["dvfsp-bigidvfs-backend"], "method") == '"smc"',
        "BigiDVFS SMC method")
binder_phandle = prop(nodes["a72-binder"], "phandle")
platform_phandle = prop(nodes["a72-platform-state@10222000"], "phandle")
clock_phandle = prop(nodes["dvfsp-clock-backend@1001a000"], "phandle")
bigidvfs_phandle = prop(nodes["dvfsp-bigidvfs-backend"], "phandle")
controller = nodes["a72-admission-controller"]
binder = nodes["a72-binder"]
require(prop(controller, "mediatek,binder") == binder_phandle, "controller binder phandle")
require(prop(controller, "mediatek,platform-state") == platform_phandle,
        "controller platform phandle")
require(prop(controller, "mediatek,clock-backend") == clock_phandle,
        "controller clock phandle")
require(prop(controller, "mediatek,bigidvfs-backend") == bigidvfs_phandle,
        "controller BigiDVFS phandle")
require(prop(binder, "mediatek,platform-state") == platform_phandle,
        "binder platform phandle")
require(prop(binder, "mediatek,bigidvfs") == bigidvfs_phandle,
        "binder BigiDVFS phandle")
for cpu in ("cpu@200", "cpu@201"):
    block = node_block(cpu)
    require(prop(block, "compatible") == '"arm,cortex-a72"', f"{cpu} identity")
    require(prop(block, "enable-method") == '"mediatek,mt6797-psci"',
            f"{cpu} enable method")
print("dt_graph_validation=passed")
PY

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
	printf 'validation=portable-fetched-a72-admission-trace-package\n'
	printf 'repository_commit=%s\nprofile=%s\nkernel_release=%s\n' \
		"$REPOSITORY_COMMIT" "$PROFILE" "$RELEASE"
	printf 'package_manifest_sha256=%s\nsha256sums=passed\n' "$PACKAGE_MANIFEST_SHA256"
	printf 'image_sha256=%s\nimage_gzip_sha256=%s\ndtb_sha256=%s\n' \
		"$IMAGE_SHA256" "$IMAGE_GZIP_SHA256" "$DTB_SHA256"
	printf 'config_sha256=%s\nsystem_map_sha256=%s\nresult=pass\n' \
		"$CONFIG_SHA256" "$SYSTEM_MAP_SHA256"
} >"$stage/package-validation.txt"
{
	printf 'experiment=2026-08-28-mainline-a72-admission-durable-candidate\n'
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
	printf 'runtime_hypothesis=one-source-derived-same-task-add-cpu8-request\n'
	printf 'cpu8_requests_expected=1\ncpu9_requests_expected=0\n'
	printf 'retry_paths_expected=0\ncpu_off_paths_expected=0\n'
	printf 'runtime_success=cpu-online-list-is-0-8-and-cpu9-remains-offline\n'
	printf 'failure_evidence=retained-entry-zero-terminal-or-transition-ledger\n'
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

output_name="candidate-a72-admission-trace-${RAW_SHA256:0:8}"
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
printf 'validation=a72-admission-durable-candidate-build\n'
printf 'artifact=%s\ncandidate_sha256=%s\npadded_sha256=%s\n' \
	"$output" "$RAW_SHA256" "$PADDED_SHA256"
printf 'device_access=none\nhardware_write=none\n'
printf 'boot_candidate=pending-independent-validation\n'
