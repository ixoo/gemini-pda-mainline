#!/usr/bin/env bash

# Capture Candidate AP's raw post-LK FDT over its inherited direct USB shell.
# The remote command reads only boot identity, /proc/config.gz, and
# /sys/firmware/fdt. It performs no partition, bus, regulator, CPU-hotplug,
# watchdog, reboot, or power-state operation.

set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_MAC=42:00:15:19:82:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly DECODER_SHA256=459305f848380f55f7a191a445c1fb2460af8efd96d91142732b7f9b2faf05c8

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --interface IFACE --output-dir ABSOLUTE-DIR --expected-config-sha256 SHA256\n' "$0" >&2
}

interface=
output_dir=
expected_config_sha256=
while (($#)); do
	case "$1" in
	--interface|--output-dir|--expected-config-sha256)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--interface)
			[[ -z "$interface" ]] || die "$1 duplicated"
			interface=$2
			;;
		--output-dir)
			[[ -z "$output_dir" ]] || die "$1 duplicated"
			output_dir=$2
			;;
		--expected-config-sha256)
			[[ -z "$expected_config_sha256" ]] || die "$1 duplicated"
			expected_config_sha256=$2
			;;
		esac
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

[[ "$interface" =~ ^[A-Za-z0-9]+$ ]] || {
	usage
	die 'interface must contain only ASCII letters and digits'
}
[[ -n "$output_dir" && "$output_dir" == /* ]] || {
	usage
	die 'output directory must be absolute'
}
[[ "$expected_config_sha256" =~ ^[0-9a-f]{64}$ ]] || {
	usage
	die 'expected configuration must be one lowercase SHA-256 value'
}
for command in awk cat chmod dirname ifconfig mktemp nc ping python3 rm route \
	shasum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repository="$(cd -- "$script_dir/../../.." && pwd -P)"
decoder="$script_dir/decode-live-fdt.py"
[[ -f "$decoder" && ! -L "$decoder" ]] || die 'live-FDT decoder is missing or unsafe'
[[ "$(shasum -a 256 "$decoder" | awk '{ print $1 }')" == \
	"$DECODER_SHA256" ]] || die 'source-pinned live-FDT decoder changed'

mac="$(ifconfig "$interface" | \
	awk '/^[[:space:]]*ether / { print tolower($2); count++; exit } END { exit count != 1 }')"
[[ "$mac" == "$HOST_MAC" ]] || die "interface $interface is not the Gemini USB MAC"
ifconfig "$interface" | awk -v address="$HOST_ADDRESS" \
	'$1 == "inet" && $2 == address { found++ } END { exit found != 1 }' || \
	die 'host USB address is absent or duplicated'
route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | \
	awk '$1 == "interface:" { print $2; count++ } END { exit count != 1 }')"
[[ "$route_interface" == "$interface" ]] || \
	die 'device route is not the exact Gemini USB interface'
ping -b "$interface" -c 3 -S "$HOST_ADDRESS" "$DEVICE_ADDRESS" >/dev/null || \
	die 'bounded direct-USB ping failed'

python3 "$decoder" prepare \
	--repository "$repository" \
	--output-dir "$output_dir"

command_file="$(mktemp /tmp/candidate-ap-live-fdt-command.XXXXXX)"
cleanup() {
	[[ ! -f "$command_file" ]] || rm -f -- "$command_file"
}
trap cleanup EXIT

cat >"$command_file" <<'EOF'
/bin/busybox sh <<'__AP_LIVE_FDT_REMOTE__'
set -eu
fdt=/sys/firmware/fdt
config=/proc/config.gz
boot_id_path=/proc/sys/kernel/random/boot_id
[ -r "$fdt" ] && [ -r "$config" ] && [ -r "$boot_id_path" ]

file_sha256() {
	/bin/busybox sha256sum "$1" | /bin/busybox awk '{ print $1 }'
}
file_size() {
	/bin/busybox stat -c '%s' "$1"
}

boot_id_pre=$(/bin/busybox cat "$boot_id_path")
config_sha256=$(
	/bin/busybox zcat "$config" |
		/bin/busybox sha256sum |
		/bin/busybox awk '{ print $1 }'
)
fdt_sha256_pre=$(file_sha256 "$fdt")
fdt_size_pre=$(file_size "$fdt")

printf '\n%s\n' '__AP_LIVE_FDT_CAPTURE_BEGIN__'
printf 'boot_id_pre=%s\n' "$boot_id_pre"
printf 'config_sha256=%s\n' "$config_sha256"
printf 'fdt_sha256_pre=%s\n' "$fdt_sha256_pre"
printf 'fdt_size_pre=%s\n' "$fdt_size_pre"
printf '%s\n' '__AP_LIVE_FDT_BASE64_BEGIN__'
/bin/busybox base64 "$fdt"
printf '%s\n' '__AP_LIVE_FDT_BASE64_END__'

boot_id_post=$(/bin/busybox cat "$boot_id_path")
fdt_sha256_post=$(file_sha256 "$fdt")
fdt_size_post=$(file_size "$fdt")
printf 'boot_id_post=%s\n' "$boot_id_post"
printf 'fdt_sha256_post=%s\n' "$fdt_sha256_post"
printf 'fdt_size_post=%s\n' "$fdt_size_post"
printf '%s\n\n' '__AP_LIVE_FDT_CAPTURE_END__'
exit
__AP_LIVE_FDT_REMOTE__
exit
EOF

transcript="$output_dir/live-fdt-transfer.txt"
[[ ! -e "$transcript" && ! -L "$transcript" ]] || \
	die 'refusing to overwrite a live-FDT transcript'
( set -C; : >"$transcript" ) 2>/dev/null || \
	die 'cannot exclusively create the live-FDT transcript'
chmod 0600 "$transcript"
{
	printf '%s\n' '__AP_LIVE_FDT_HOST_BEGIN__'
	printf 'interface=%s\n' "$interface"
	printf 'route_interface=%s\n' "$route_interface"
	printf 'mac=%s\n' "$mac"
	printf 'host_address=%s\n' "$HOST_ADDRESS"
	printf 'device_address=%s\n' "$DEVICE_ADDRESS"
	printf 'capture_transport=direct-usb-tcp-2323\n'
	printf 'authentication=none\n'
	printf 'encryption=none\n'
	printf 'fdt_source=/sys/firmware/fdt\n'
	printf 'device_partition_read=no\n'
	printf 'hardware_write=no\n'
	printf 'i2c_transaction_or_controller_control=none\n'
	printf 'regulator_control=none\n'
	printf 'cpu_hotplug_control=none\n'
	printf 'watchdog_control=none\n'
	printf 'reboot_executed=no\n'
	printf 'power_state_transition_requested=no\n'
	printf '%s\n' '__AP_LIVE_FDT_HOST_END__'
} >>"$transcript"

if ! nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 60 \
	"$DEVICE_ADDRESS" 2323 <"$command_file" >>"$transcript"; then
	die 'bounded direct-USB live-FDT transfer failed'
fi

python3 "$decoder" decode \
	--repository "$repository" \
	--output-dir "$output_dir" \
	--expected-config-sha256 "$expected_config_sha256"
