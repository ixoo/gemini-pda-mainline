#!/usr/bin/env bash
# Read-only, bounded runtime identity-surface census over the Gemini USB shell.
# Only path labels, token labels, and counts leave the device.
set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_MAC=42:00:15:19:82:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DEVICE_PORT=2323

die() {
	printf 'error: %s\n' "$*" >&2
	exit 2
}
usage() {
	printf 'usage: %s --interface IFACE --output FILE\n' "$0" >&2
}

interface=
output=
while (($#)); do
	case "$1" in
	--interface)
		(($# >= 2)) || die '--interface requires a value'
		[[ -z "$interface" ]] || die '--interface duplicated'
		interface=$2
		shift 2
		;;
	--output)
		(($# >= 2)) || die '--output requires a value'
		[[ -z "$output" ]] || die '--output duplicated'
		output=$2
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

[[ "$interface" =~ ^[A-Za-z0-9]+$ && -n "$output" ]] || {
	usage
	exit 2
}
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite runtime capture'
[[ -d "$(dirname -- "$output")" ]] || die 'output directory does not exist'
for command in awk dirname ifconfig mktemp mv nc ping rm route; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

mac="$(ifconfig "$interface" | awk '/^[[:space:]]*ether / { print tolower($2); exit }')"
[[ "$mac" == "$HOST_MAC" ]] || die "interface $interface is not the Gemini USB MAC"
ifconfig "$interface" | awk -v address="$HOST_ADDRESS" \
	'$1 == "inet" && $2 == address { found = 1 } END { exit !found }' || \
	die 'host USB address is absent'
route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | \
	awk '$1 == "interface:" { print $2; count++ } END { exit count != 1 }')"
[[ "$route_interface" == "$interface" ]] || die 'device route is not the exact Gemini interface'
ping -b "$interface" -c 3 -S "$HOST_ADDRESS" "$DEVICE_ADDRESS" >/dev/null || \
	die 'bounded USB ping failed'

command_file="$(mktemp "${TMPDIR:-/tmp}/gemini-runtime-identity-nc-command.XXXXXX")"
capture_file="$(mktemp "${TMPDIR:-/tmp}/gemini-runtime-identity-nc-output.XXXXXX")"
cleanup() {
	[[ ! -f "$command_file" ]] || rm -f -- "$command_file"
	[[ ! -f "$capture_file" ]] || rm -f -- "$capture_file"
}
trap cleanup EXIT HUP INT TERM

cat >"$command_file" <<'REMOTE'
/bin/busybox sh <<'__GEMINI_REMOTE__'
set -eu
export LC_ALL=C
printf '%s\n' '# Gemian runtime identity-surface census (direct USB netcat)'
printf 'kernel=%s\n' "$(uname -r)"
printf 'architecture=%s\n' "$(uname -m)"
printf 'boot_id=%s\n' "$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unavailable)"
printf 'cpu_possible=%s\n' "$(cat /sys/devices/system/cpu/possible 2>/dev/null || echo unavailable)"
printf 'cpu_present=%s\n' "$(cat /sys/devices/system/cpu/present 2>/dev/null || echo unavailable)"
printf 'cpu_online=%s\n' "$(cat /sys/devices/system/cpu/online 2>/dev/null || echo unavailable)"

tmp=${TMPDIR:-/tmp}/gemini-runtime-identity-nc.$$
trap 'rm -f "$tmp" "$tmp.paths"' EXIT HUP INT TERM
: >"$tmp.paths"
for root in /sys/kernel/debug /sys/devices/platform /sys/devices/system/cpu /proc/device-tree; do
	if [ -d "$root" ]; then
		find "$root" -maxdepth 6 -type f 2>/dev/null || true
	fi
done | grep -Ei '/(dvfs|eem|ppm|cpufreq|calib|volt|vsram|vproc|epoch|generation|owner|lock|transition|handle|ptp)(/|$)|/(dvfs|eem|ppm|cpufreq|calib|volt|vsram|vproc|epoch|generation|owner|lock|transition|handle|ptp)[^/]*$' \
	| sort -u | head -n 256 >"$tmp.paths" || true
printf 'candidate_path_count=%s\n' "$(wc -l <"$tmp.paths" | tr -d ' ')"
while IFS= read -r path; do
	[ -r "$path" ] || continue
	printf 'candidate_path=%s\n' "$path"
done <"$tmp.paths"

scan_file() {
	path=$1
	[ -r "$path" ] || return 0
	bytes=$(wc -c <"$path" 2>/dev/null | tr -d ' ' || echo 0)
	hits=
	for token in epoch generation calibration handle owner transition lock mutex atomic; do
		if head -c 4096 "$path" 2>/dev/null | tr '\000' ' ' | grep -Eiq "$token"; then
			hits=${hits:+"$hits,"}$token
		fi
	done
	[ -z "$hits" ] || printf 'content_token_hit=%s tokens=%s bytes=%s\n' "$path" "$hits" "$bytes"
}
while IFS= read -r path; do
	scan_file "$path"
done <"$tmp.paths"
for path in /proc/ppm /proc/eem /proc/cpufreq; do
	[ -e "$path" ] || continue
	printf 'known_surface=%s\n' "$path"
	if [ -f "$path" ]; then
		scan_file "$path"
	else
		find "$path" -maxdepth 2 -type f 2>/dev/null | sort -u | head -n 64 |
			while IFS= read -r child; do
				printf 'known_surface_child=%s\n' "$child"
				scan_file "$child"
			done
	fi
done
printf '%s\n' 'raw_payload_retained=none'
printf '%s\n' 'device_action=none'
printf '%s\n' 'hardware_write=none'
__GEMINI_REMOTE__
REMOTE

if ! nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 110 \
	"$DEVICE_ADDRESS" "$DEVICE_PORT" <"$command_file" >"$capture_file"; then
	die 'direct USB netcat shell failed'
fi
[[ ! -e "$output" && ! -L "$output" ]] || die 'runtime capture appeared during collection'
mv -- "$capture_file" "$output"
printf 'runtime_capture=%s\n' "$output"
