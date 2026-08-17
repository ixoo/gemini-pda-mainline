#!/usr/bin/env bash

# Delete only the MT6797 watchdog IRQ from the exact stopped predecessor DT.
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
for command in awk chmod dirname dtc fdtget fdtput mkdir mktemp rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -f "$base_dtb" && ! -L "$base_dtb" && -s "$base_dtb" ]] ||
	die 'base DTB is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output'
mkdir -p -- "$(dirname -- "$output")"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-16-mainline-scp-handoff-node/scripts/build-scp-handoff-dtb.sh"
readonly SOURCE_BUILDER_SHA256=932f0b987275539dcc0b9ea8126e3787ab2d4347d8d322221c83f9e3de41e0b8
readonly PREDECESSOR_DTB_SHA256=53ceeaddcae13ff10ddc219441ac46a300324e5490e436626601f0d928c1558b
readonly OUTPUT_DTB_SHA256=49d8189b3801c2e95345857ff704ab0b819001c55101f16dd1949cfa5106d3aa
readonly WDT=/watchdog@10007000
readonly SCP=/scp@10020000
readonly SSUSB=/usb@11271000
readonly XHCI=/usb@11271000/usb@11270000

[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_BUILDER_SHA256" ]] ||
	die 'source SCP predecessor builder changed'

temporary="$(mktemp "$(dirname -- "$output")/.wdt-noirq-dtb.XXXXXXXX")"
rm -f -- "$temporary"
cleanup() { [[ ! -e "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT HUP INT TERM
"$source_builder" --base-dtb "$base_dtb" --output "$temporary" >/dev/null
[[ "$(sha256sum "$temporary" | awk '{print $1}')" == "$PREDECESSOR_DTB_SHA256" ]] ||
	die 'source SCP predecessor DT changed'
[[ "$(fdtget -tx "$temporary" "$WDT" interrupts)" == '0 89 2' ]] ||
	die 'predecessor watchdog IRQ changed'

fdtput -d "$temporary" "$WDT" interrupts
dtc -q -I dtb -O dtb -o /dev/null "$temporary"
if fdtget "$temporary" "$WDT" interrupts >/dev/null 2>&1; then
	die 'watchdog IRQ property remains present'
fi
[[ "$(fdtget -ts "$temporary" "$WDT" compatible)" == \
	'mediatek,mt6797-wdt mediatek,mt6589-wdt' ]] || die 'watchdog compatible changed'
[[ "$(fdtget -tx "$temporary" "$WDT" reg)" == '0 10007000 0 100' ]] ||
	die 'watchdog register range changed'
[[ "$(fdtget -tx "$temporary" "$WDT" '#reset-cells')" == 1 ]] ||
	die 'watchdog reset-provider input changed'
[[ "$(fdtget -ts "$temporary" "$SCP" status)" == disabled ]] ||
	die 'SCP closure changed'
[[ "$(fdtget -ts "$temporary" "$SSUSB" status)" == okay ]] ||
	die 'USB observation controller changed'
[[ "$(fdtget -ts "$temporary" "$SSUSB" dr_mode)" == peripheral ]] ||
	die 'USB role changed'
[[ "$(fdtget -ts "$temporary" "$SSUSB" maximum-speed)" == high-speed ]] ||
	die 'USB speed changed'
[[ "$(fdtget -ts "$temporary" "$XHCI" status)" == disabled ]] ||
	die 'host-controller closure changed'
[[ "$(sha256sum "$temporary" | awk '{print $1}')" == "$OUTPUT_DTB_SHA256" ]] ||
	die 'derived watchdog no-IRQ DT identity changed'

mv "$temporary" "$output"
chmod 0600 "$output"
temporary=
trap - EXIT HUP INT TERM
printf 'validation=mainline-wdt-irq-isolation-derivation\n'
printf 'predecessor_dtb_sha256=%s\noutput_dtb_sha256=%s\n' \
	"$PREDECESSOR_DTB_SHA256" "$OUTPUT_DTB_SHA256"
printf 'semantic_delta=delete-watchdog-interrupts-property-only\n'
printf 'watchdog_irq=absent\nwatchdog_reset_cells=1\n'
printf 'scp_status=disabled\nusb_status=okay\n'
printf 'xhci_status=disabled\nrole=peripheral\nmaximum_speed=high-speed\n'
printf 'device_access=none\nhardware_write=none\nresult=pass\n'
