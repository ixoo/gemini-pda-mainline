#!/usr/bin/env bash

# Derive the exact read-only provider DT from the package-built Gemini DT.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'Usage: %s --base-dtb FILE --output FILE\n' "$0"; }

base_dtb=
output=
while (($#)); do
	case "$1" in
	--base-dtb) base_dtb=${2:-}; shift 2 ;;
	--output) output=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$base_dtb" && -n "$output" ]] || { usage >&2; exit 2; }
for command in awk chmod dirname dtc fdtget fdtput install mkdir mktemp mv rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -f "$base_dtb" && ! -L "$base_dtb" && -s "$base_dtb" ]] ||
	die 'base DTB is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output'
mkdir -p -- "$(dirname -- "$output")"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
serviceability_builder="$repo_root/experiments/2026-08-17-mainline-i2c5-serviceability-restoration/scripts/build-serviceability-dtb.sh"
readonly SERVICEABILITY_BUILDER_SHA256=b63913108ab329915e505c6fbee54b6c85338dcb80252dbee9b9731142ee9503
readonly BASE_DTB_SHA256=380205e0546c1b87f4ce6b4c34fcd734a22dc42e3b1c3145044d396a16e00709
readonly OUTPUT_DTB_SHA256=d7dba05efa272c8264c8ea15c776fb88c21a0012603214b49dfd9e2893e87d48
readonly PINCTRL=/pinctrl@10005000
readonly I2C5=/i2c@1101c000
readonly AW9523=/i2c@1101c000/gpio-expander@5b
readonly KEYBOARD=/keyboard-matrix
readonly SCP=/scp@10020000
readonly WDT=/watchdog@10007000
readonly TPHY=/t-phy@11290000
readonly U2PORT0=/t-phy@11290000/usb-phy@11290800
readonly SSUSB=/usb@11271000
readonly XHCI=/usb@11271000/usb@11270000
readonly I2C6=/i2c@1100e000
readonly DA921X=/i2c@1100e000/regulator@68
readonly HANDOFF=/dvfsp-handoff@11015000
readonly DEVINFO=/firmware/atag-devinfo

[[ -f "$serviceability_builder" && ! -L "$serviceability_builder" ]] ||
	die 'serviceability reference builder is unsafe'
[[ "$(sha256sum "$serviceability_builder" | awk '{print $1}')" == \
	"$SERVICEABILITY_BUILDER_SHA256" ]] || die 'serviceability reference builder changed'
[[ "$(sha256sum "$base_dtb" | awk '{print $1}')" == "$BASE_DTB_SHA256" ]] ||
	die 'package DTB identity changed'

require_absent() {
	if fdtget "$1" "$2" "$3" >/dev/null 2>&1; then
		die "property must be absent: $2/$3"
	fi
}

validate_cpu_clocks() {
	local dtb=$1 node expected
	while read -r node expected; do
		[[ "$(fdtget -tu "$dtb" "/cpus/$node" clock-frequency)" == "$expected" ]] ||
			die "CPU clock changed: $node"
	done <<'EOF'
cpu@0 1391000000
cpu@1 1391000000
cpu@2 1391000000
cpu@3 1391000000
cpu@100 1950000000
cpu@101 1950000000
cpu@102 1950000000
cpu@103 1950000000
cpu@200 2288000000
cpu@201 2288000000
EOF
}

validate_provider() {
	local dtb=$1 handoff_phandle
	[[ "$(fdtget -ts "$dtb" "$I2C6" status)" == okay ]] || die 'I2C6 is not enabled'
	handoff_phandle="$(fdtget -tx "$dtb" "$HANDOFF" phandle)"
	[[ "$(fdtget -tx "$dtb" "$I2C6" access-controllers)" == "$handoff_phandle" ]] ||
		die 'I2C6 access-controller changed'
	[[ "$(fdtget -ts "$dtb" "$DA921X" compatible)" == dlg,da9214-legacy ]] ||
		die 'DA921x identity changed'
	[[ "$(fdtget -tx "$dtb" "$DA921X" reg)" == '68 69' ]] ||
		die 'DA921x direct addresses changed'
	[[ -z "$(fdtget -l "$dtb" "$DA921X")" ]] || die 'DA921x gained a consumer child'
	fdtget "$dtb" "$DEVINFO" read-only >/dev/null || die 'LK devinfo is not read-only'
	[[ "$(fdtget -tx "$dtb" "$DEVINFO/ptp-calibration-data@c" reg)" == 'c 4c' ]] ||
		die 'PTP handoff cell changed'
	[[ "$(fdtget -tx "$dtb" "$DEVINFO/cpu-efuse-identity@58" reg)" == '58 c' ]] ||
		die 'CPU identity handoff cell changed'
	[[ "$(fdtget -ts "$dtb" "$HANDOFF" status)" == okay ]] || die 'handoff is not enabled'
	[[ "$(fdtget -ts "$dtb" "$HANDOFF" nvmem-cell-names)" == \
		'ptp-calibration-data cpu-efuse-identity' ]] || die 'handoff NVMEM names changed'
}

validate_cpu_clocks "$base_dtb"
validate_provider "$base_dtb"
for node_path in "$TPHY" "$U2PORT0" "$SSUSB"; do
	[[ "$(fdtget -ts "$base_dtb" "$node_path" status)" == disabled ]] ||
		die "base USB node is not disabled: $node_path"
done
[[ "$(fdtget -ts "$base_dtb" "$XHCI" status)" == disabled ]] || die 'xHCI changed'
[[ "$(fdtget -ts "$base_dtb" "$I2C5" status)" == disabled ]] || die 'I2C5 changed'
[[ "$(fdtget -ts "$base_dtb" "$AW9523" status)" == disabled ]] || die 'AW9523 changed'
[[ "$(fdtget -ts "$base_dtb" "$KEYBOARD" status)" == disabled ]] || die 'keyboard changed'
[[ "$(fdtget -tx "$base_dtb" "$WDT" interrupts)" == '0 89 2' ]] || die 'watchdog IRQ changed'
if fdtget "$base_dtb" "$SCP" compatible >/dev/null 2>&1; then
	die 'base unexpectedly contains the LK SCP input node'
fi

temporary="$(mktemp "$(dirname -- "$output")/.da921x-lkro-provider-dtb.XXXXXXXX")"
cleanup() { [[ ! -e "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT HUP INT TERM
install -m 0600 "$base_dtb" "$temporary"

for node_path in "$TPHY" "$U2PORT0" "$SSUSB"; do
	fdtput -ts "$temporary" "$node_path" status okay
done
fdtput -c "$temporary" "$SCP"
fdtput -ts "$temporary" "$SCP" compatible mediatek,scp
fdtput -tx "$temporary" "$SCP" reg \
	0 10020000 0 80000 0 100a0000 0 1000 0 100a4000 0 1000
fdtput -tx "$temporary" "$SCP" interrupts 0 c7 4
fdtput -ts "$temporary" "$SCP" status disabled
fdtput -d "$temporary" "$WDT" interrupts

i2c5_phandle="$(fdtget -tx "$temporary" "$PINCTRL/i2c5-pins" phandle)"
fdtput -ts "$temporary" "$I2C5" status okay
fdtput -tx "$temporary" "$I2C5" clock-frequency 61a80
fdtput -ts "$temporary" "$I2C5" pinctrl-names default
fdtput -tx "$temporary" "$I2C5" pinctrl-0 "$i2c5_phandle"
fdtput -ts "$temporary" "$AW9523" status okay
for property in interrupt-parent interrupts interrupt-controller '#interrupt-cells'; do
	fdtput -d "$temporary" "$AW9523" "$property"
done
fdtput -ts "$temporary" "$KEYBOARD" status okay
fdtput -tx "$temporary" "$KEYBOARD" poll-interval 14
fdtput -tx "$temporary" "$KEYBOARD" col-scan-delay-us 2

dtc -q -I dtb -O dtb -o /dev/null "$temporary"
validate_cpu_clocks "$temporary"
validate_provider "$temporary"
for node_path in "$TPHY" "$U2PORT0" "$SSUSB"; do
	[[ "$(fdtget -ts "$temporary" "$node_path" status)" == okay ]] ||
		die "USB node is not enabled: $node_path"
done
[[ "$(fdtget -ts "$temporary" "$SSUSB" dr_mode)" == peripheral ]] || die 'USB role changed'
[[ "$(fdtget -ts "$temporary" "$SSUSB" maximum-speed)" == high-speed ]] ||
	die 'USB speed changed'
[[ "$(fdtget -ts "$temporary" "$XHCI" status)" == disabled ]] || die 'xHCI closure changed'
[[ "$(fdtget -ts "$temporary" "$SCP" status)" == disabled ]] || die 'SCP closure changed'
require_absent "$temporary" "$WDT" interrupts
[[ "$(fdtget -ts "$temporary" "$I2C5" status)" == okay ]] || die 'I2C5 is not enabled'
[[ "$(fdtget -tx "$temporary" "$I2C5" clock-frequency)" == 61a80 ]] ||
	die 'I2C5 frequency changed'
[[ "$(fdtget -ts "$temporary" "$AW9523" status)" == okay ]] || die 'AW9523 is not enabled'
for property in interrupt-parent interrupts interrupt-controller '#interrupt-cells'; do
	require_absent "$temporary" "$AW9523" "$property"
done
[[ "$(fdtget -ts "$temporary" "$KEYBOARD" status)" == okay ]] || die 'keyboard is not enabled'
[[ "$(fdtget -tx "$temporary" "$KEYBOARD" poll-interval)" == 14 ]] ||
	die 'keyboard polling changed'
[[ "$(fdtget -tx "$temporary" "$KEYBOARD" col-scan-delay-us)" == 2 ]] ||
	die 'keyboard scan delay changed'
[[ "$(sha256sum "$temporary" | awk '{print $1}')" == "$OUTPUT_DTB_SHA256" ]] ||
	die 'derived provider DT identity changed'

mv "$temporary" "$output"
chmod 0600 "$output"
temporary=
trap - EXIT HUP INT TERM
printf 'validation=mainline-da921x-readonly-provider-dtb\n'
printf 'base_dtb_sha256=%s\noutput_dtb_sha256=%s\n' "$BASE_DTB_SHA256" "$OUTPUT_DTB_SHA256"
printf 'package_CPU_clock_properties=10\npostbuild_CPU_clock_mutations=0\n'
printf 'serviceability_property_mutations=20\nserviceability_nodes_added=1\n'
printf 'LK_devinfo_NVMEM=read-only\nI2C6_access_controller=preserved\n'
printf 'DA921x_consumers=0\nDA921x_register_data_writes_expected=0\n'
printf 'CPU8_CPU9_admission=closed\nUSB_role=peripheral\nxhci_status=disabled\n'
printf 'I2C5_status=okay\nAW9523_status=okay\nkeyboard_mode=polling\n'
printf 'watchdog_IRQ=absent\nSCP_status=disabled\n'
printf 'device_access=none\nhardware_write=none\nresult=pass\n'
