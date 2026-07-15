#!/usr/bin/env bash

set -euo pipefail

# Static-only audit of the extracted Gemini connectivity userspace.  The
# payload is treated as immutable evidence: this script never executes an
# AArch32/AArch64 payload binary, opens a device node, loads firmware, or
# invokes an ioctl.

ROOT=${GEMINI_VENDOR_ROOT:-"$HOME/reverse-engineering/gemini-vendor"}

command -v file >/dev/null 2>&1 || { echo "file is required" >&2; exit 1; }
command -v readelf >/dev/null 2>&1 || { echo "readelf is required" >&2; exit 1; }
command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum is required" >&2; exit 1; }
command -v strings >/dev/null 2>&1 || { echo "strings is required" >&2; exit 1; }

readonly -a FILES=(
	"system/vendor/bin/wmt_launcher"
	"system/vendor/bin/wmt_loader"
	"system/vendor/bin/wmt_loopback"
	"system/vendor/bin/wmt_concurrency"
	"system/vendor/bin/stp_dump3"
	"system/vendor/bin/wifi2agps"
	"system/vendor/bin/mtk_agpsd"
	"system/vendor/lib/hw/gps.mt6797.so"
	"system/vendor/lib64/hw/gps.mt6797.so"
	"system/vendor/lib64/libwifitest.so"
)

print_one_line() {
	local label="$1"
	local value="$2"
	printf '%s=%s\n' "$label" "$value"
}

readelf_needed() {
	readelf -d "$1" 2>/dev/null |
		awk -F'[][]' '/\(NEEDED\)/ { printf "%s%s", sep, $2; sep = "," }'
}

readelf_exports() {
	local path="$1"
	readelf -Ws "$path" 2>/dev/null |
		awk '$4 == "FUNC" && $5 == "GLOBAL" && $6 == "DEFAULT" && $7 != "UND" { print $8 }' |
		grep -E '^(gps|hal2mnl|gpshal|WIFI_TEST|wifi_set_power)' |
		sort -u | paste -sd, - || true
}

print_string_anchors() {
	local path="$1"
	strings -a -n 5 "$path" |
		grep -E '(^/dev/|^/system/(vendor/)?firmware|^/data/(agps_supl|misc/stp_dump)|WMT|wmt|STP|stp|GPS|gps|AGPS|agps|WIFI|wifi|SDIO|BTIF|btif|property|ioctl|socket|ttyMT|mt6797|MT279|SUPL_|MSG_ID_)' |
		sort -u | head -80 | paste -sd';' - || true
}

print_ioctl_sites() {
	local path="$1"
	local kind
	local disassembler
	kind="$(file -b "$path")"
	if [[ "$kind" == *aarch64* ]] && command -v aarch64-linux-gnu-objdump >/dev/null 2>&1; then
		disassembler=aarch64-linux-gnu-objdump
	elif [[ "$kind" == *ARM,* ]] && command -v arm-linux-gnueabi-objdump >/dev/null 2>&1; then
		disassembler=arm-linux-gnueabi-objdump
	else
		return 0
	fi

	# Keep only short call-site neighborhoods.  Immediate request words are
	# evidence for the private ABI, not decoded ioctl names; naming them would
	# require the matching vendor kernel header or a trace.
	"$disassembler" -d "$path" 2>/dev/null |
		awk '
			/^[[:space:]]*[0-9a-f]+:/ { p4 = p3; p3 = p2; p2 = p1; p1 = $0 }
			/<ioctl@plt>/ {
				print p4;
				print p3;
				print p2;
				print p1;
				print "--";
				seen++;
				if (seen == 12) exit
			}' || true
}

printf 'audit=gemini-connectivity-userspace-static\n'
printf 'analysis=metadata_strings_exports_and_bounded_ioctl_call_sites\n'
printf 'execution=none\n'
printf 'payload_root=%s\n\n' "$ROOT"

for relative in "${FILES[@]}"; do
	path="$ROOT/$relative"
	printf '[file]\n'
	print_one_line path "$relative"
	if [[ ! -f "$path" ]]; then
		print_one_line present no
		printf '\n'
		continue
	fi
	print_one_line present yes
	print_one_line size_bytes "$(stat -c '%s' "$path")"
	print_one_line sha256 "$(sha256sum "$path" | awk '{ print $1 }')"
	print_one_line elf "$(file -b "$path")"
	print_one_line needed "$(readelf_needed "$path")"
	print_one_line exports "$(readelf_exports "$path")"
	print_one_line string_anchors "$(print_string_anchors "$path")"
	printf '[ioctl_call_sites]\n'
	print_ioctl_sites "$path"
	printf '\n'
done
