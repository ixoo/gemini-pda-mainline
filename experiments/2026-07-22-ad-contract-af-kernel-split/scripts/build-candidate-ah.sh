#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --af-artifact DIR --ag-artifact DIR --ad-artifact DIR --output-parent DIR\n' "$0" >&2
}

af_artifact=
ag_artifact=
ad_artifact=
output_parent=
while (($#)); do
	case "$1" in
	--af-artifact|--ag-artifact|--ad-artifact|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--af-artifact) af_artifact=$2 ;;
		--ag-artifact) ag_artifact=$2 ;;
		--ad-artifact) ad_artifact=$2 ;;
		--output-parent) output_parent=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die 'run in the Linux development VM'
case "$(uname -m)" in aarch64|arm64) ;; *) die 'expected Linux AArch64' ;; esac
for directory in "$af_artifact" "$ag_artifact" "$ad_artifact" "$output_parent"; do
	[[ -d "$directory" && ! -L "$directory" ]] || \
		die "unsafe or missing directory: $directory"
done
for command in awk bash chmod cmp dirname find grep install mkdir mktemp mv \
	python3 rm sed sha256sum sort tr uname wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "$script_dir/.." && pwd -P)"
repo_root="$(cd -- "$experiment_dir/../.." && pwd -P)"
af_artifact="$(cd -- "$af_artifact" && pwd -P)"
ag_artifact="$(cd -- "$ag_artifact" && pwd -P)"
ad_artifact="$(cd -- "$ad_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$af_artifact"|"$af_artifact"/*|\
"$ag_artifact"|"$ag_artifact"/*|"$ad_artifact"|"$ad_artifact"/*)
	die 'output parent must be outside the repository and all selected inputs'
	;;
esac

lineage_validator="$script_dir/validate-lineage.py"
dtb_builder="$script_dir/build-ah-dtb.sh"
boot_validator="$script_dir/validate-boot.py"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for input in "$lineage_validator" "$dtb_builder" "$boot_validator" \
	"$serializer" "$analyzer"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || \
		die "repository input missing or unsafe: $input"
done

af_boot="$af_artifact/gemini-a72-observer-initcall-diagnostic.boot.img"
ag_boot="$ag_artifact/gemini-simplefb-observation-restoration.boot.img"
ad_boot="$ad_artifact/gemini-smp8.boot.img"
ad_dtb="$ad_artifact/mt6797-gemini-pda-smp8.dtb"
ag_initramfs="$ag_artifact/gemini-simplefb-observation-restoration-initramfs.img"
for input in "$af_boot" "$ag_boot" "$ad_boot" "$ad_dtb" "$ag_initramfs"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || \
		die "artifact input missing or unsafe: $input"
done

workdir="$(mktemp -d "$output_parent/.candidate-AH-component-split.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

python3 "$lineage_validator" --af-artifact "$af_artifact" \
	--ag-artifact "$ag_artifact" --ad-artifact "$ad_artifact" \
	>"$stage/lineage-validation.txt"

install -m 0600 "$ag_artifact/Image.gz" "$stage/Image.gz"
install -m 0600 "$ag_artifact/System.map" "$stage/System.map"
install -m 0600 "$ag_artifact/kernel.config" "$stage/kernel.config"
install -m 0600 "$ag_artifact/source-build.json" "$stage/source-build.json"
install -m 0600 "$ag_initramfs" \
	"$stage/gemini-ad-contract-af-kernel-split-initramfs.img"
install -m 0600 "$ag_artifact/gemini-us.bkeymap" "$stage/gemini-us.bkeymap"
install -m 0755 "$ag_artifact/console-unicode-mode" "$stage/console-unicode-mode"
install -m 0755 "$ag_artifact/console-keymap-verify" "$stage/console-keymap-verify"
install -m 0755 "$ag_artifact/input-event-capture" "$stage/input-event-capture"

ah_dtb="$stage/mt6797-gemini-pda-ad-contract-af-kernel-split.dtb"
replica_dtb="$replica/mt6797-gemini-pda-ad-contract-af-kernel-split.dtb"
bash "$dtb_builder" --ad-dtb "$ad_dtb" --output "$ah_dtb" \
	>"$stage/dtb-validation.raw"
bash "$dtb_builder" --ad-dtb "$ad_dtb" --output "$replica_dtb" >/dev/null
cmp -s "$ah_dtb" "$replica_dtb" || die 'two independent AH DT transforms differ'
sed -e "s|$ah_dtb|@AH_DTB@|g" "$stage/dtb-validation.raw" \
	>"$stage/dtb-validation.txt"
rm "$stage/dtb-validation.raw"

candidate="$stage/gemini-ad-contract-af-kernel-split.boot.img"
replica_boot="$replica/gemini-ad-contract-af-kernel-split.boot.img"
bootopt=bootopt=64S3,32N2,64N2
python3 "$serializer" --kernel "$stage/Image.gz" \
	--ramdisk "$stage/gemini-ad-contract-af-kernel-split-initramfs.img" \
	--dtb "$ah_dtb" --output "$candidate" --name gemini-obs-L \
	--cmdline "$bootopt" --kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
	--tags-addr 0x44000000 --lk-android8 >"${candidate}.serializer"
python3 "$serializer" --kernel "$stage/Image.gz" \
	--ramdisk "$stage/gemini-ad-contract-af-kernel-split-initramfs.img" \
	--dtb "$replica_dtb" --output "$replica_boot" --name gemini-obs-L \
	--cmdline "$bootopt" --kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
	--tags-addr 0x44000000 --lk-android8 >"${replica_boot}.serializer"
cmp -s "$candidate" "$replica_boot" || die 'two Candidate AH constructions differ'
grep -v '^output=' "${candidate}.serializer" >"$stage/serializer.txt"
rm "${candidate}.serializer" "${replica_boot}.serializer"

python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/gemini-ad-contract-af-kernel-split-initramfs.img" \
	--expected-dtb "$ah_dtb" --expected-name gemini-obs-L \
	--expected-cmdline "$bootopt" "$candidate" >"$stage/analysis.raw"
sed -e "s|$workdir|@WORK@|g" -e "s|$repo_root|@REPOSITORY@|g" \
	"$stage/analysis.raw" >"$stage/analysis.txt"
rm "$stage/analysis.raw"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] || \
	die 'LK analyzer did not emit 32 gates'

python3 "$boot_validator" --af-boot "$af_boot" --ag-boot "$ag_boot" \
	--ad-boot "$ad_boot" --candidate "$candidate" --image-gz "$stage/Image.gz" \
	--ad-dtb "$ad_dtb" --ah-dtb "$ah_dtb" \
	--initramfs "$stage/gemini-ad-contract-af-kernel-split-initramfs.img" \
	>"$stage/boot-validation.txt"

candidate_sha256="$(sha256sum "$candidate" | awk '{ print $1 }')"
candidate_size="$(wc -c <"$candidate" | tr -d ' ')"
dtb_sha256="$(sha256sum "$ah_dtb" | awk '{ print $1 }')"
{
	printf 'experiment=2026-07-22-ad-contract-af-kernel-split\n'
	printf 'candidate_label=AH\n'
	printf 'candidate_sha256=%s\n' "$candidate_sha256"
	printf 'candidate_size=%s\n' "$candidate_size"
	printf 'candidate_dtb_sha256=%s\n' "$dtb_sha256"
	printf 'af_boot_sha256=fe43efa8c9d18174fec97ab7ad6cbe59bbc490df92366bcd254c55daa932d0a3\n'
	printf 'ag_boot_sha256=0552986c885d89fd65d05f3da8513040f756c9cfc84b1b30e1e085ee68238a91\n'
	printf 'ad_boot_sha256=a1b61d8c34b5a447f1f672663f4e74fed6eb465b90154392a3c42f4db030826b\n'
	printf 'image_gz_sha256=b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912\n'
	printf 'system_map_sha256=a0bf3087fb2225e17192606cb2150204ce89cfb51ea0719e4ce200800b1a407d\n'
	printf 'config_sha256=bfd71f6618fab738d378530f73d1c75d73c69f19334b84d9c663aaa98740eb63\n'
	printf 'initramfs_sha256=166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3\n'
	printf 'ad_dtb_sha256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f\n'
	printf 'kernel_config_system_map_initramfs_helpers=byte-exact-candidate-af-and-ag\n'
	printf 'initramfs_keymap_helpers_also=byte-exact-candidate-ad\n'
	printf 'dtb_baseline=byte-exact-hardware-passed-candidate-ad\n'
	printf 'dtb_delta=cpu8-and-cpu9-enable-method-only\n'
	printf 'cpu8_cpu9_enable_method=mediatek,mt6797-psci-rejecting\n'
	printf 'simplefb_usb_keyboard_scp_reserved_memory=byte-exact-candidate-ad\n'
	printf 'a72_power_da9214_static_lk_framebuffer_nodes=absent\n'
	printf 'blacklisted_initcall=mt6797_a72_power_driver_init\n'
	printf 'patch_profile_manifest=unchanged-file-only-component-split\n'
	printf 'storage_access=none\nwatchdog_userspace=none\n'
	printf 'active_a72_operation=none\nraw_framebuffer_write=none\n'
	printf 'artifact_builder_device_access=none\nflash=none\nruntime_result=not-tested\n'
} >"$stage/provenance.txt"

expected_inventory="$(printf '%s\n' Image.gz System.map analysis.txt \
	boot-validation.txt console-keymap-verify console-unicode-mode \
	dtb-validation.txt gemini-ad-contract-af-kernel-split.boot.img \
	gemini-ad-contract-af-kernel-split-initramfs.img gemini-us.bkeymap \
	input-event-capture kernel.config lineage-validation.txt \
	mt6797-gemini-pda-ad-contract-af-kernel-split.dtb provenance.txt \
	serializer.txt source-build.json | sort)"
actual_inventory="$(find "$stage" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)"
unexpected_entry="$(find "$stage" -mindepth 1 -maxdepth 1 ! -type f -print -quit)"
[[ -z "$unexpected_entry" && "$actual_inventory" == "$expected_inventory" ]] || \
	die 'Candidate AH output inventory changed'
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate AH manifest failed'
final_inventory="$(find "$stage" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)"
[[ "$final_inventory" == "$(printf '%s\n%s\n' "$expected_inventory" SHA256SUMS | sort)" ]] || \
	die 'Candidate AH manifest publication changed the inventory'
chmod 0600 "$stage"/*
chmod 0755 "$stage/console-keymap-verify" "$stage/console-unicode-mode" \
	"$stage/input-event-capture"

output_name="candidate-AH-ad-contract-af-kernel-split-${candidate_sha256:0:8}"
artifact="$workdir/$output_name"
mv -n "$stage" "$artifact"
[[ -d "$artifact" && ! -e "$stage" ]] || die 'internal AH publication failed'
stage=
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv -n "$artifact" "$output"
[[ -d "$output" && ! -e "$artifact" ]] || die 'exclusive AH publication failed'
workdir=
trap - EXIT
printf 'validation=candidate-ah-ad-contract-af-kernel-split\n'
printf 'artifact=%s\n' "$output"
printf 'candidate=%s/gemini-ad-contract-af-kernel-split.boot.img\n' "$output"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$candidate_sha256" "$candidate_size"
printf 'dtb_sha256=%s\nruntime_result=not-tested\n' "$dtb_sha256"
