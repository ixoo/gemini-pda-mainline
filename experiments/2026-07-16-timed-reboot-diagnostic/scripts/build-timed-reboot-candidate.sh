#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() {
	echo "error: $*" >&2
	exit 2
}

usage() {
	cat >&2 <<'EOF'
usage: build-timed-reboot-candidate.sh --package DIR [--output DIR]
       [--source-date-epoch N]

Rebuild the exact tested USB baseline, then create a non-flashing Android v0
variant whose sole payload change is /init arming `busybox reboot -f` after 10
seconds. This command has no device, partition, or flashing interface.
EOF
}

package=
output=
source_date_epoch=${SOURCE_DATE_EPOCH:-0}
while (($#)); do
	case "$1" in
		--package)
			(($# >= 2)) || die "--package requires DIR"
			package=$2
			shift 2
			;;
		--output)
			(($# >= 2)) || die "--output requires DIR"
			output=$2
			shift 2
			;;
		--source-date-epoch)
			(($# >= 2)) || die "--source-date-epoch requires N"
			source_date_epoch=$2
			shift 2
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			usage
			die "unknown option: $1"
			;;
	esac
done

[[ "$(uname -s)" == Linux ]] || die "run inside the Linux development VM"
[[ "$(uname -m)" == aarch64 ]] || die "expected an aarch64 development VM"
[[ -n "$package" ]] || die "--package is required; implicit package selection is forbidden"
[[ -d "$package" ]] || die "package does not exist: $package"
[[ "$source_date_epoch" =~ ^[0-9]+$ ]] || die "epoch must be a non-negative integer"
for command in awk cmp cpio find git gzip jq patch python3 sha256sum sort; do
	command -v "$command" >/dev/null 2>&1 || die "required command not found: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
experiment_dir="$(cd -- "${script_dir}/.." && pwd -P)"
repo_root="$(cd -- "${experiment_dir}/../.." && pwd -P)"
package="$(cd -- "$package" && pwd -P)"
package_id="$(basename -- "$package")"
if [[ -z "$output" ]]; then
	output="${HOME}/artifacts/boot-candidates/${package_id}-timed-reboot-C"
fi
[[ ! -e "$output" ]] || die "refusing to overwrite $output"

baseline_builder="${repo_root}/experiments/2026-07-16-usb-gadget-diagnostic/scripts/build-usb-diagnostic-candidate.sh"
initramfs_builder="${script_dir}/build-initramfs.sh"
initramfs_delta_validator="${script_dir}/validate-initramfs-delta.sh"
boot_delta_validator="${script_dir}/validate-boot-delta.py"
serializer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/build-android-boot-v0.py"
analyzer="${repo_root}/experiments/2026-07-12-boot-contract-recovery/scripts/analyze-lk-boot-image.py"
candidate_builder="${script_dir}/build-timed-reboot-candidate.sh"
baseline_init_source="${repo_root}/experiments/2026-07-16-usb-gadget-diagnostic/initramfs/init"
reboot_patch="${experiment_dir}/initramfs/timed-reboot.patch"
usb_shell_source="${repo_root}/experiments/2026-07-16-usb-gadget-diagnostic/initramfs/usb-shell"
busybox=/usr/bin/busybox
for input in \
	"$baseline_builder" "$initramfs_builder" "$initramfs_delta_validator" \
	"$boot_delta_validator" "$serializer" "$analyzer" "$candidate_builder" \
	"$baseline_init_source" "$reboot_patch" "$usb_shell_source" "$busybox"; do
	[[ -s "$input" ]] || die "required input is missing: $input"
done

readonly EXPECTED_BASELINE_CANDIDATE_SHA256=41b97a83c53e76cc0fc117660dd4f7189b397f63ea5f6545fc00ef89af0263ca
readonly EXPECTED_BASELINE_INITRAMFS_SHA256=6468beafdec6343aa9ee61fc3e72fedf777162a13db8981eb9429babbd194e00
readonly EXPECTED_BASELINE_DTB_SHA256=5717a8c2f3f4f02533fae4dad8c9f9137f0f78cb0986fd6908a74309722e7db4

mkdir -p "$(dirname -- "$output")"
workdir="$(mktemp -d "$(dirname -- "$output")/.rebootdiag-work.XXXXXX")"
staging="$(mktemp -d "$(dirname -- "$output")/.rebootdiag-output.XXXXXX")"
cleanup() {
	[[ ! -d "$workdir" ]] || rm -rf "$workdir"
	[[ ! -d "$staging" ]] || rm -rf "$staging"
}
trap cleanup EXIT

normalize_log() {
	local log=$1
	local normalized="${log}.normalized"
	local value
	while IFS= read -r value || [[ -n "$value" ]]; do
		value=${value//"$workdir"/@WORK@}
		value=${value//"$staging"/@OUTPUT@}
		value=${value//"$package"/@PACKAGE@}
		value=${value//"$repo_root"/@REPOSITORY@}
		printf '%s\n' "$value"
	done <"$log" >"$normalized"
	mv "$normalized" "$log"
}

baseline_dir="${workdir}/baseline"
"$baseline_builder" --package "$package" --output "$baseline_dir" \
	--source-date-epoch "$source_date_epoch" >"${staging}/baseline-build.txt"
normalize_log "${staging}/baseline-build.txt"
(
	cd "$baseline_dir"
	sha256sum --check SHA256SUMS >/dev/null
)

baseline_candidate="${baseline_dir}/gemini-lk-usbdiag.boot.img"
baseline_initramfs="${baseline_dir}/gemini-lk-usbdiag-initramfs.img"
baseline_dtb="${baseline_dir}/mt6797-gemini-pda-lk-usbdiag.dtb"
[[ "$(sha256sum "$baseline_candidate" | awk '{print $1}')" == "$EXPECTED_BASELINE_CANDIDATE_SHA256" ]] || \
	die "rebuilt baseline candidate does not match the tested image"
[[ "$(sha256sum "$baseline_initramfs" | awk '{print $1}')" == "$EXPECTED_BASELINE_INITRAMFS_SHA256" ]] || \
	die "rebuilt baseline initramfs does not match the tested image"
[[ "$(sha256sum "$baseline_dtb" | awk '{print $1}')" == "$EXPECTED_BASELINE_DTB_SHA256" ]] || \
	die "rebuilt baseline DTB does not match the tested image"

timed_initramfs="${staging}/gemini-lk-rebootdiag-initramfs.img"
timed_candidate="${staging}/gemini-lk-rebootdiag.boot.img"
dtb="${staging}/mt6797-gemini-pda-lk-usbdiag.dtb"
install -m 0600 "$baseline_dtb" "$dtb"
"$initramfs_builder" --output "$timed_initramfs" --busybox "$busybox" \
	--source-date-epoch "$source_date_epoch" >"${staging}/initramfs-build.txt"
normalize_log "${staging}/initramfs-build.txt"
"$initramfs_delta_validator" --baseline "$baseline_initramfs" \
	--candidate "$timed_initramfs" >"${staging}/initramfs-delta.txt"
normalize_log "${staging}/initramfs-delta.txt"

image_gz="${package}/Image.gz"
bootopt='bootopt=64S3,32N2,64N2'
python3 "$serializer" \
	--kernel "$image_gz" \
	--ramdisk "$timed_initramfs" \
	--dtb "$dtb" \
	--output "$timed_candidate" \
	--name gemini-usbdiag \
	--cmdline "$bootopt" \
	--kernel-addr 0x40200000 \
	--ramdisk-addr 0x45000000 \
	--second-addr 0x40f00000 \
	--tags-addr 0x44000000 \
	--lk-android8 >"${staging}/serializer.txt"
normalize_log "${staging}/serializer.txt"
python3 "$analyzer" --validate-lk --expected-dtb "$dtb" "$timed_candidate" \
	>"${staging}/analysis.txt"
normalize_log "${staging}/analysis.txt"
python3 "$boot_delta_validator" \
	--baseline "$baseline_candidate" \
	--candidate "$timed_candidate" \
	--baseline-ramdisk "$baseline_initramfs" \
	--candidate-ramdisk "$timed_initramfs" \
	--expected-baseline-sha256 "$EXPECTED_BASELINE_CANDIDATE_SHA256" \
	>"${staging}/boot-delta.txt"
normalize_log "${staging}/boot-delta.txt"

install -m 0600 "${package}/provenance/build.json" "${staging}/source-build.json"
repo_revision="$(git -C "$repo_root" rev-parse HEAD)"
repo_status="$(git -C "$repo_root" status --porcelain=v1 --untracked-files=all)"
repo_status_sha256="$(printf '%s\n' "$repo_status" | sha256sum | awk '{print $1}')"
{
	printf 'experiment=2026-07-16-timed-reboot-diagnostic\n'
	printf 'package=%s\n' "$package_id"
	printf 'repo_revision=%s\n' "$repo_revision"
	printf 'repo_status_sha256=%s\n' "$repo_status_sha256"
	printf 'source_date_epoch=%s\n' "$source_date_epoch"
	printf 'single_runtime_delta=initramfs-/init\n'
	printf 'reboot_delay_seconds=10\n'
	printf 'reboot_invocation=/bin/busybox reboot -f\n'
	printf 'kernel_addr=0x40200000\nramdisk_addr=0x45000000\n'
	printf 'second_addr=0x40f00000\ntags_addr=0x44000000\n'
	printf 'header_name=gemini-usbdiag\nheader_cmdline=%s\n' "$bootopt"
	printf 'baseline_candidate_sha256=%s\n' "$EXPECTED_BASELINE_CANDIDATE_SHA256"
	printf 'baseline_initramfs_sha256=%s\n' "$EXPECTED_BASELINE_INITRAMFS_SHA256"
	printf 'baseline_dtb_sha256=%s\n' "$EXPECTED_BASELINE_DTB_SHA256"
	printf 'timed_initramfs_sha256=%s\n' "$(sha256sum "$timed_initramfs" | awk '{print $1}')"
	printf 'timed_candidate_sha256=%s\n' "$(sha256sum "$timed_candidate" | awk '{print $1}')"
	for input in \
		"$baseline_builder" "$initramfs_builder" "$initramfs_delta_validator" \
		"$boot_delta_validator" "$serializer" "$analyzer" "$candidate_builder" \
		"$baseline_init_source" "$reboot_patch" "$usb_shell_source" "$busybox"; do
		printf 'input_sha256[%s]=%s\n' \
			"${input#"$repo_root"/}" "$(sha256sum "$input" | awk '{print $1}')"
	done
	for tool in cpio gzip patch; do
		tool_path="$(command -v "$tool")"
		printf 'tool_sha256[%s]=%s\n' \
			"$tool" "$(sha256sum "$tool_path" | awk '{print $1}')"
	done
	printf 'storage_access=none\n'
	printf 'hardware_write=none\nflash=none\n'
	printf 'intended_runtime_action=forced-reboot-request\n'
	printf 'runtime_reboot_observed=not-tested\n'
	printf 'runtime_loop_risk=boot2-selection-may-persist-across-reset\n'
} >"${staging}/provenance.txt"

(
	cd "$staging"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"${staging}/SHA256SUMS"
(
	cd "$staging"
	sha256sum --check SHA256SUMS >/dev/null
)
chmod 0600 "${staging}"/*
mv "$staging" "$output"
staging=
rm -rf "$workdir"
workdir=
trap - EXIT

printf 'validation=timed-reboot-diagnostic-candidate\n'
printf 'package=%s\n' "$package_id"
printf 'output=%s\n' "$output"
printf 'candidate=%s/gemini-lk-rebootdiag.boot.img\n' "$output"
printf 'candidate_sha256=%s\n' "$(sha256sum "$output/gemini-lk-rebootdiag.boot.img" | awk '{print $1}')"
printf 'reboot_delay_seconds=10\n'
printf 'hardware_write=none\nflash=none\n'
printf 'intended_runtime_action=forced-reboot-request\n'
printf 'runtime_reboot_observed=not-tested\n'
