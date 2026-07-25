#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --package DIR --baseline DIR [--output DIR]\n' "$0" >&2
}

package=
baseline=
output=
while (($#)); do
	case "$1" in
		--package) package=$2; shift 2 ;;
		--baseline) baseline=$2; shift 2 ;;
		--output) output=$2; shift 2 ;;
		*) usage; die "unknown option: $1" ;;
	esac
done
[[ "$(uname -s)" == Linux && "$(uname -m)" == aarch64 ]] || \
	die "run inside the AArch64 Linux development VM"
[[ -d "$package" && -d "$baseline" ]] || die "package and Candidate P baseline are required"

readonly P_BOOT_SHA256=d192dac9e4516eac9319da2a885abaf3203da6c357c574e7f1f6deef2208d341
readonly P_DTB_SHA256=c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379
readonly P_INITRAMFS_SHA256=3f19afd81632fbe654c024b9f865180b42caf61163bb26ea26211884271a11d8
readonly BOOT2_CAPACITY=16777216
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "${script_dir}/../../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
baseline="$(cd -- "$baseline" && pwd -P)"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
if [[ -z "$output" ]]; then
	output="${HOME}/artifacts/boot-candidates/candidate-Q-keyboard-shell-${repo_revision:0:8}"
fi
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
mkdir -p "$(dirname -- "$output")"

p_boot="$baseline/gemini-fbcon-rotation.boot.img"
p_dtb="$baseline/mt6797-gemini-pda-fbcon-rotation.dtb"
p_initramfs="$baseline/gemini-fbcon-rotation-initramfs.img"
for input in "$p_boot" "$p_dtb" "$p_initramfs" "$package/Image.gz" \
	"$package/kernel.config" "$package/dtbs/mediatek/mt6797-gemini-pda.dtb" \
	"$package/provenance/build.json"; do
	[[ -s "$input" ]] || die "required input missing: $input"
done
[[ "$(sha256sum "$p_boot" | awk '{print $1}')" == "$P_BOOT_SHA256" ]] || die "baseline boot is not P"
[[ "$(sha256sum "$p_dtb" | awk '{print $1}')" == "$P_DTB_SHA256" ]] || die "baseline DTB is not P"
[[ "$(sha256sum "$p_initramfs" | awk '{print $1}')" == "$P_INITRAMFS_SHA256" ]] || die "baseline initramfs is not P"

build_json="$package/provenance/build.json"
[[ "$(jq -r .build_profile "$build_json")" == observability-fbcon-rotation-keyboard ]] || \
	die "package profile is not Candidate Q"
[[ "$(jq -r .modules_built "$build_json")" == false ]] || die "modules were built"
config="$package/kernel.config"
required=(
	'CONFIG_I2C=y' 'CONFIG_I2C_MT65XX=y' 'CONFIG_PINCTRL_AW9523=y'
	'CONFIG_KEYBOARD_MATRIX=y' 'CONFIG_INPUT=y' 'CONFIG_INPUT_EVDEV=y'
	'CONFIG_INPUT_KEYBOARD=y' 'CONFIG_INPUT_MATRIXKMAP=y' 'CONFIG_GPIOLIB=y'
	'CONFIG_GPIOLIB_IRQCHIP=y' 'CONFIG_EINT_MTK=y' 'CONFIG_PINCTRL_MT6797=y'
	'CONFIG_REGMAP_I2C=y' 'CONFIG_TTY=y' 'CONFIG_VT=y' 'CONFIG_VT_CONSOLE=y'
	'CONFIG_CMDLINE_FORCE=y' 'CONFIG_FRAMEBUFFER_CONSOLE_ROTATION=y'
	'CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y' 'CONFIG_WATCHDOG_OPEN_TIMEOUT=0'
	'# CONFIG_MODULES is not set' '# CONFIG_I2C_CHARDEV is not set'
	'# CONFIG_DEVMEM is not set' '# CONFIG_MMC is not set'
)
for line in "${required[@]}"; do grep -Fxq "$line" "$config" || die "resolved config missing: $line"; done
cmdline="$(grep '^CONFIG_CMDLINE=' "$config")"
for token in 'maxcpus=1' 'panic=0' 'clk_ignore_unused' 'fbcon=rotate:3' 'consoleblank=0'; do
	case " $cmdline " in *" $token"*) ;; *) die "forced command line missing $token" ;; esac
done
for forbidden in 'CONFIG_MMC=y' 'CONFIG_KEXEC=y' 'CONFIG_DEVMEM=y' 'CONFIG_I2C_CHARDEV=y'; do
	! grep -Fxq "$forbidden" "$config" || die "forbidden config enabled: $forbidden"
done

staging="$(mktemp -d "$(dirname -- "$output")/.candidate-Q.XXXXXX")"
trap 'rm -rf "$staging"' EXIT
helper="$staging/input-event-capture"
dtb="$staging/mt6797-gemini-pda-keyboard-shell.dtb"
initramfs="$staging/gemini-keyboard-shell-initramfs.img"
boot="$staging/gemini-keyboard-shell.boot.img"
"$script_dir/build-input-event-capture.sh" "$helper" >"$staging/helper-build.txt"
"$script_dir/build-keyboard-dtb.sh" \
	"$package/dtbs/mediatek/mt6797-gemini-pda.dtb" "$dtb" >"$staging/dtb-build.txt"
"$script_dir/build-initramfs.sh" --baseline "$p_initramfs" --helper "$helper" \
	--output "$initramfs" >"$staging/initramfs-build.txt"

serializer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="$repo_root/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
bootopt='bootopt=64S3,32N2,64N2'
python3 "$serializer" --kernel "$package/Image.gz" --ramdisk "$initramfs" \
	--dtb "$dtb" --output "$boot" --name gemini-obs-L --cmdline "$bootopt" \
	--kernel-addr 0x40200000 --ramdisk-addr 0x45000000 --second-addr 0x40f00000 \
	--tags-addr 0x44000000 --lk-android8 >"$staging/serializer.txt"
python3 "$analyzer" --validate-lk --expected-image-gz "$package/Image.gz" \
	--expected-ramdisk "$initramfs" --expected-dtb "$dtb" \
	--expected-name gemini-obs-L --expected-cmdline "$bootopt" "$boot" \
	>"$staging/analysis.txt"
size="$(wc -c <"$boot")"
[[ "$size" -le "$BOOT2_CAPACITY" ]] || die "Candidate Q exceeds boot2 capacity"

install -m 0600 "$build_json" "$staging/source-build.json"
{
	printf 'experiment=2026-07-18-keyboard-shell-diagnostic\n'
	printf 'candidate_label=Q\nrepo_revision=%s\n' "$repo_revision"
	printf 'repo_status_sha256=%s\n' "$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all | sha256sum | awk '{print $1}')"
	printf 'baseline_candidate_sha256=%s\n' "$P_BOOT_SHA256"
	printf 'package=%s\n' "$(basename -- "$package")"
	printf 'candidate_size=%s\ncandidate_sha256=%s\n' "$size" "$(sha256sum "$boot" | awk '{print $1}')"
	printf 'candidate_image_gz_sha256=%s\n' "$(sha256sum "$package/Image.gz" | awk '{print $1}')"
	printf 'candidate_config_sha256=%s\n' "$(sha256sum "$config" | awk '{print $1}')"
	printf 'candidate_dtb_sha256=%s\n' "$(sha256sum "$dtb" | awk '{print $1}')"
	printf 'candidate_initramfs_sha256=%s\n' "$(sha256sum "$initramfs" | awk '{print $1}')"
	printf 'input_helper_sha256=%s\n' "$(sha256sum "$helper" | awk '{print $1}')"
	printf 'header_name=gemini-obs-L\nheader_cmdline=%s\n' "$bootopt"
	printf 'kernel_addr=0x40200000\nramdisk_addr=0x45000000\nsecond_addr=0x40f00000\ntags_addr=0x44000000\n'
	printf 'marker=GEMINI_KEYBOARD_SHELL_20260718_Q\n'
	printf 'enabled_dtb_nodes=/i2c@1101c000,/i2c@1101c000/gpio-expander@5b,/keyboard-matrix\n'
	printf 'event_window_seconds=60\nconsoleblank=0\nautomatic_reboot=no\nstorage_access=none\nruntime_networking=none\n'
	printf 'build_hardware_write=none\nflash=none\nruntime_result=not-tested\n'
} >"$staging/provenance.txt"
rm "$helper"
(
	cd "$staging"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$staging/SHA256SUMS"
(cd "$staging" && sha256sum --check SHA256SUMS >/dev/null)
chmod 0600 "$staging"/*
mv "$staging" "$output"
trap - EXIT
printf 'validation=compiled-keyboard-shell-candidate\ncandidate_label=Q\noutput=%s\n' "$output"
printf 'candidate=%s/gemini-keyboard-shell.boot.img\ncandidate_sha256=%s\n' \
	"$output" "$(sha256sum "$output/gemini-keyboard-shell.boot.img" | awk '{print $1}')"
printf 'build_hardware_write=none\nflash=none\nruntime_result=not-tested\n'
