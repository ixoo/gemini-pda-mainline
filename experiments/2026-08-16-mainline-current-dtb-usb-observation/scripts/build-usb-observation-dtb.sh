#!/usr/bin/env bash

# Derive the minimum live-USB observation DT from the exact current package DT.
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
for command in awk dirname dtc fdtget fdtput install mkdir mktemp rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 ||
		die "required command missing: $command"
done
[[ -f "$base_dtb" && ! -L "$base_dtb" && -s "$base_dtb" ]] ||
	die 'base DTB is missing, empty, or unsafe'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite output'
mkdir -p -- "$(dirname -- "$output")"

readonly BASE_DTB_SHA256=61ea34a4f780afe04da1257f8c3655be7f8490a7c3af2df727dd8592bb6e6285
readonly OUTPUT_DTB_SHA256=e93264b32e0a42098fa6556e454abc99b75373e92e1e3b6eef50285542251331
readonly TPHY=/t-phy@11290000
readonly U2PORT0=/t-phy@11290000/usb-phy@11290800
readonly SSUSB=/usb@11271000
readonly XHCI=/usb@11271000/usb@11270000

[[ "$(sha256sum "$base_dtb" | awk '{print $1}')" == "$BASE_DTB_SHA256" ]] ||
	die 'base DTB identity changed'
[[ "$(fdtget -ts "$base_dtb" / compatible)" == \
	'planet,gemini-pda mediatek,mt6797' ]] || die 'board compatibility changed'
for node_path in "$TPHY" "$U2PORT0" "$SSUSB"; do
	[[ "$(fdtget -ts "$base_dtb" "$node_path" status)" == disabled ]] ||
		die "base observation node is not disabled: $node_path"
done
[[ "$(fdtget -ts "$base_dtb" "$XHCI" status)" == disabled ]] ||
	die 'host controller policy changed'
[[ "$(fdtget -ts "$base_dtb" "$SSUSB" dr_mode)" == peripheral ]] ||
	die 'SSUSB role changed'
[[ "$(fdtget -ts "$base_dtb" "$SSUSB" maximum-speed)" == high-speed ]] ||
	die 'SSUSB speed policy changed'

temporary="$(mktemp "$(dirname -- "$output")/.usb-observation-dtb.XXXXXXXX")"
cleanup() { [[ ! -e "${temporary:-}" ]] || rm -f -- "$temporary"; }
trap cleanup EXIT HUP INT TERM
install -m 0600 "$base_dtb" "$temporary"
for node_path in "$TPHY" "$U2PORT0" "$SSUSB"; do
	fdtput -t s "$temporary" "$node_path" status okay
done
dtc -q -I dtb -O dtb -o /dev/null "$temporary"
for node_path in "$TPHY" "$U2PORT0" "$SSUSB"; do
	[[ "$(fdtget -ts "$temporary" "$node_path" status)" == okay ]] ||
		die "derived observation node is not enabled: $node_path"
done
[[ "$(fdtget -ts "$temporary" "$XHCI" status)" == disabled ]] ||
	die 'derived DT unexpectedly enabled the host controller'
[[ "$(sha256sum "$temporary" | awk '{print $1}')" == "$OUTPUT_DTB_SHA256" ]] ||
	die 'derived DT identity changed'

install -m 0600 "$temporary" "$output"
printf 'validation=current-dtb-usb-observation-derivation\n'
printf 'base_dtb_sha256=%s\noutput_dtb_sha256=%s\n' \
	"$BASE_DTB_SHA256" "$OUTPUT_DTB_SHA256"
printf 'semantic_delta_count=3\n'
printf 'enabled_nodes=%s,%s,%s\n' "$TPHY" "$U2PORT0" "$SSUSB"
printf 'xhci_status=disabled\nrole=peripheral\nmaximum_speed=high-speed\n'
printf 'device_access=none\nhardware_write=none\nresult=pass\n'
