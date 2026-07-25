#!/usr/bin/env bash
# Assemble Candidate AQ from the exact hardware-passed Candidate AO lineage.
set -euo pipefail
export LC_ALL=C
export PYTHONDONTWRITEBYTECODE=1
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || die 'run in the recovery VM'
[[ $# -eq 3 ]] || die 'usage: build-candidate-aq.sh PACKAGE AO_ARTIFACT OUTPUT_PARENT'
package=$(cd -- "$1" && pwd -P)
ao=$(cd -- "$2" && pwd -P)
output_parent=$(cd -- "$3" && pwd -P)
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
for command in awk basename chmod cmp find grep install jq mkdir mktemp mv python3 rm sha256sum sort tr wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ "$(basename "$ao")" == candidate-AO-mt6797-dvfsp-handoff-owner-44fc1e6a ]] || die 'wrong AO artifact'
[[ -f "$package/SHA256SUMS" && -f "$package/Image.gz" && -f "$package/System.map" && -f "$package/kernel.config" ]] || die 'incomplete package'
(cd "$package" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'package manifest failed'
profile=$(jq -r .build_profile "$package/provenance/build.json")
[[ "$profile" == observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-owner-ap-dma-observer ]] || die 'wrong package profile'
grep -Fqx 'CONFIG_DEBUG_FS=y' "$package/kernel.config" || die 'CONFIG_DEBUG_FS was not retained'
[[ "$(sha256sum "$ao/SHA256SUMS" | awk '{print $1}')" == \
	6e8eb261d0a59807d20a605626c3ef8aff5799ac4f61494f77d6210be15acf85 ]] || die 'AO manifest changed'
[[ "$(sha256sum "$ao/mt6797-gemini-pda-dvfsp-handoff-owner.dtb" | awk '{print $1}')" == \
	de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7 ]] || die 'AO DT changed'
[[ "$(sha256sum "$ao/gemini-dvfsp-handoff-owner-initramfs.img" | awk '{print $1}')" == \
	166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3 ]] || die 'AO initramfs changed'
serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
[[ "$(sha256sum "$serializer" | awk '{print $1}')" == 569ca6f2b365f119c8c3668cb3d63724b29e76447e47638d707983ee8eafadf4 ]] || die 'serializer changed'
[[ "$(sha256sum "$analyzer" | awk '{print $1}')" == aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95 ]] || die 'LK analyzer changed'
work=$(mktemp -d "$output_parent/.candidate-aq.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
stage="$work/stage"
replica="$work/replica"
mkdir "$stage" "$replica"
install -m 0600 "$package/Image.gz" "$stage/Image.gz"
install -m 0600 "$package/System.map" "$stage/System.map"
install -m 0600 "$package/kernel.config" "$stage/kernel.config"
install -m 0600 "$package/provenance/build.json" "$stage/source-build.json"
cp "$stage/Image.gz" "$replica/Image.gz"
cp "$stage/System.map" "$replica/System.map"
install -m 0600 "$ao/mt6797-gemini-pda-dvfsp-handoff-owner.dtb" \
	"$stage/mt6797-gemini-pda-ap-dma-owner-observer.dtb"
install -m 0600 "$ao/gemini-us.bkeymap" "$stage/gemini-us.bkeymap"
install -m 0755 "$ao/console-unicode-mode" "$stage/console-unicode-mode"
install -m 0755 "$ao/console-keymap-verify" "$stage/console-keymap-verify"
install -m 0755 "$ao/input-event-capture" "$stage/input-event-capture"
"$script_dir/build-initramfs.sh" \
	"$ao/gemini-dvfsp-handoff-owner-initramfs.img" \
	"$stage/gemini-ap-dma-owner-observer-initramfs.img" \
	"$script_dir/../initramfs" >/dev/null
cp "$stage/mt6797-gemini-pda-ap-dma-owner-observer.dtb" \
	"$replica/mt6797-gemini-pda-ap-dma-owner-observer.dtb"
cp "$stage/gemini-ap-dma-owner-observer-initramfs.img" \
	"$replica/gemini-ap-dma-owner-observer-initramfs.img"
boot="$stage/gemini-mt6797-dvfsp-ap-dma-owner-observer.boot.img"
replica_boot="$replica/gemini-mt6797-dvfsp-ap-dma-owner-observer.boot.img"
python3 "$serializer" --kernel "$stage/Image.gz" \
	--ramdisk "$stage/gemini-ap-dma-owner-observer-initramfs.img" \
	--dtb "$stage/mt6797-gemini-pda-ap-dma-owner-observer.dtb" \
	--output "$boot" --name gemini-obs-L --cmdline bootopt=64S3,32N2,64N2 \
	--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 >/dev/null
python3 "$serializer" --kernel "$replica/Image.gz" \
	--ramdisk "$replica/gemini-ap-dma-owner-observer-initramfs.img" \
	--dtb "$replica/mt6797-gemini-pda-ap-dma-owner-observer.dtb" \
	--output "$replica_boot" --name gemini-obs-L --cmdline bootopt=64S3,32N2,64N2 \
	--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 --tags-addr 0x44000000 --lk-android8 >/dev/null
cmp -s "$boot" "$replica_boot" || die 'two boot assemblies differ'
python3 "$analyzer" --validate-lk --expected-image-gz "$stage/Image.gz" \
	--expected-ramdisk "$stage/gemini-ap-dma-owner-observer-initramfs.img" \
	--expected-dtb "$stage/mt6797-gemini-pda-ap-dma-owner-observer.dtb" \
	--expected-name gemini-obs-L --expected-cmdline bootopt=64S3,32N2,64N2 "$boot" \
	>"$stage/analysis.txt"
grep -q '^gate_' "$stage/analysis.txt" || die 'LK analyzer emitted no gates'
candidate_sha=$(sha256sum "$boot" | awk '{print $1}')
candidate_size=$(wc -c <"$boot" | tr -d ' ')
dtb_sha=$(sha256sum "$stage/mt6797-gemini-pda-ap-dma-owner-observer.dtb" | awk '{print $1}')
init_sha=$(sha256sum "$stage/gemini-ap-dma-owner-observer-initramfs.img" | awk '{print $1}')
img_sha=$(sha256sum "$stage/Image.gz" | awk '{print $1}')
map_sha=$(sha256sum "$stage/System.map" | awk '{print $1}')
cfg_sha=$(sha256sum "$stage/kernel.config" | awk '{print $1}')
build_sha=$(sha256sum "$stage/source-build.json" | awk '{print $1}')
{
	printf 'experiment=2026-07-24-mt6797-ap-dma-owner-observer\ncandidate_label=AQ\n'
	printf 'kernel_profile=%s\ncandidate_sha256=%s\ncandidate_size=%s\n' "$profile" "$candidate_sha" "$candidate_size"
	printf 'candidate_image_gz_sha256=%s\ncandidate_system_map_sha256=%s\n' "$img_sha" "$map_sha"
	printf 'candidate_config_sha256=%s\ncandidate_source_build_sha256=%s\n' "$cfg_sha" "$build_sha"
	printf 'candidate_dtb_sha256=%s\ncandidate_initramfs_sha256=%s\n' "$dtb_sha" "$init_sha"
	printf 'ao_padded_sha256=3e3a4450d5541e4ad80eceb83e3903981dd1613e05fecd7b25cd2720aadc3edb\nap_padded_sha256=602f06be094c6091ceff9b501bf5328bc2f79d26be5c26f98479905aa3caa5f9\n'
	printf 'i2c6=disabled\nda9214_node=absent\na72_power_node=absent\n'
	printf 'debugfs=CONFIG_DEBUG_FS_and_read_only_initramfs_mount\nclock_observation=early_and_5_second_late_clk_summary\n'
	printf 'hardware_mutation=none\nstorage_access=none\nwatchdog_userspace=none\nautomatic_reboot=none\nruntime_result=not-tested\n'
} >"$stage/provenance.txt"
expected='Image.gz System.map analysis.txt console-keymap-verify console-unicode-mode gemini-ap-dma-owner-observer-initramfs.img gemini-mt6797-dvfsp-ap-dma-owner-observer.boot.img gemini-us.bkeymap input-event-capture kernel.config mt6797-gemini-pda-ap-dma-owner-observer.dtb provenance.txt source-build.json'
actual=$(find "$stage" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort | tr '\n' ' ' | sed 's/ $//')
expected=$(printf '%s\n' $expected | sort | tr '\n' ' ' | sed 's/ $//')
[[ "$actual" == "$expected" ]] || die 'artifact inventory changed'
(
	cd "$stage"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$stage/SHA256SUMS"
(cd "$stage" && sha256sum --check --strict SHA256SUMS >/dev/null) || die 'artifact manifest failed'
chmod 0600 "$stage"/*
chmod 0755 "$stage/console-keymap-verify" "$stage/console-unicode-mode" "$stage/input-event-capture"
out="$output_parent/candidate-AQ-mt6797-ap-dma-owner-observer-${candidate_sha:0:8}"
[[ ! -e "$out" && ! -L "$out" ]] || die 'refusing to overwrite artifact'
mv "$stage" "$out"
printf 'artifact=%s\ncandidate=%s/%s\ncandidate_sha256=%s\ncandidate_size=%s\ndtb_sha256=%s\n' \
	"$out" "$out" "$(basename "$boot")" "$candidate_sha" "$candidate_size" "$dtb_sha"
