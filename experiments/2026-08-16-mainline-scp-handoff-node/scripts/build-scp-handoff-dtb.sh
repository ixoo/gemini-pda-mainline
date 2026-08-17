#!/usr/bin/env bash

# Add the one disabled SCP node required by the pinned public MT6797 LK path.
set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'Usage: %s --base-dtb FILE --output FILE\n' "$0"; }

base_dtb=
output=
while [[ "$#" -gt 0 ]]; do
	case "$1" in
	--base-dtb) base_dtb=${2:-}; shift 2 ;;
	--output) output=${2:-}; shift 2 ;;
	-h|--help) usage; exit 0 ;;
	*) die "unknown argument: $1" ;;
	esac
done
[[ -n "$base_dtb" && -n "$output" ]] || { usage >&2; exit 2; }
for command in awk dirname dtc fdtget fdtput mkdir mktemp rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
[[ -f "$base_dtb" && ! -L "$base_dtb" && -s "$base_dtb" ]] ||
	die 'base DTB is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output'
mkdir -p -- "$(dirname -- "$output")"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
source_builder="$repo_root/experiments/2026-08-16-mainline-current-dtb-usb-observation/scripts/build-usb-observation-dtb.sh"
readonly SOURCE_BUILDER_SHA256=dbf8a99fc99f2f7cbd256495bb3d295b2c5bed9b627a9c60a338cfa518303efb
readonly USB_DTB_SHA256=e93264b32e0a42098fa6556e454abc99b75373e92e1e3b6eef50285542251331
readonly OUTPUT_DTB_SHA256=53ceeaddcae13ff10ddc219441ac46a300324e5490e436626601f0d928c1558b
readonly SCP=/scp@10020000
readonly TPHY=/t-phy@11290000
readonly U2PORT0=/t-phy@11290000/usb-phy@11290800
readonly SSUSB=/usb@11271000
readonly XHCI=/usb@11271000/usb@11270000

[[ -f "$source_builder" && ! -L "$source_builder" ]] || die 'source builder is unsafe'
[[ "$(sha256sum "$source_builder" | awk '{print $1}')" == "$SOURCE_BUILDER_SHA256" ]] ||
	die 'source USB-observation builder changed'
if fdtget "$base_dtb" "$SCP" compatible >/dev/null 2>&1; then
	die 'base DT unexpectedly contains the selected SCP node'
fi

temporary="$(mktemp "$(dirname -- "$output")/.scp-handoff-dtb.XXXXXXXX")"
rm -f -- "$temporary"
cleanup() { [[ ! -e "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT HUP INT TERM
"$source_builder" --base-dtb "$base_dtb" --output "$temporary" >/dev/null
[[ "$(sha256sum "$temporary" | awk '{print $1}')" == "$USB_DTB_SHA256" ]] ||
	die 'source USB-observation DT changed'

fdtput -c "$temporary" "$SCP"
fdtput -t s "$temporary" "$SCP" compatible mediatek,scp
fdtput -t x "$temporary" "$SCP" reg \
	0 10020000 0 80000 0 100a0000 0 1000 0 100a4000 0 1000
fdtput -t x "$temporary" "$SCP" interrupts 0 c7 4
fdtput -t s "$temporary" "$SCP" status disabled
dtc -q -I dtb -O dtb -o /dev/null "$temporary"

[[ "$(fdtget -ts "$temporary" "$SCP" compatible)" == mediatek,scp ]] ||
	die 'SCP compatible changed'
[[ "$(fdtget -ts "$temporary" "$SCP" status)" == disabled ]] ||
	die 'SCP input status is not disabled'
[[ "$(fdtget -tx "$temporary" "$SCP" interrupts)" == '0 c7 4' ]] ||
	die 'SCP interrupt tuple changed'
[[ "$(fdtget -tx "$temporary" "$SCP" reg)" == \
	'0 10020000 0 80000 0 100a0000 0 1000 0 100a4000 0 1000' ]] ||
	die 'SCP register ranges changed'
for node_path in "$TPHY" "$U2PORT0" "$SSUSB"; do
	[[ "$(fdtget -ts "$temporary" "$node_path" status)" == okay ]] ||
		die "USB observation node changed: $node_path"
done
[[ "$(fdtget -ts "$temporary" "$XHCI" status)" == disabled ]] ||
	die 'host-controller closure changed'
[[ "$(fdtget -ts "$temporary" "$SSUSB" dr_mode)" == peripheral ]] ||
	die 'USB role changed'
[[ "$(fdtget -ts "$temporary" "$SSUSB" maximum-speed)" == high-speed ]] ||
	die 'USB speed changed'
[[ "$(sha256sum "$temporary" | awk '{print $1}')" == "$OUTPUT_DTB_SHA256" ]] ||
	die 'derived SCP handoff DT identity changed'

mv "$temporary" "$output"
chmod 0600 "$output"
temporary=
trap - EXIT HUP INT TERM
printf 'validation=mainline-scp-handoff-node-derivation\n'
printf 'base_usb_dtb_sha256=%s\noutput_dtb_sha256=%s\n' \
	"$USB_DTB_SHA256" "$OUTPUT_DTB_SHA256"
printf 'semantic_delta=one-disabled-mediatek-scp-node\n'
printf 'scp_status=disabled\nLinux_probe=closed\n'
printf 'usb_status_properties=3\nxhci_status=disabled\n'
printf 'role=peripheral\nmaximum_speed=high-speed\n'
printf 'device_access=none\nhardware_write=none\nresult=pass\n'
