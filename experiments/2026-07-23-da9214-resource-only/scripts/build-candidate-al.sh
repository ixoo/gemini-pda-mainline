#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --ah-artifact DIR --ak-artifact DIR --output-parent DIR\n' "$0" >&2
}

ah_artifact=
ak_artifact=
output_parent=
while (($#)); do
	case "$1" in
	--ah-artifact|--ak-artifact|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--ah-artifact) ah_artifact=$2 ;;
		--ak-artifact) ak_artifact=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die 'run in the Linux recovery VM'
case "$(uname -m)" in aarch64|arm64) ;; *) die 'expected Linux AArch64' ;; esac
for directory in "$ah_artifact" "$ak_artifact" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] || \
		die "unsafe or missing directory: $directory"
done
for command in awk bash basename chmod cmp find grep install mkdir mktemp mv \
	python3 rm rmdir sed sha256sum sort tr uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
ah_artifact="$(cd -- "$ah_artifact" && pwd -P)"
ak_artifact="$(cd -- "$ak_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$ah_artifact"|"$ah_artifact"/*|\
"$ak_artifact"|"$ak_artifact"/*)
	die 'output parent must be outside the repository and both input artifacts'
	;;
esac

lineage_validator="$script_dir/validate-lineage.py"
dtb_builder="$script_dir/build-al-dtb.sh"
dtb_validator="$script_dir/validate-dtb-delta.py"
boot_validator="$script_dir/validate-boot.py"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
patch_0089="$repo_root/patches/v7.1.3/0089-arm64-dts-mediatek-gemini-describe-DA9214-rail.patch"
for input in "$lineage_validator" "$dtb_builder" "$dtb_validator" \
	"$boot_validator" "$serializer" "$analyzer" "$patch_0089"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || \
		die "repository input missing or unsafe: $input"
done
[[ "$(sha256sum "$serializer" | awk '{ print $1 }')" == \
	569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4 ]] || \
	die 'source-pinned Android-v0 serializer changed'
[[ "$(sha256sum "$analyzer" | awk '{ print $1 }')" == \
	aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95 ]] || \
	die 'source-pinned LK analyzer changed'
[[ "$(sha256sum "$patch_0089" | awk '{ print $1 }')" == \
	5626670d4d4b39e8b8e9b1e803bcb9a847068690046531a7132a4dda6936248b ]] || \
	die 'source-pinned patch 0089 changed'

readonly AH_DTB=mt6797-gemini-pda-ad-contract-af-kernel-split.dtb
readonly AH_INITRAMFS=gemini-ad-contract-af-kernel-split-initramfs.img
readonly AL_DTB=mt6797-gemini-pda-da9214-resource-only.dtb
readonly AL_INITRAMFS=gemini-da9214-resource-only-initramfs.img
readonly AL_BOOT=gemini-da9214-resource-only.boot.img

workdir="$(mktemp -d "$output_parent/.candidate-AL-da9214-resource.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

python3 "$lineage_validator" --ah-artifact "$ah_artifact" \
	--ak-artifact "$ak_artifact" >"$stage/lineage-validation.txt"

install -m 0600 "$ah_artifact/Image.gz" "$stage/Image.gz"
install -m 0600 "$ah_artifact/System.map" "$stage/System.map"
install -m 0600 "$ah_artifact/kernel.config" "$stage/kernel.config"
install -m 0600 "$ah_artifact/source-build.json" "$stage/source-build.json"
install -m 0600 "$ah_artifact/$AH_INITRAMFS" "$stage/$AL_INITRAMFS"
install -m 0600 "$ah_artifact/gemini-us.bkeymap" "$stage/gemini-us.bkeymap"
install -m 0755 "$ah_artifact/console-unicode-mode" "$stage/console-unicode-mode"
install -m 0755 "$ah_artifact/console-keymap-verify" "$stage/console-keymap-verify"
install -m 0755 "$ah_artifact/input-event-capture" "$stage/input-event-capture"

bash "$dtb_builder" --ah-dtb "$ah_artifact/$AH_DTB" \
	--output "$stage/$AL_DTB" >"$stage/dtb-validation.raw"
bash "$dtb_builder" --ah-dtb "$ah_artifact/$AH_DTB" \
	--output "$replica/$AL_DTB" >/dev/null
cmp -s "$stage/$AL_DTB" "$replica/$AL_DTB" || \
	die 'two independent Candidate AL DT derivations differ'
sed -e "s|$stage/$AL_DTB|@AL_DTB@|g" \
	"$stage/dtb-validation.raw" >"$stage/dtb-validation.txt"
rm "$stage/dtb-validation.raw"

candidate="$stage/$AL_BOOT"
replica_boot="$replica/$AL_BOOT"
boot_cmdline=bootopt=64S3,32N2,64N2
for output in "$candidate" "$replica_boot"; do
	python3 "$serializer" --kernel "$stage/Image.gz" \
		--ramdisk "$stage/$AL_INITRAMFS" --dtb "$stage/$AL_DTB" \
		--output "$output" --name gemini-obs-L --cmdline "$boot_cmdline" \
		--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
		--second-addr 0x40f00000 --tags-addr 0x44000000 \
		--lk-android8 >"${output}.serializer"
done
cmp -s "$candidate" "$replica_boot" || \
	die 'two independent Candidate AL container assemblies differ'
grep -v '^output=' "${candidate}.serializer" >"$stage/serializer.txt"
rm "${candidate}.serializer" "${replica_boot}.serializer"

python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/$AL_INITRAMFS" \
	--expected-dtb "$stage/$AL_DTB" --expected-name gemini-obs-L \
	--expected-cmdline "$boot_cmdline" "$candidate" >"$stage/analysis.raw"
sed -e "s|$workdir|@WORK@|g" -e "s|$repo_root|@REPOSITORY@|g" \
	"$stage/analysis.raw" >"$stage/analysis.txt"
rm "$stage/analysis.raw"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] || \
	die 'LK analyzer did not emit exactly 32 gates'

python3 "$boot_validator" --ah-artifact "$ah_artifact" \
	--candidate "$candidate" --dtb "$stage/$AL_DTB" \
	--image-gz "$stage/Image.gz" --system-map "$stage/System.map" \
	--kernel-config "$stage/kernel.config" --initramfs "$stage/$AL_INITRAMFS" \
	>"$stage/boot-validation.txt"

candidate_sha256="$(sha256sum "$candidate" | awk '{ print $1 }')"
candidate_size="$(wc -c <"$candidate" | tr -d ' ')"
dtb_sha256="$(sha256sum "$stage/$AL_DTB" | awk '{ print $1 }')"
{
	printf 'experiment=2026-07-23-da9214-resource-only\n'
	printf 'candidate_label=AL\n'
	printf 'candidate_sha256=%s\ncandidate_size=%s\n' \
		"$candidate_sha256" "$candidate_size"
	printf 'candidate_dtb_sha256=%s\n' "$dtb_sha256"
	printf 'ah_raw_sha256=e5ba6ee0a257b804a02af11b83e733f861b89de17470470a497f07056b6b3197\n'
	printf 'ah_dtb_sha256=27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845\n'
	printf 'image_gz_sha256=b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912\n'
	printf 'system_map_sha256=a0bf3087fb2225e17192606cb2150204ce89cfb51ea0719e4ce200800b1a407d\n'
	printf 'config_sha256=bfd71f6618fab738d378530f73d1c75d73c69f19334b84d9c663aaa98740eb63\n'
	printf 'initramfs_sha256=166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3\n'
	printf 'patch_0089_sha256=5626670d4d4b39e8b8e9b1e803bcb9a847068690046531a7132a4dda6936248b\n'
	printf 'ak_installed_predecessor_sha256=66902cb2f2faa5c4c6457ce89ff67aa25e5345ac43ee0ca8062a55e0fbac870e\n'
	printf 'functional_baseline=byte-exact-hardware-passed-candidate-ah\n'
	printf 'ak_functional_payload_reused=no\n'
	printf 'kernel_config_system_map_initramfs=byte-exact-candidate-ah\n'
	printf 'final_dtb_baseline=exact-candidate-ah-final-dtb\n'
	printf 'final_dtb_delta=patch-0089-i2c6-da9214-only\n'
	printf 'maxcpus=8\nobserver_initcall=blacklisted\n'
	printf 'a72_power_node=absent\ncpu8_cpu9_request=none\n'
	printf 'storage_access=none\nwatchdog_userspace=none\n'
	printf 'artifact_builder_device_access=none\nflash=none\nruntime_result=not-tested\n'
} >"$stage/provenance.txt"

expected_pre_manifest="$(printf '%s\n' Image.gz System.map \
	analysis.txt boot-validation.txt console-keymap-verify console-unicode-mode \
	dtb-validation.txt "$AL_BOOT" "$AL_INITRAMFS" gemini-us.bkeymap \
	input-event-capture kernel.config lineage-validation.txt "$AL_DTB" \
	provenance.txt serializer.txt source-build.json | sort)"
actual_inventory="$(find "$stage" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)"
[[ "$actual_inventory" == "$expected_pre_manifest" ]] || \
	die 'Candidate AL output inventory changed'
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate AL artifact manifest failed'
final_inventory="$(find "$stage" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)"
[[ "$final_inventory" == "$(printf '%s\n%s\n' "$expected_pre_manifest" \
	SHA256SUMS | sort)" ]] || die 'Candidate AL manifest publication changed inventory'
chmod 0600 "$stage"/*
chmod 0755 "$stage/console-keymap-verify" "$stage/console-unicode-mode" \
	"$stage/input-event-capture"

output_name="candidate-AL-da9214-resource-only-${candidate_sha256:0:8}"
artifact="$workdir/$output_name"
mv -n "$stage" "$artifact"
stage=
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv -n "$artifact" "$output"
[[ -d "$output" && ! -e "$artifact" ]] || die 'exclusive AL publication failed'
rm -rf -- "$replica"
rmdir "$workdir"
workdir=
trap - EXIT
printf 'validation=candidate-al-da9214-resource-only\n'
printf 'artifact=%s\ncandidate=%s/%s\n' "$output" "$output" "$AL_BOOT"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$candidate_sha256" "$candidate_size"
printf 'dtb_sha256=%s\nruntime_result=not-tested\n' "$dtb_sha256"
