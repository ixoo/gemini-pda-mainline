#!/usr/bin/env bash

# Restore the exact Stage-27 I2C5/AW9523 polling-keyboard serviceability group.
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
for command in awk chmod cp dirname dtc fdtget fdtput mkdir mktemp mv rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -f "$base_dtb" && ! -L "$base_dtb" && -s "$base_dtb" ]] ||
	die 'base DTB is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output'
mkdir -p -- "$(dirname -- "$output")"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-16-mainline-wdt-irq-isolation/scripts/build-wdt-noirq-dtb.sh"
readonly SOURCE_BUILDER_SHA256=90de973cd5fa0d5f7625dd5eae8e3fd6a71817f568ae3775983869620b9775ea
readonly PREDECESSOR_DTB_SHA256=49d8189b3801c2e95345857ff704ab0b819001c55101f16dd1949cfa5106d3aa
readonly OUTPUT_DTB_SHA256=a6b76ffc352e818d90709712a372c583ee275baf5f06ebf2cd11f593022b429c
readonly PINCTRL=/pinctrl@10005000
readonly I2C5=/i2c@1101c000
readonly AW9523=/i2c@1101c000/gpio-expander@5b
readonly KEYBOARD=/keyboard-matrix
readonly SCP=/scp@10020000
readonly WDT=/watchdog@10007000
readonly SSUSB=/usb@11271000
readonly XHCI=/usb@11271000/usb@11270000

[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_BUILDER_SHA256" ]] ||
	die 'source watchdog predecessor builder changed'

temporary="$(mktemp "$(dirname -- "$output")/.i2c5-serviceability-dtb.XXXXXXXX")"
rm -f -- "$temporary"
cleanup() { [[ ! -e "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT HUP INT TERM
"$source_builder" --base-dtb "$base_dtb" --output "$temporary" >/dev/null
[[ "$(sha256sum "$temporary" | awk '{print $1}')" == "$PREDECESSOR_DTB_SHA256" ]] ||
	die 'stopped watchdog predecessor DT changed'

[[ "$(fdtget -ts "$temporary" "$I2C5" status)" == disabled ]] ||
	die 'predecessor I2C5 status changed'
[[ "$(fdtget -ts "$temporary" "$AW9523" status)" == disabled ]] ||
	die 'predecessor AW9523 status changed'
[[ "$(fdtget -ts "$temporary" "$KEYBOARD" status)" == disabled ]] ||
	die 'predecessor keyboard status changed'
pinctrl_phandle="$(fdtget -tx "$temporary" "$PINCTRL/i2c5-pins" phandle)"

fdtput -ts "$temporary" "$I2C5" status okay
fdtput -tx "$temporary" "$I2C5" clock-frequency 61a80
fdtput -ts "$temporary" "$I2C5" pinctrl-names default
fdtput -tx "$temporary" "$I2C5" pinctrl-0 "$pinctrl_phandle"
fdtput -ts "$temporary" "$AW9523" status okay
for property in interrupt-parent interrupts interrupt-controller '#interrupt-cells'; do
	fdtput -d "$temporary" "$AW9523" "$property"
done
fdtput -ts "$temporary" "$KEYBOARD" status okay
fdtput -tx "$temporary" "$KEYBOARD" poll-interval 14
fdtput -tx "$temporary" "$KEYBOARD" col-scan-delay-us 2

dtc -q -I dtb -O dtb -o /dev/null "$temporary"
[[ "$(fdtget -ts "$temporary" "$I2C5" status)" == okay ]] || die 'I2C5 is not enabled'
[[ "$(fdtget -tx "$temporary" "$I2C5" clock-frequency)" == 61a80 ]] ||
	die 'I2C5 frequency changed'
[[ "$(fdtget -ts "$temporary" "$I2C5" pinctrl-names)" == default ]] ||
	die 'I2C5 pinctrl name changed'
[[ "$(fdtget -tx "$temporary" "$I2C5" pinctrl-0)" == "$pinctrl_phandle" ]] ||
	die 'I2C5 pinctrl reference changed'
[[ "$(fdtget -ts "$temporary" "$AW9523" status)" == okay ]] || die 'AW9523 is not enabled'
for property in interrupt-parent interrupts interrupt-controller '#interrupt-cells'; do
	if fdtget "$temporary" "$AW9523" "$property" >/dev/null 2>&1; then
		die "AW9523 positive-control property must be absent: $property"
	fi
done
[[ "$(fdtget -ts "$temporary" "$KEYBOARD" status)" == okay ]] ||
	die 'keyboard is not enabled'
[[ "$(fdtget -tx "$temporary" "$KEYBOARD" poll-interval)" == 14 ]] ||
	die 'keyboard poll interval changed'
[[ "$(fdtget -tx "$temporary" "$KEYBOARD" col-scan-delay-us)" == 2 ]] ||
	die 'keyboard scan delay changed'
[[ "$(fdtget -ts "$temporary" "$SCP" status)" == disabled ]] || die 'SCP closure changed'
if fdtget "$temporary" "$WDT" interrupts >/dev/null 2>&1; then
	die 'stopped watchdog IRQ was restored'
fi
[[ "$(fdtget -ts "$temporary" "$SSUSB" status)" == okay ]] || die 'USB status changed'
[[ "$(fdtget -ts "$temporary" "$SSUSB" dr_mode)" == peripheral ]] || die 'USB role changed'
[[ "$(fdtget -ts "$temporary" "$XHCI" status)" == disabled ]] || die 'xHCI closure changed'
[[ "$(sha256sum "$temporary" | awk '{print $1}')" == "$OUTPUT_DTB_SHA256" ]] ||
	die 'derived serviceability DT identity changed'

mv "$temporary" "$output"
chmod 0600 "$output"
temporary=
trap - EXIT HUP INT TERM
printf 'validation=mainline-i2c5-serviceability-restoration-derivation\n'
printf 'predecessor_dtb_sha256=%s\noutput_dtb_sha256=%s\n' \
	"$PREDECESSOR_DTB_SHA256" "$OUTPUT_DTB_SHA256"
printf 'semantic_delta=exact-I2C5-AW9523-polling-keyboard-positive-control-group\n'
printf 'property_mutations=12\nI2C5_status=okay\nAW9523_status=okay\n'
printf 'AW9523_parent_IRQ=absent\nkeyboard_status=okay\nkeyboard_mode=polling\n'
printf 'SCP_status=disabled\nwatchdog_IRQ=absent\nUSB_role=peripheral\n'
printf 'xhci_status=disabled\nrole=peripheral\nmaximum_speed=high-speed\n'
printf 'device_access=none\nhardware_write=none\nresult=pass\n'
