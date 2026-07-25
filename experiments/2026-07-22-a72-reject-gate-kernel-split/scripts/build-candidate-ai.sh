#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package AI_PACKAGE --ad-package AD_PACKAGE --ad-artifact DIR --ah-artifact DIR --af-artifact DIR --output-parent DIR\n' "$0" >&2
}

package=
ad_package=
ad_artifact=
ah_artifact=
af_artifact=
output_parent=
while (($#)); do
	case "$1" in
	--package|--ad-package|--ad-artifact|--ah-artifact|--af-artifact|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--package) package=$2 ;;
		--ad-package) ad_package=$2 ;;
		--ad-artifact) ad_artifact=$2 ;;
		--ah-artifact) ah_artifact=$2 ;;
		--af-artifact) af_artifact=$2 ;;
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
for directory in "$package" "$ad_package" "$ad_artifact" "$ah_artifact" \
	"$af_artifact" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] || \
		die "unsafe or missing directory: $directory"
done
for command in awk bash basename chmod cmp find grep install mkdir mktemp \
	objdump python3 rm rmdir sed sha256sum sort tr uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
ad_package="$(cd -- "$ad_package" && pwd -P)"
ad_artifact="$(cd -- "$ad_artifact" && pwd -P)"
ah_artifact="$(cd -- "$ah_artifact" && pwd -P)"
af_artifact="$(cd -- "$af_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$package"|"$package"/*|"$ad_package"|"$ad_package"/*|\
"$ad_artifact"|"$ad_artifact"/*|"$ah_artifact"|"$ah_artifact"/*|\
"$af_artifact"|"$af_artifact"/*)
	die 'output parent must be outside the repository and all selected inputs'
	;;
esac

lineage_validator="$script_dir/validate-lineage.py"
series_validator="$script_dir/validate-series-selection.py"
package_validator="$script_dir/validate-package.py"
boot_validator="$script_dir/validate-boot.py"
gate_auditor="$script_dir/audit-mt6797-psci-cpu-boot.py"
finalizer="$script_dir/finalize-artifact.py"
normalizer="$repo_root/experiments/2026-07-22-cortex-a72-observer-initcall-diagnostic/scripts/normalize-build-json.py"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
patch_0092="$repo_root/patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch"
for input in "$lineage_validator" "$series_validator" "$package_validator" "$boot_validator" \
	"$gate_auditor" "$finalizer" "$normalizer" "$serializer" "$analyzer" "$patch_0092"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || \
		die "repository input missing or unsafe: $input"
done
[[ "$(sha256sum "$normalizer" | awk '{print $1}')" == \
	bb7c1ad5b9b200b1db0a397a97cb1e69c5748de848a1f43dbcec8c9a4aade9ab ]] || \
	die 'source-pinned build normalizer changed'
[[ "$(sha256sum "$serializer" | awk '{print $1}')" == \
	569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4 ]] || \
	die 'source-pinned Android-v0 serializer changed'
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == \
	aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95 ]] || \
	die 'source-pinned LK analyzer changed'
[[ "$(sha256sum "$patch_0092" | awk '{print $1}')" == \
	cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5 ]] || \
	die 'corrected patch 0092 changed'

workdir="$(mktemp -d "$output_parent/.candidate-AI-gate-split.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

python3 "$series_validator" --repository "$repo_root" \
	>"$stage/series-validation.txt"
python3 "$lineage_validator" --ad-artifact "$ad_artifact" \
	--ah-artifact "$ah_artifact" --af-artifact "$af_artifact" \
	>"$stage/lineage-validation.txt"
python3 "$package_validator" --ad-package "$ad_package" \
	--candidate-package "$package" --patch-0092 "$patch_0092" \
	>"$stage/package-validation.raw"
sed -e "s|$repo_root|@REPOSITORY@|g" -e "s|$workdir|@WORK@|g" \
	-e "s|$package|@AI_PACKAGE@|g" -e "s|$ad_package|@AD_PACKAGE@|g" \
	"$stage/package-validation.raw" >"$stage/package-validation.txt"
rm "$stage/package-validation.raw"

readonly AD_INITRAMFS=gemini-usb-gadget-ethernet-initramfs.img
readonly AH_DTB=mt6797-gemini-pda-ad-contract-af-kernel-split.dtb
readonly AI_INITRAMFS=gemini-a72-reject-gate-kernel-split-initramfs.img
readonly AI_DTB=mt6797-gemini-pda-a72-reject-gate-kernel-split.dtb
readonly AI_BOOT=gemini-a72-reject-gate-kernel-split.boot.img

install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
install -m 0600 "$package/kernel.config" "$stage/kernel.config"
python3 "$normalizer" --input "$package/provenance/build.json" \
	--output "$stage/source-build.json"
install -m 0600 "$ad_artifact/$AD_INITRAMFS" "$stage/$AI_INITRAMFS"
install -m 0600 "$ah_artifact/$AH_DTB" "$stage/$AI_DTB"
install -m 0600 "$ad_artifact/gemini-us.bkeymap" "$stage/gemini-us.bkeymap"
install -m 0755 "$ad_artifact/console-unicode-mode" "$stage/console-unicode-mode"
install -m 0755 "$ad_artifact/console-keymap-verify" "$stage/console-keymap-verify"
install -m 0755 "$ad_artifact/input-event-capture" "$stage/input-event-capture"

candidate="$stage/$AI_BOOT"
replica_boot="$replica/$AI_BOOT"
boot_cmdline=bootopt=64S3,32N2,64N2
for output in "$candidate" "$replica_boot"; do
	python3 "$serializer" --kernel "$stage/Image.gz" \
		--ramdisk "$stage/$AI_INITRAMFS" --dtb "$stage/$AI_DTB" \
		--output "$output" --name gemini-obs-L --cmdline "$boot_cmdline" \
		--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
		--second-addr 0x40f00000 --tags-addr 0x44000000 \
		--lk-android8 >"${output}.serializer"
done
cmp -s "$candidate" "$replica_boot" || \
	die 'two Candidate AI container constructions differ'
grep -v '^output=' "${candidate}.serializer" >"$stage/serializer.txt"
rm "${candidate}.serializer" "${replica_boot}.serializer"

python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/$AI_INITRAMFS" --expected-dtb "$stage/$AI_DTB" \
	--expected-name gemini-obs-L --expected-cmdline "$boot_cmdline" "$candidate" \
	>"$stage/analysis.raw"
sed -e "s|$workdir|@WORK@|g" -e "s|$repo_root|@REPOSITORY@|g" \
	"$stage/analysis.raw" >"$stage/analysis.txt"
rm "$stage/analysis.raw"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] || \
	die 'LK analyzer did not emit exactly 32 gates'

python3 "$boot_validator" --candidate "$candidate" --image-gz "$stage/Image.gz" \
	--dtb "$stage/$AI_DTB" --initramfs "$stage/$AI_INITRAMFS" \
	--kernel-config "$stage/kernel.config" --system-map "$stage/System.map" \
	--ad-boot "$ad_artifact/gemini-smp8.boot.img" \
	--ah-boot "$ah_artifact/gemini-ad-contract-af-kernel-split.boot.img" \
	--af-boot "$af_artifact/gemini-a72-observer-initcall-diagnostic.boot.img" \
	>"$stage/boot-validation.txt"

python3 "$gate_auditor" --image "$package/Image" \
	--system-map "$package/System.map" \
	>"$stage/mt6797-psci-cpu-boot-audit.txt"

candidate_sha256="$(sha256sum "$candidate" | awk '{print $1}')"
candidate_size="$(wc -c <"$candidate" | tr -d ' ')"
image_sha256="$(sha256sum "$stage/Image.gz" | awk '{print $1}')"
system_map_sha256="$(sha256sum "$stage/System.map" | awk '{print $1}')"
source_build_sha256="$(sha256sum "$stage/source-build.json" | awk '{print $1}')"
gate_audit_sha256="$(sha256sum "$stage/mt6797-psci-cpu-boot-audit.txt" | awk '{print $1}')"
{
	printf 'experiment=2026-07-22-a72-reject-gate-kernel-split\n'
	printf 'candidate_label=AI\n'
	printf 'kernel_profile=observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate\n'
	printf 'series_path=patches/series-a72-reject-gate\n'
	printf 'series_sha256=b172d419cc1e331932e734dda57be076872a442719dd6d406b217d81547dfd00\n'
	printf 'patchset_sha256=ba2cd5a66bd1fcff6552674d6d875d363e4ef0a24cfd10ede4f304136f0dc0dd\n'
	printf 'patch_delta_from_ad=corrected-0092-only\n'
	printf 'patches_0088_0091=absent\n'
	printf 'config_inputs_sha256=ad93d6669bd261cf1171237328dd9209fd45b2c3ed2154e441a1951908da4ba1\n'
	printf 'config_sha256=32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46\n'
	printf 'candidate_sha256=%s\n' "$candidate_sha256"
	printf 'candidate_size=%s\n' "$candidate_size"
	printf 'candidate_image_gz_sha256=%s\n' "$image_sha256"
	printf 'candidate_system_map_sha256=%s\n' "$system_map_sha256"
	printf 'candidate_source_build_sha256=%s\n' "$source_build_sha256"
	printf 'compiled_gate_audit_sha256=%s\n' "$gate_audit_sha256"
	printf 'candidate_dtb_sha256=27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845\n'
	printf 'candidate_initramfs_sha256=166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3\n'
	printf 'final_dtb_lineage=byte-exact-candidate-ah\n'
	printf 'initramfs_helpers_lineage=byte-exact-candidate-ad\n'
	printf 'cpu_policy=maxcpus-8-cpu8-cpu9-not-requested\n'
	printf 'regulator_reset_observer_paths=absent\n'
	printf 'active_cpu_request=none\n'
	printf 'storage_access=none\nwatchdog_userspace=none\nuserspace_automatic_reboot=none\n'
	printf 'artifact_builder_device_access=none\nflash=none\nruntime_result=not-tested\n'
} >"$stage/provenance.txt"

python3 "$finalizer" --stage "$stage" >/dev/null

output_name="candidate-AI-a72-reject-gate-${candidate_sha256:0:8}"
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
python3 "$finalizer" --publish "$stage" --output "$output" >/dev/null
[[ ! -e "$stage" && ! -L "$stage" ]] || \
	die 'atomic publication did not consume the staging tree'
stage=
rm -rf -- "$replica"
rmdir "$workdir"
workdir=
trap - EXIT
printf 'validation=candidate-ai-a72-reject-gate\nartifact=%s\n' "$output"
printf 'candidate=%s/%s\n' "$output" "$AI_BOOT"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$candidate_sha256" "$candidate_size"
printf 'image_gz_sha256=%s\nsystem_map_sha256=%s\n' "$image_sha256" "$system_map_sha256"
printf 'runtime_result=not-tested\n'
