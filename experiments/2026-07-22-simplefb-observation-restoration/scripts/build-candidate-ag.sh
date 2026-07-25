#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --af-artifact DIR --ad-artifact DIR --output-parent DIR\n' "$0" >&2
}

af_artifact=
ad_artifact=
output_parent=
while (($#)); do
	case "$1" in
	--af-artifact|--ad-artifact|--output-parent)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--af-artifact) af_artifact=$2 ;;
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
for directory in "$af_artifact" "$ad_artifact" "$output_parent"; do
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
ad_artifact="$(cd -- "$ad_artifact" && pwd -P)"
output_parent="$(cd -- "$output_parent" && pwd -P)"
case "$output_parent" in
"$repo_root"|"$repo_root"/*|"$af_artifact"|"$af_artifact"/*|"$ad_artifact"|"$ad_artifact"/*)
	die 'output parent must be outside the repository and selected inputs'
	;;
esac

lineage_validator="$script_dir/validate-lineage.py"
dtb_builder="$script_dir/build-simplefb-dtb.sh"
dtb_validator="$script_dir/validate-dtb-delta.py"
boot_validator="$script_dir/validate-boot.py"
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
for input in "$lineage_validator" "$dtb_builder" "$dtb_validator" \
	"$boot_validator" "$serializer" "$analyzer"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || \
		die "repository input missing or unsafe: $input"
done

af_boot="$af_artifact/gemini-a72-observer-initcall-diagnostic.boot.img"
af_dtb="$af_artifact/mt6797-gemini-pda-a72-observer-initcall-diagnostic.dtb"
ad_dtb="$ad_artifact/mt6797-gemini-pda-smp8.dtb"
af_initramfs="$af_artifact/gemini-a72-observer-initcall-diagnostic-initramfs.img"
for input in "$af_boot" "$af_dtb" "$ad_dtb" "$af_initramfs"; do
	[[ -f "$input" && ! -L "$input" && -s "$input" ]] || \
		die "artifact input missing or unsafe: $input"
done

workdir="$(mktemp -d "$output_parent/.candidate-AG-simplefb.XXXXXX")"
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT
stage="$workdir/stage"
replica="$workdir/replica"
mkdir "$stage" "$replica"

python3 "$lineage_validator" --af-artifact "$af_artifact" \
	--ad-artifact "$ad_artifact" >"$stage/lineage-validation.txt"

install -m 0600 "$af_artifact/Image.gz" "$stage/Image.gz"
install -m 0600 "$af_artifact/System.map" "$stage/System.map"
install -m 0600 "$af_artifact/kernel.config" "$stage/kernel.config"
install -m 0600 "$af_artifact/source-build.json" "$stage/source-build.json"
install -m 0600 "$af_initramfs" \
	"$stage/gemini-simplefb-observation-restoration-initramfs.img"
install -m 0600 "$af_artifact/gemini-us.bkeymap" "$stage/gemini-us.bkeymap"
install -m 0755 "$af_artifact/console-unicode-mode" "$stage/console-unicode-mode"
install -m 0755 "$af_artifact/console-keymap-verify" "$stage/console-keymap-verify"
install -m 0755 "$af_artifact/input-event-capture" "$stage/input-event-capture"

ag_dtb="$stage/mt6797-gemini-pda-simplefb-observation-restoration.dtb"
replica_dtb="$replica/mt6797-gemini-pda-simplefb-observation-restoration.dtb"
bash "$dtb_builder" --af-dtb "$af_dtb" --ad-dtb "$ad_dtb" \
	--output "$ag_dtb" >"$stage/dtb-validation.raw"
bash "$dtb_builder" --af-dtb "$af_dtb" --ad-dtb "$ad_dtb" \
	--output "$replica_dtb" >/dev/null
cmp -s "$ag_dtb" "$replica_dtb" || die 'two independent AG DT transforms differ'
sed -e "s|$ag_dtb|@AG_DTB@|g" "$stage/dtb-validation.raw" \
	>"$stage/dtb-validation.txt"
rm "$stage/dtb-validation.raw"

candidate="$stage/gemini-simplefb-observation-restoration.boot.img"
replica_boot="$replica/gemini-simplefb-observation-restoration.boot.img"
bootopt=bootopt=64S3,32N2,64N2
python3 "$serializer" --kernel "$stage/Image.gz" \
	--ramdisk "$stage/gemini-simplefb-observation-restoration-initramfs.img" \
	--dtb "$ag_dtb" --output "$candidate" --name gemini-obs-L \
	--cmdline "$bootopt" --kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
	--tags-addr 0x44000000 --lk-android8 >"${candidate}.serializer"
python3 "$serializer" --kernel "$stage/Image.gz" \
	--ramdisk "$stage/gemini-simplefb-observation-restoration-initramfs.img" \
	--dtb "$replica_dtb" --output "$replica_boot" --name gemini-obs-L \
	--cmdline "$bootopt" --kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
	--tags-addr 0x44000000 --lk-android8 >"${replica_boot}.serializer"
cmp -s "$candidate" "$replica_boot" || die 'two Candidate AG constructions differ'
grep -v '^output=' "${candidate}.serializer" >"$stage/serializer.txt"
rm "${candidate}.serializer" "${replica_boot}.serializer"

python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/gemini-simplefb-observation-restoration-initramfs.img" \
	--expected-dtb "$ag_dtb" --expected-name gemini-obs-L \
	--expected-cmdline "$bootopt" "$candidate" >"$stage/analysis.raw"
sed -e "s|$workdir|@WORK@|g" -e "s|$repo_root|@REPOSITORY@|g" \
	"$stage/analysis.raw" >"$stage/analysis.txt"
rm "$stage/analysis.raw"
[[ "$(grep -c '^gate_' "$stage/analysis.txt")" == 32 ]] || \
	die 'LK analyzer did not emit 32 gates'

python3 "$boot_validator" --af-boot "$af_boot" --candidate "$candidate" \
	--image-gz "$stage/Image.gz" --af-dtb "$af_dtb" --ad-dtb "$ad_dtb" \
	--ag-dtb "$ag_dtb" \
	--initramfs "$stage/gemini-simplefb-observation-restoration-initramfs.img" \
	>"$stage/boot-validation.txt"

candidate_sha256="$(sha256sum "$candidate" | awk '{ print $1 }')"
candidate_size="$(wc -c <"$candidate" | tr -d ' ')"
dtb_sha256="$(sha256sum "$ag_dtb" | awk '{ print $1 }')"
[[ "$candidate_sha256" == 0552986c885d89fd65d05f3da8513040f756c9cfc84b1b30e1e085ee68238a91 ]] || \
	die 'Candidate AG raw Android-v0 identity differs from the reproduced artifact'
[[ "$candidate_size" == 7387136 ]] || \
	die 'Candidate AG raw Android-v0 size differs from the reproduced artifact'
[[ "$dtb_sha256" == 7ea5e8f9edb09f2365a112b29359fed897f306422a26449b1cb8870bb1212512 ]] || \
	die 'Candidate AG DTB identity differs from the reproduced artifact'
{
	printf 'experiment=2026-07-22-simplefb-observation-restoration\n'
	printf 'candidate_label=AG\n'
	printf 'candidate_sha256=%s\n' "$candidate_sha256"
	printf 'candidate_size=%s\n' "$candidate_size"
	printf 'candidate_dtb_sha256=%s\n' "$dtb_sha256"
	printf 'af_boot_sha256=fe43efa8c9d18174fec97ab7ad6cbe59bbc490df92366bcd254c55daa932d0a3\n'
	printf 'af_image_gz_sha256=b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912\n'
	printf 'af_config_sha256=bfd71f6618fab738d378530f73d1c75d73c69f19334b84d9c663aaa98740eb63\n'
	printf 'af_system_map_sha256=a0bf3087fb2225e17192606cb2150204ce89cfb51ea0719e4ce200800b1a407d\n'
	printf 'af_dtb_sha256=3f9e6d977ca1c8060ad4170bdca12eed3d40b112009b8ad93b4a08017221643b\n'
	printf 'ad_dtb_sha256=bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f\n'
	printf 'initramfs_sha256=166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3\n'
	printf 'kernel_config_system_map=byte-exact-candidate-af\n'
	printf 'initramfs_helpers_cmdline=byte-exact-candidate-af\n'
	printf 'patch_profile=byte-exact-candidate-af-no-kernel-build\n'
	printf 'dtb_delta=exact-ad-hardware-passed-simplefb-observation-path-only\n'
	printf 'chosen_parent_delta=address-cells+size-cells+empty-ranges\n'
	printf 'simplefb=0x7dfb0000+0x01f90000;1080x2160;stride4352;a8r8g8b8\n'
	printf 'simplefb_clocks=path-resolved-infracfg-45+topckgen-6\n'
	printf 'static_lk_framebuffer_reservation=absent\n'
	printf 'blacklisted_initcall=mt6797_a72_power_driver_init\n'
	printf 'cpu_policy=maxcpus-8-cpu8-cpu9-rejecting-method-retained\n'
	printf 'raw_framebuffer_beacon_plan=superseded-not-implemented\n'
	printf 'raw_framebuffer_write=none\n'
	printf 'storage_access=none\nwatchdog_userspace=none\n'
	printf 'artifact_builder_device_access=none\nflash=none\nruntime_result=not-tested\n'
} >"$stage/provenance.txt"

expected_inventory="$(printf '%s\n' Image.gz System.map analysis.txt \
	boot-validation.txt console-keymap-verify console-unicode-mode \
	dtb-validation.txt gemini-simplefb-observation-restoration.boot.img \
	gemini-simplefb-observation-restoration-initramfs.img gemini-us.bkeymap \
	input-event-capture kernel.config lineage-validation.txt \
	mt6797-gemini-pda-simplefb-observation-restoration.dtb provenance.txt \
	serializer.txt source-build.json | sort)"
actual_inventory="$(find "$stage" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)"
unexpected_entry="$(find "$stage" -mindepth 1 -maxdepth 1 ! -type f -print -quit)"
[[ -z "$unexpected_entry" && "$actual_inventory" == "$expected_inventory" ]] || \
	die 'Candidate AG output inventory changed'
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || \
	die 'Candidate AG manifest failed'
final_inventory="$(find "$stage" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)"
[[ "$final_inventory" == "$(printf '%s\n%s\n' "$expected_inventory" SHA256SUMS | sort)" ]] || \
	die 'Candidate AG manifest publication changed the inventory'
chmod 0600 "$stage"/*
chmod 0755 "$stage/console-keymap-verify" "$stage/console-unicode-mode" \
	"$stage/input-event-capture"

output_name="candidate-AG-simplefb-restoration-${candidate_sha256:0:8}"
artifact="$workdir/$output_name"
mv -n "$stage" "$artifact"
[[ -d "$artifact" && ! -e "$stage" ]] || die 'internal AG publication failed'
stage=
output="$output_parent/$output_name"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv -n "$artifact" "$output"
[[ -d "$output" && ! -e "$artifact" ]] || die 'exclusive AG publication failed'
workdir=
trap - EXIT
printf 'validation=candidate-ag-simplefb-observation-restoration\n'
printf 'artifact=%s\n' "$output"
printf 'candidate=%s/gemini-simplefb-observation-restoration.boot.img\n' "$output"
printf 'candidate_sha256=%s\ncandidate_size=%s\n' "$candidate_sha256" "$candidate_size"
printf 'dtb_sha256=%s\nruntime_result=not-tested\n' "$dtb_sha256"
