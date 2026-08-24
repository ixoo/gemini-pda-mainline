#!/usr/bin/env bash

# Add only the minimum platform-state provider contracts to the exact,
# runtime-proven Stage-27 serviceability DTB.
set -euo pipefail
export LC_ALL=C
umask 077

readonly SOURCE_SHA256=7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806
readonly OUTPUT_SHA256=57e11e4392edfdb9fa695ac3f87b82aad4043bc2a61b78646bf97344bae101fd
readonly OUTPUT_SIZE=27031
readonly OUTPUT_FILE=mt6797-gemini-pda-a72-platform-state-stage27-control.dtb

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --input-dtb FILE --output-parent DIR\n' "$0" >&2; }

input=
output_parent=
while (($#)); do
	case "$1" in
	--input-dtb) input=${2:-}; shift 2 ;;
	--output-parent) output_parent=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ -n "$input" && -n "$output_parent" ]] || { usage; exit 2; }
for command in awk chmod cmp cp dtc fdtget fdtput find mkdir mktemp mv rm \
	rmdir sha256sum sort tr wc xargs; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
input=$(cd -- "$(dirname -- "$input")" && pwd -P)/$(basename -- "$input")
output_parent=$(cd -- "$output_parent" && pwd -P)
case "$output_parent/" in "$repo_root/artifacts/"*) ;; *) die 'output must remain below artifacts' ;; esac
[[ -f "$input" && ! -L "$input" ]] || die 'input DTB is missing or unsafe'
[[ "$(sha256sum "$input" | awk '{print $1}')" == "$SOURCE_SHA256" ]] || die 'Stage-27 source DTB changed'

workdir=$(mktemp -d "$output_parent/.a72-platform-state-stage27.XXXXXXXX")
cleanup() { [[ ! -d "${workdir:-}" ]] || rm -rf -- "$workdir"; }
trap cleanup EXIT HUP INT TERM
mkdir "$workdir/first" "$workdir/second"

derive() {
	local source=$1 output=$2
	cp "$source" "$output"
	fdtput -t s "$output" /power-controller@10006000 compatible \
		mediatek,mt6797-scpsys syscon
	fdtput -t x "$output" /watchdog@10007000 '#reset-cells' 1
	fdtput -t x "$output" /watchdog@10007000 phandle 2e
	fdtput -c "$output" /a72-platform-state@10222000
	fdtput -t s "$output" /a72-platform-state@10222000 compatible \
		mediatek,mt6797-a72-platform-state
	fdtput -t x "$output" /a72-platform-state@10222000 reg \
		0 10222000 0 1000 0 10390000 0 10000
	fdtput -t s "$output" /a72-platform-state@10222000 reg-names mcucfg cci
	fdtput -t x "$output" /a72-platform-state@10222000 mediatek,spm b
	fdtput -t x "$output" /a72-platform-state@10222000 resets 2e b
	fdtput -t s "$output" /a72-platform-state@10222000 reset-names pwrap
	fdtput -t s "$output" /a72-platform-state@10222000 status okay
}

for root in "$workdir/first" "$workdir/second"; do
	derive "$input" "$root/$OUTPUT_FILE"
done
cmp -s "$workdir/first/$OUTPUT_FILE" "$workdir/second/$OUTPUT_FILE" ||
	die 'independent DT derivations differ'

dtb="$workdir/first/$OUTPUT_FILE"
[[ "$(sha256sum "$dtb" | awk '{print $1}')" == "$OUTPUT_SHA256" ]] || die 'derived DTB identity changed'
[[ "$(wc -c <"$dtb" | tr -d ' ')" == "$OUTPUT_SIZE" ]] || die 'derived DTB size changed'

[[ "$(fdtget -t s "$dtb" /power-controller@10006000 compatible | tr ' ' '\n' | sort | tr '\n' ' ')" == \
	'mediatek,mt6797-scpsys syscon ' ]] || die 'SPM syscon contract changed'
[[ "$(fdtget -t x "$dtb" /watchdog@10007000 '#reset-cells')" == 1 ]] || die 'watchdog reset cells changed'
[[ "$(fdtget -t x "$dtb" /watchdog@10007000 phandle)" == 2e ]] || die 'watchdog phandle changed'
[[ "$(fdtget -t s "$dtb" /a72-platform-state@10222000 compatible)" == \
	mediatek,mt6797-a72-platform-state ]] || die 'platform-state compatible changed'
[[ "$(fdtget -t s "$dtb" /a72-platform-state@10222000 status)" == okay ]] || die 'platform-state source is not enabled'
[[ "$(fdtget -t x "$dtb" /a72-platform-state@10222000 reg)" == \
	'0 10222000 0 1000 0 10390000 0 10000' ]] || die 'platform-state register resources changed'
[[ "$(fdtget -t x "$dtb" /a72-platform-state@10222000 mediatek,spm)" == b ]] || die 'SPM phandle changed'
[[ "$(fdtget -t x "$dtb" /a72-platform-state@10222000 resets)" == '2e b' ]] || die 'reset contract changed'

for node in /usb@11271000 /t-phy@11290000 /t-phy@11290000/usb-phy@11290800 \
	/i2c@1101c000 /i2c@1101c000/gpio-expander@5b /keyboard-matrix; do
	[[ "$(fdtget -t s "$dtb" "$node" status)" == okay ]] || die "Stage-27 serviceability node changed: $node"
done
[[ "$(fdtget -t s "$dtb" /chosen/framebuffer@7dfb0000 compatible)" == simple-framebuffer ]] ||
	die 'Stage-27 framebuffer disappeared'
[[ "$(fdtget -t s "$dtb" /scp@10020000 status)" == disabled ]] || die 'Stage-27 SCP state changed'

# Reverse the three contract additions and prove that the complete sorted
# semantic tree returns to the exact Stage-27 source tree.
cp "$dtb" "$workdir/reverted.dtb"
fdtput -r "$workdir/reverted.dtb" /a72-platform-state@10222000
fdtput -t s "$workdir/reverted.dtb" /power-controller@10006000 compatible mediatek,mt6797-scpsys
fdtput -d "$workdir/reverted.dtb" /watchdog@10007000 '#reset-cells'
fdtput -d "$workdir/reverted.dtb" /watchdog@10007000 phandle
dtc -q -s -I dtb -O dts -o "$workdir/source.sorted.dts" "$input"
dtc -q -s -I dtb -O dts -o "$workdir/reverted.sorted.dts" "$workdir/reverted.dtb"
cmp -s "$workdir/source.sorted.dts" "$workdir/reverted.sorted.dts" ||
	die 'reversing the provider contracts does not recover the Stage-27 semantic tree'

{
	printf 'experiment=2026-08-24-mainline-a72-platform-state-stage27-control\n'
	printf 'source_dtb_sha256=%s\nderived_dtb_sha256=%s\n' "$SOURCE_SHA256" "$OUTPUT_SHA256"
	printf 'semantic_baseline_after_reverse=byte-identical-sorted-dts\n'
	printf 'changed_contracts=3\nplatform_state=okay\nspm_syscon=added\nwatchdog_reset_provider=added\n'
	printf 'usb_tphy_i2c5_keyboard_framebuffer_scp=exact-stage27-state\n'
	printf 'register_data_writes=0\nprotected_calls=0\ncpu_requests=0\nresult=pass\n'
} >"$workdir/first/provenance.txt"
(
	cd "$workdir/first"
	find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum
) >"$workdir/first/SHA256SUMS"
(
	cd "$workdir/first"
	sha256sum --check --strict SHA256SUMS >/dev/null
)
chmod 0600 "$workdir/first"/*
output="$output_parent/dtb-a72-platform-state-stage27-${OUTPUT_SHA256:0:8}"
[[ ! -e "$output" && ! -L "$output" ]] || die "refusing to overwrite $output"
mv "$workdir/first" "$output"
rm -rf -- "$workdir/second"
rm -f -- "$workdir/reverted.dtb" "$workdir/source.sorted.dts" "$workdir/reverted.sorted.dts"
rmdir "$workdir"
workdir=
trap - EXIT HUP INT TERM
printf 'validation=a72-platform-state-stage27-dtb\nartifact=%s\ndtb_sha256=%s\n' "$output" "$OUTPUT_SHA256"
printf 'device_access=none\nhardware_write=none\n'
