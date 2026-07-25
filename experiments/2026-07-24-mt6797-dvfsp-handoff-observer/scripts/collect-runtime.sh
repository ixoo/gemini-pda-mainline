#!/usr/bin/env bash

# Candidate AN keeps the hardware-passed Candidate AH console, USB, keyboard,
# reboot, and eight-A53 contract.  Its only runtime addition is a read-only
# platform observer for the retained MT6797 DVFSP firmware handoff.
#
# This collector performs bounded observation only.  It does not read a device
# partition, perform an I2C or regulator operation, request CPU8/CPU9, write a
# sysfs control, arm a watchdog, or reboot the device.
#
# The inherited keymap verifier is a narrow exception to a literal read-only
# open-mode claim: it opens /dev/tty1 O_RDWR, then --verify issues only the
# readback ioctls KDGKBMODE and KDGKBENT.  It does not issue KDSKBMODE,
# KDSKBENT, load a map, inject a key, or otherwise mutate VT state.

set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_MAC=42:00:15:19:82:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82

# This exact 16 MiB zero-padded identity mirrors candidate_an.py after two
# independently reproduced Candidate AN artifact trees.
# test-runtime-validator.py requires the two source values to remain identical.
readonly EXPECTED_INSTALLED_FULL_SHA256=1ef53a25c274ed6f0df265fbc4f4e3a64150d5b7fd4cd1e0cde1db53ffb18ccb

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --interface IFACE --output FILE --installed-full-sha256 SHA256\n' "$0" >&2
}

interface=
output=
installed_full_sha256=
while (($#)); do
	case "$1" in
	--interface|--output|--installed-full-sha256)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--interface)
			[[ -z "$interface" ]] || die '--interface duplicated'
			interface=$2
			;;
		--output)
			[[ -z "$output" ]] || die '--output duplicated'
			output=$2
			;;
		--installed-full-sha256)
			[[ -z "$installed_full_sha256" ]] || \
				die '--installed-full-sha256 duplicated'
			installed_full_sha256=$2
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

[[ "$interface" =~ ^[A-Za-z0-9]+$ && -n "$output" ]] || {
	usage
	exit 2
}
[[ "$installed_full_sha256" =~ ^[0-9a-f]{64}$ ]] || \
	die 'installed checksum must be one lowercase SHA-256 value'
[[ "$EXPECTED_INSTALLED_FULL_SHA256" =~ ^[0-9a-f]{64}$ ]] || \
	die 'Candidate AN padded image identity is not calibrated'
[[ "$installed_full_sha256" == "$EXPECTED_INSTALLED_FULL_SHA256" ]] || \
	die 'installed full-partition checksum is not the exact validated AN value'
[[ ! -e "$output" && ! -L "$output" ]] || \
	die 'refusing to overwrite runtime capture'
for command in awk cat dirname ifconfig mktemp nc ping python3 rm route; do
	command -v "$command" >/dev/null 2>&1 || \
		die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
mac="$(ifconfig "$interface" | \
	awk '/^[[:space:]]*ether / { print tolower($2); exit }')"
[[ "$mac" == "$HOST_MAC" ]] || \
	die "interface $interface is not the exact Gemini USB MAC"
ifconfig "$interface" | awk -v address="$HOST_ADDRESS" \
	'$1 == "inet" && $2 == address { found = 1 } END { exit !found }' || \
	die 'host USB address is absent'
route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | \
	awk '$1 == "interface:" { print $2; count++ } END { exit count != 1 }')"
[[ "$route_interface" == "$interface" ]] || \
	die 'device route is not the exact Gemini interface'
ping -b "$interface" -c 3 -S "$HOST_ADDRESS" "$DEVICE_ADDRESS" >/dev/null || \
	die 'bounded USB ping failed'

command_file="$(mktemp /tmp/candidate-an-runtime-command.XXXXXX)"
cleanup() { [[ ! -f "$command_file" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
cat >"$command_file" <<'EOF'
/bin/busybox sh <<'__AN_REMOTE_SCRIPT__'
uptime_seconds=$(/bin/busybox cut -d. -f1 /proc/uptime)
if [ "$uptime_seconds" -lt 45 ]; then
	/bin/busybox sleep $((45 - uptime_seconds))
fi

property_hex() {
	if [ -f "$1" ]; then
		/bin/busybox hexdump -v -e '1/1 "%02x"' "$1"
	else
		printf 'missing'
	fi
}

file_sha256() {
	if [ -f "$1" ]; then
		/bin/busybox sha256sum "$1" | /bin/busybox awk '{ print $1 }'
	else
		printf 'missing'
	fi
}

compatible_count() {
	root=/sys/firmware/devicetree/base
	wanted=$1
	count=0
	for property in $(/bin/busybox find "$root" -type f -name compatible); do
		compatible=$(property_hex "$property")
		[ "$compatible" != "$wanted" ] || count=$((count + 1))
	done
	printf '%s' "$count"
}

read_state() {
	dt_root=/sys/firmware/devicetree/base
	chosen=$dt_root/chosen
	simplefb_node=$chosen/framebuffer@7dfb0000
	reserved_root=$dt_root/reserved-memory
	reserved_fb=$reserved_root/mblock-3-framebuffer
	platform_fb=/sys/bus/platform/devices/7dfb0000.framebuffer
	printf 'live_fdt_sha256='
	file_sha256 /sys/firmware/fdt
	printf '\n'
	printf 'live_fdt_size='
	/bin/busybox stat -c '%s' /sys/firmware/fdt 2>/dev/null || \
		printf 'missing\n'

	chosen_framebuffer_child_count=0
	chosen_simplefb_compatible_count=0
	for node in "$chosen"/framebuffer@*; do
		[ -d "$node" ] || continue
		chosen_framebuffer_child_count=$((chosen_framebuffer_child_count + 1))
	done
	for node in "$chosen"/*; do
		[ -d "$node" ] || continue
		compatible=$(property_hex "$node/compatible")
		[ "$compatible" != 73696d706c652d6672616d6562756666657200 ] || \
			chosen_simplefb_compatible_count=$((chosen_simplefb_compatible_count + 1))
	done
	printf 'chosen_framebuffer_child_count=%s\n' "$chosen_framebuffer_child_count"
	printf 'chosen_simplefb_compatible_count=%s\n' "$chosen_simplefb_compatible_count"
	[ ! -d "$simplefb_node" ] || printf 'simplefb_node_present=1\n'
	[ -d "$simplefb_node" ] || printf 'simplefb_node_present=0\n'
	printf 'chosen_address_cells_hex='
	property_hex "$chosen/#address-cells"
	printf '\n'
	printf 'chosen_size_cells_hex='
	property_hex "$chosen/#size-cells"
	printf '\n'
	printf 'chosen_ranges_hex='
	property_hex "$chosen/ranges"
	printf '\n'
	printf 'simplefb_compatible_hex='
	property_hex "$simplefb_node/compatible"
	printf '\n'
	printf 'simplefb_reg_hex='
	property_hex "$simplefb_node/reg"
	printf '\n'
	printf 'simplefb_width_hex='
	property_hex "$simplefb_node/width"
	printf '\n'
	printf 'simplefb_height_hex='
	property_hex "$simplefb_node/height"
	printf '\n'
	printf 'simplefb_stride_hex='
	property_hex "$simplefb_node/stride"
	printf '\n'
	printf 'simplefb_format_hex='
	property_hex "$simplefb_node/format"
	printf '\n'
	printf 'simplefb_clocks_hex='
	property_hex "$simplefb_node/clocks"
	printf '\n'
	if [ -e "$simplefb_node/memory-region" ]; then
		printf 'simplefb_memory_region_present=1\n'
	else
		printf 'simplefb_memory_region_present=0\n'
	fi

	runtime_framebuffer_reservation_count=0
	for node in "$reserved_root"/*; do
		[ -d "$node" ] || continue
		compatible=$(property_hex "$node/compatible")
		[ "$compatible" != 6d6564696174656b2c6672616d6562756666657200 ] || \
			runtime_framebuffer_reservation_count=$((runtime_framebuffer_reservation_count + 1))
	done
	printf 'runtime_framebuffer_reservation_count=%s\n' \
		"$runtime_framebuffer_reservation_count"
	[ ! -d "$reserved_fb" ] || \
		printf 'runtime_framebuffer_reservation_present=1\n'
	[ -d "$reserved_fb" ] || \
		printf 'runtime_framebuffer_reservation_present=0\n'
	printf 'runtime_framebuffer_compatible_hex='
	property_hex "$reserved_fb/compatible"
	printf '\n'
	printf 'runtime_framebuffer_reg_hex='
	property_hex "$reserved_fb/reg"
	printf '\n'
	if [ -e "$reserved_fb/no-map" ]; then
		printf 'runtime_framebuffer_no_map_present=1\n'
	else
		printf 'runtime_framebuffer_no_map_present=0\n'
	fi

	simplefb_platform_count=0
	for device in /sys/bus/platform/devices/*; do
		[ -d "$device" ] || continue
		node=$(/bin/busybox readlink -f "$device/of_node" 2>/dev/null || true)
		[ "$node" != "$simplefb_node" ] || \
			simplefb_platform_count=$((simplefb_platform_count + 1))
	done
	printf 'simplefb_platform_count=%s\n' "$simplefb_platform_count"
	[ ! -d "$platform_fb" ] || printf 'simplefb_platform_present=1\n'
	[ -d "$platform_fb" ] || printf 'simplefb_platform_present=0\n'
	if [ -L "$platform_fb/driver" ]; then
		printf 'simplefb_platform_driver='
		/bin/busybox basename "$(/bin/busybox readlink -f "$platform_fb/driver")"
	else
		printf 'simplefb_platform_driver=unbound\n'
	fi

	fb_count=0
	for fb in /sys/class/graphics/fb[0-9]*; do
		[ -d "$fb" ] || continue
		fb_count=$((fb_count + 1))
	done
	printf 'fb_count=%s\n' "$fb_count"
	[ ! -d /sys/class/graphics/fb0 ] || printf 'fb0_present=1\n'
	[ -d /sys/class/graphics/fb0 ] || printf 'fb0_present=0\n'
	printf 'fb0_name='
	/bin/busybox cat /sys/class/graphics/fb0/name 2>/dev/null || \
		printf 'unavailable\n'
	printf 'fb0_virtual_size='
	/bin/busybox cat /sys/class/graphics/fb0/virtual_size 2>/dev/null || \
		printf 'unavailable\n'
	printf 'fb0_bits_per_pixel='
	/bin/busybox cat /sys/class/graphics/fb0/bits_per_pixel 2>/dev/null || \
		printf 'unavailable\n'
	printf 'fb0_stride='
	/bin/busybox cat /sys/class/graphics/fb0/stride 2>/dev/null || \
		printf 'unavailable\n'

	observer_node=$dt_root/dvfsp-observer@11015000
	observer_node_canonical=$(/bin/busybox readlink -f "$observer_node" \
		2>/dev/null || true)
	printf 'dvfsp_observer_dt_count='
	compatible_count \
		6d6564696174656b2c6d74363739372d64766673702d68616e646f66662d6f6273657276657200
	printf '\n'
	[ ! -d "$observer_node" ] || printf 'observer_dt_node_present=1\n'
	[ -d "$observer_node" ] || printf 'observer_dt_node_present=0\n'
	printf 'observer_compatible_hex='
	property_hex "$observer_node/compatible"
	printf '\n'
	printf 'observer_reg_hex='
	property_hex "$observer_node/reg"
	printf '\n'
	printf 'observer_infracfg_hex='
	property_hex "$observer_node/mediatek,infracfg"
	printf '\n'
	printf 'observer_status_hex='
	property_hex "$observer_node/status"
	printf '\n'

	observer_platform_count=0
	observer_device=unavailable
	observer_device_path=
	observer_driver=unavailable
	observer_of_node_target=unavailable
	observer_driver_target=unavailable
	observer_of_node_is_symlink=0
	observer_driver_is_symlink=0
	for device in /sys/bus/platform/devices/*; do
		[ -d "$device" ] || continue
		node=$(/bin/busybox readlink -f "$device/of_node" 2>/dev/null || true)
		if [ -n "$observer_node_canonical" ] && \
		   [ "$node" = "$observer_node_canonical" ]; then
			observer_platform_count=$((observer_platform_count + 1))
			observer_device=${device##*/}
			observer_device_path=$device
			observer_of_node_target=$node
			[ ! -L "$device/of_node" ] || observer_of_node_is_symlink=1
			if [ -L "$device/driver" ]; then
				observer_driver_is_symlink=1
				observer_driver_target=$(/bin/busybox readlink -f \
					"$device/driver")
				observer_driver=$(/bin/busybox basename \
					"$observer_driver_target")
			else
				observer_driver=unbound
			fi
		fi
	done
	printf 'observer_platform_count=%s\n' "$observer_platform_count"
	printf 'observer_device=%s\n' "$observer_device"
	printf 'observer_driver=%s\n' "$observer_driver"
	printf 'observer_of_node_target=%s\n' "$observer_of_node_target"
	printf 'observer_driver_target=%s\n' "$observer_driver_target"
	printf 'observer_of_node_is_symlink=%s\n' \
		"$observer_of_node_is_symlink"
	printf 'observer_driver_is_symlink=%s\n' "$observer_driver_is_symlink"
	if [ -d /sys/bus/platform/drivers/mt6797-dvfsp-handoff-observer ]; then
		printf 'observer_driver_present=1\n'
	else
		printf 'observer_driver_present=0\n'
	fi

	observer_state=unavailable
	observer_snapshots_hex=missing
	observer_snapshots_sha256=missing
	observer_snapshot_line_count=0
	observer_state_mode=missing
	observer_state_uid=missing
	observer_state_gid=missing
	observer_snapshots_mode=missing
	observer_snapshots_uid=missing
	observer_snapshots_gid=missing
	observer_snapshots_capture_ok=0
	if [ "$observer_platform_count" -eq 1 ] && \
	   [ -f "$observer_device_path/state" ] && \
	   [ -f "$observer_device_path/snapshots" ]; then
		observer_state=$(/bin/busybox cat "$observer_device_path/state")
		observer_snapshots_sentinel=$(/bin/busybox printf '\001')
		observer_snapshots_capture=$(
			/bin/busybox cat "$observer_device_path/snapshots"
			/bin/busybox printf '\001'
		)
		case "$observer_snapshots_capture" in
		*"$observer_snapshots_sentinel")
			observer_snapshots=${observer_snapshots_capture%"$observer_snapshots_sentinel"}
			observer_snapshots_capture_ok=1
			;;
		*)
			observer_snapshots=
			;;
		esac
		observer_snapshots_hex=$(printf '%s' "$observer_snapshots" | \
			/bin/busybox hexdump -v -e '1/1 "%02x"')
		observer_snapshots_sha256=$(printf '%s' "$observer_snapshots" | \
			/bin/busybox sha256sum | /bin/busybox awk '{ print $1 }')
		observer_snapshot_line_count=$(printf '%s' \
			"$observer_snapshots" | /bin/busybox grep -c '^snapshot=' || true)
		observer_state_mode=$(/bin/busybox stat -c '%a' \
			"$observer_device_path/state")
		observer_state_uid=$(/bin/busybox stat -c '%u' \
			"$observer_device_path/state")
		observer_state_gid=$(/bin/busybox stat -c '%g' \
			"$observer_device_path/state")
		observer_snapshots_mode=$(/bin/busybox stat -c '%a' \
			"$observer_device_path/snapshots")
		observer_snapshots_uid=$(/bin/busybox stat -c '%u' \
			"$observer_device_path/snapshots")
		observer_snapshots_gid=$(/bin/busybox stat -c '%g' \
			"$observer_device_path/snapshots")
	fi
	printf 'observer_state=%s\n' "$observer_state"
	printf 'observer_snapshots_hex=%s\n' "$observer_snapshots_hex"
	printf 'observer_snapshots_sha256=%s\n' "$observer_snapshots_sha256"
	printf 'observer_snapshot_line_count=%s\n' \
		"$observer_snapshot_line_count"
	printf 'observer_state_mode=%s\n' "$observer_state_mode"
	printf 'observer_state_uid=%s\n' "$observer_state_uid"
	printf 'observer_state_gid=%s\n' "$observer_state_gid"
	printf 'observer_snapshots_mode=%s\n' "$observer_snapshots_mode"
	printf 'observer_snapshots_uid=%s\n' "$observer_snapshots_uid"
	printf 'observer_snapshots_gid=%s\n' "$observer_snapshots_gid"
	printf 'observer_snapshots_capture_ok=%s\n' \
		"$observer_snapshots_capture_ok"
	observer_probe_logs=$(/bin/busybox dmesg | \
		/bin/busybox grep '11015000.dvfsp-observer:' || true)
	observer_probe_log_line_count=$(printf '%s\n' \
		"$observer_probe_logs" | /bin/busybox awk \
		'NF { count++ } END { print count + 0 }')
	observer_probe_log_sha256=$(printf '%s\n' "$observer_probe_logs" | \
		/bin/busybox sha256sum | /bin/busybox awk '{ print $1 }')
	printf 'observer_probe_log_line_count=%s\n' \
		"$observer_probe_log_line_count"
	printf 'observer_probe_log_sha256=%s\n' "$observer_probe_log_sha256"

	i2c6_node=$dt_root/i2c@1100e000
	i2c6_node_canonical=$(/bin/busybox readlink -f "$i2c6_node" \
		2>/dev/null || true)
	[ ! -d "$i2c6_node" ] || printf 'i2c6_dt_node_present=1\n'
	[ -d "$i2c6_node" ] || printf 'i2c6_dt_node_present=0\n'
	printf 'i2c6_status_hex='
	property_hex "$i2c6_node/status"
	printf '\n'
	i2c6_child_count=0
	for node in "$i2c6_node"/*; do
		[ -d "$node" ] || continue
		i2c6_child_count=$((i2c6_child_count + 1))
	done
	printf 'i2c6_child_count=%s\n' "$i2c6_child_count"
	i2c6_platform_count=0
	for device in /sys/bus/platform/devices/*; do
		[ -d "$device" ] || continue
		node=$(/bin/busybox readlink -f "$device/of_node" 2>/dev/null || true)
		[ "${node##*/}" != i2c@1100e000 ] || \
			i2c6_platform_count=$((i2c6_platform_count + 1))
	done
	printf 'i2c6_platform_count=%s\n' "$i2c6_platform_count"
	i2c6_adapter_count=0
	i2c6_adapter=unavailable
	for adapter in /sys/class/i2c-adapter/i2c-*; do
		[ -d "$adapter" ] || continue
		node=$(/bin/busybox readlink -f "$adapter/of_node" \
			2>/dev/null || true)
		if [ -n "$i2c6_node_canonical" ] && \
		   [ "$node" = "$i2c6_node_canonical" ]; then
			i2c6_adapter_count=$((i2c6_adapter_count + 1))
			i2c6_adapter=${adapter##*/i2c-}
		fi
	done
	printf 'i2c6_adapter_count=%s\n' "$i2c6_adapter_count"
	printf 'i2c6_adapter=%s\n' "$i2c6_adapter"
	i2c6_client_count=0
	if [ "$i2c6_adapter_count" -eq 1 ]; then
		for client in /sys/bus/i2c/devices/"$i2c6_adapter"-*; do
			[ -d "$client" ] || continue
			i2c6_client_count=$((i2c6_client_count + 1))
		done
	fi
	printf 'i2c6_client_count=%s\n' "$i2c6_client_count"
	i2c6_regulator_count=0
	if [ -n "$i2c6_node_canonical" ]; then
		for regulator in /sys/class/regulator/regulator.*; do
			[ -d "$regulator" ] || continue
			node=$(/bin/busybox readlink -f \
				"$regulator/device/of_node" 2>/dev/null || true)
			case "$node" in
			"$i2c6_node_canonical"/*)
				i2c6_regulator_count=$((i2c6_regulator_count + 1))
				;;
			esac
		done
	fi
	printf 'i2c6_regulator_count=%s\n' "$i2c6_regulator_count"
	address_0068_client_count=0
	address_0068_bound_driver_count=0
	for client in /sys/bus/i2c/devices/*-0068; do
		[ -d "$client" ] || continue
		address_0068_client_count=$((address_0068_client_count + 1))
		[ ! -L "$client/driver" ] || \
			address_0068_bound_driver_count=$((address_0068_bound_driver_count + 1))
	done
	printf 'address_0068_client_count=%s\n' \
		"$address_0068_client_count"
	printf 'address_0068_bound_driver_count=%s\n' \
		"$address_0068_bound_driver_count"
	address_0068_regulator_count=0
	for regulator in /sys/class/regulator/regulator.*; do
		[ -d "$regulator" ] || continue
		device=$(/bin/busybox readlink -f "$regulator/device" \
			2>/dev/null || true)
		case "$device" in
		*/[0-9]*-0068/*)
			address_0068_regulator_count=$((address_0068_regulator_count + 1))
			;;
		esac
	done
	printf 'address_0068_regulator_count=%s\n' \
		"$address_0068_regulator_count"
	da9214_live_client_count=0
	for client in /sys/bus/i2c/devices/*-0068; do
		[ -d "$client" ] || continue
		node=$(/bin/busybox readlink -f "$client/of_node" \
			2>/dev/null || true)
		compatible=$(property_hex "$node/compatible")
		[ "$compatible" != 646c672c64613932313400 ] || \
			da9214_live_client_count=$((da9214_live_client_count + 1))
	done
	printf 'da9214_live_client_count=%s\n' "$da9214_live_client_count"
	printf 'da9214_dt_count='
	compatible_count 646c672c64613932313400
	printf '\n'
	if [ -d "$i2c6_node/regulator@68" ]; then
		printf 'da9214_named_node_present=1\n'
	else
		printf 'da9214_named_node_present=0\n'
	fi
	printf 'a72_power_dt_count='
	compatible_count \
		6d6564696174656b2c6d74363739372d6137322d706f77657200
	printf '\n'
	if [ -d "$dt_root/a72-power@10222000" ]; then
		printf 'a72_power_named_node_present=1\n'
	else
		printf 'a72_power_named_node_present=0\n'
	fi

	aw_node=$dt_root/i2c@1101c000/gpio-expander@5b
	printf 'aw9523_compatible_hex='
	property_hex "$aw_node/compatible"
	printf '\n'
	printf 'aw9523_status_hex='
	property_hex "$aw_node/status"
	printf '\n'
	aw9523_client_count=0
	aw9523_driver=unavailable
	for client in /sys/bus/i2c/devices/*-005b; do
		[ -d "$client" ] || continue
		aw9523_client_count=$((aw9523_client_count + 1))
		if [ -L "$client/driver" ]; then
			aw9523_driver=$(/bin/busybox basename \
				"$(/bin/busybox readlink -f "$client/driver")")
		else
			aw9523_driver=unbound
		fi
	done
	printf 'aw9523_client_count=%s\n' "$aw9523_client_count"
	printf 'aw9523_driver=%s\n' "$aw9523_driver"

	matrix_node=$dt_root/keyboard-matrix
	matrix_device=/sys/bus/platform/devices/keyboard-matrix
	printf 'matrix_compatible_hex='
	property_hex "$matrix_node/compatible"
	printf '\n'
	printf 'matrix_status_hex='
	property_hex "$matrix_node/status"
	printf '\n'
	printf 'matrix_poll_interval_hex='
	property_hex "$matrix_node/poll-interval"
	printf '\n'
	printf 'matrix_col_scan_delay_hex='
	property_hex "$matrix_node/col-scan-delay-us"
	printf '\n'
	[ ! -d "$matrix_device" ] || printf 'matrix_device_present=1\n'
	[ -d "$matrix_device" ] || printf 'matrix_device_present=0\n'
	if [ -L "$matrix_device/driver" ]; then
		printf 'matrix_driver='
		/bin/busybox basename \
			"$(/bin/busybox readlink -f "$matrix_device/driver")"
	else
		printf 'matrix_driver=unbound\n'
	fi
	matrix_event_count=0
	matrix_event_node=unavailable
	for event in /sys/class/input/event*; do
		[ -d "$event" ] || continue
		name=$(/bin/busybox cat "$event/device/name" 2>/dev/null || true)
		[ "$name" != keyboard-matrix ] || {
			matrix_event_count=$((matrix_event_count + 1))
			matrix_event_node=/dev/input/${event##*/}
		}
	done
	printf 'matrix_event_count=%s\n' "$matrix_event_count"
	printf 'matrix_event_node=%s\n' "$matrix_event_node"
	if [ -c "$matrix_event_node" ]; then
		printf 'matrix_event_char_device=1\n'
	else
		printf 'matrix_event_char_device=0\n'
	fi

	keymap_output=$(/bin/console-keymap-verify \
		--verify /etc/gemini-us.bkeymap 2>&1)
	keymap_rc=$?
	printf 'keymap_verify_rc=%s\n' "$keymap_rc"
	printf 'keymap_verify_output_hex='
	printf '%s' "$keymap_output" | \
		/bin/busybox hexdump -v -e '1/1 "%02x"'
	printf '\n'
	keymap_ready_count=$(/bin/busybox grep -c \
		'keyboard_map=loaded.*sha256=02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c.*tty1_shell=ready.*prompt=GEMINI-AB#.*reboot_dispatch=validated' \
		/run/x-status 2>/dev/null || true)
	printf 'keymap_ready_count=%s\n' "$keymap_ready_count"

	usb0_count=0
	for netdev in /sys/class/net/usb0; do
		[ -d "$netdev" ] || continue
		usb0_count=$((usb0_count + 1))
	done
	printf 'usb0_count=%s\n' "$usb0_count"
	printf 'usb0_address='
	/bin/busybox cat /sys/class/net/usb0/address 2>/dev/null || \
		printf 'unavailable\n'
	printf 'usb0_carrier='
	/bin/busybox cat /sys/class/net/usb0/carrier 2>/dev/null || \
		printf 'unavailable\n'
	printf 'usb0_operstate='
	/bin/busybox cat /sys/class/net/usb0/operstate 2>/dev/null || \
		printf 'unavailable\n'
	usb0_ipv4_total=$(/bin/busybox ip -o -4 address show dev usb0 \
		2>/dev/null | /bin/busybox awk 'END { print NR + 0 }')
	usb0_ipv4_exact=$(/bin/busybox ip -o -4 address show dev usb0 \
		2>/dev/null | /bin/busybox awk \
		'$4 == "10.15.19.82/24" { found++ } END { print found + 0 }')
	printf 'usb0_ipv4_total=%s\n' "$usb0_ipv4_total"
	printf 'usb0_ipv4_exact=%s\n' "$usb0_ipv4_exact"
	udc_count=0
	udc_name=unavailable
	udc_state=unavailable
	for udc in /sys/class/udc/*; do
		[ -d "$udc" ] || continue
		udc_count=$((udc_count + 1))
		udc_name=${udc##*/}
		udc_state=$(/bin/busybox cat "$udc/state" 2>/dev/null || true)
	done
	printf 'udc_count=%s\n' "$udc_count"
	printf 'udc_name=%s\n' "$udc_name"
	printf 'udc_state=%s\n' "$udc_state"
	ac_service_count=$(/bin/busybox grep -c \
		'service=nc status=listening address=10.15.19.82 port=2323 shell=/bin/usb-shell authentication=none encryption=none direct_link_only=yes' \
		/run/ac-status 2>/dev/null || true)
	ac_ready_count=$(/bin/busybox grep -c \
		'usb_shell=ready reboot_dispatch=validated privilege=root authentication=none encryption=none direct_link_only=yes' \
		/run/ac-status 2>/dev/null || true)
	printf 'ac_service_count=%s\n' "$ac_service_count"
	printf 'ac_ready_count=%s\n' "$ac_ready_count"

	watchdog_fd_count=0
	for descriptor in /proc/[0-9]*/fd/*; do
		[ -L "$descriptor" ] || continue
		target=$(/bin/busybox readlink "$descriptor" 2>/dev/null || true)
		case "$target" in
		/dev/watchdog*)
			watchdog_fd_count=$((watchdog_fd_count + 1))
			;;
		esac
	done
	printf 'watchdog_fd_count=%s\n' "$watchdog_fd_count"
	printf 'boot_id='
	/bin/busybox cat /proc/sys/kernel/random/boot_id
	printf 'uptime_seconds='
	/bin/busybox cut -d. -f1 /proc/uptime
	printf 'online='
	/bin/busybox cat /sys/devices/system/cpu/online
	printf 'offline='
	/bin/busybox cat /sys/devices/system/cpu/offline
}

printf '__AN_IDENTITY_BEGIN__\n'
printf 'boot_id='
/bin/busybox cat /proc/sys/kernel/random/boot_id
printf 'uptime_seconds='
/bin/busybox cut -d. -f1 /proc/uptime
printf 'cmdline='
/bin/busybox cat /proc/cmdline
printf 'possible='
/bin/busybox cat /sys/devices/system/cpu/possible
printf 'present='
/bin/busybox cat /sys/devices/system/cpu/present
printf 'online='
/bin/busybox cat /sys/devices/system/cpu/online
printf 'offline='
/bin/busybox cat /sys/devices/system/cpu/offline
printf 'nproc='
/bin/busybox nproc
printf 'kernel='
/bin/busybox uname -r
printf 'config_sha256='
/bin/busybox zcat /proc/config.gz | /bin/busybox sha256sum | \
	/bin/busybox awk '{ print $1 }'
printf 'config_cmdline='
/bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_CMDLINE='
printf 'config_force='
/bin/busybox zcat /proc/config.gz | \
	/bin/busybox grep '^CONFIG_CMDLINE_FORCE='
printf 'config_a72_observer='
/bin/busybox zcat /proc/config.gz | \
	/bin/busybox grep '^CONFIG_MTK_MT6797_A72_POWER='
printf 'config_dvfsp_observer='
/bin/busybox zcat /proc/config.gz | \
	/bin/busybox grep '^CONFIG_MTK_MT6797_DVFSP_HANDOFF_OBSERVER='
printf 'config_da9211='
/bin/busybox zcat /proc/config.gz | \
	/bin/busybox grep '^CONFIG_REGULATOR_DA9211='
printf 'config_simplefb='
/bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_FB_SIMPLE='
printf 'config_aw9523='
/bin/busybox zcat /proc/config.gz | \
	/bin/busybox grep '^CONFIG_PINCTRL_AW9523='
printf 'config_matrix='
/bin/busybox zcat /proc/config.gz | \
	/bin/busybox grep '^CONFIG_KEYBOARD_MATRIX='
printf 'cpu8_enable_method='
/bin/busybox tr -d '\000' \
	</sys/firmware/devicetree/base/cpus/cpu@200/enable-method
printf '\n'
printf 'cpu9_enable_method='
/bin/busybox tr -d '\000' \
	</sys/firmware/devicetree/base/cpus/cpu@201/enable-method
printf '\n'
printf 'init_sha256='
file_sha256 /init
printf '\n'
printf 'busybox_sha256='
file_sha256 /bin/busybox
printf '\n'
printf 'ac_record_sha256='
file_sha256 /bin/ac-record
printf '\n'
printf 'usb_net_sha256='
file_sha256 /bin/usb-net
printf '\n'
printf 'usb_shell_sha256='
file_sha256 /bin/usb-shell
printf '\n'
printf 'local_shell_sha256='
file_sha256 /bin/local-shell
printf '\n'
printf 'reboot_sha256='
file_sha256 /bin/reboot
printf '\n'
printf 'keymap_sha256='
file_sha256 /etc/gemini-us.bkeymap
printf '\n'
printf 'keymap_verifier_sha256='
file_sha256 /bin/console-keymap-verify
printf '\n'
printf 'unicode_helper_sha256='
file_sha256 /bin/console-unicode-mode
printf '\n'
printf 'input_helper_sha256='
file_sha256 /bin/input-event-capture
printf '\n'
printf '__AN_IDENTITY_END__\n'

printf '__AN_STATE1_BEGIN__\n'
read_state
printf '__AN_STATE1_END__\n'
printf '__AN_STAT1_BEGIN__\n'
/bin/busybox grep '^cpu[0-9]' /proc/stat
printf '__AN_STAT1_END__\n'
/bin/busybox sleep 5
printf '__AN_STATE2_BEGIN__\n'
read_state
printf '__AN_STATE2_END__\n'
printf '__AN_STAT2_BEGIN__\n'
/bin/busybox grep '^cpu[0-9]' /proc/stat
printf '__AN_STAT2_END__\n'
printf '__AN_DMESG_BEGIN__\n'
/bin/busybox dmesg
printf '__AN_DMESG_END__\n'
exit
__AN_REMOTE_SCRIPT__
exit
EOF

{
	printf '__AN_HOST_BEGIN__\n'
	printf 'installed_full_sha256_input=%s\n' "$installed_full_sha256"
	printf 'attestation_basis=caller-supplied-prior-full-partition-readback\n'
	printf 'device_partition_read_during_collection=no\n'
	printf 'observer_access_path=platform-device-read-only-sysfs\n'
	printf 'i2c_transaction_or_controller_control=none\n'
	printf 'regulator_control_or_value_read=none\n'
	printf 'cpu_online_control_access=none\n'
	printf 'watchdog_control_access=none\n'
	printf 'reboot_executed=no\n'
	printf 'keymap_helper_tty_open_mode=O_RDWR\n'
	printf 'keymap_helper_ioctl_scope=KDGKBMODE-plus-KDGKBENT-readback-only\n'
	printf 'keymap_helper_mutating_ioctl=none\n'
	printf 'interface=%s\n' "$interface"
	printf 'mac=%s\n' "$mac"
	printf 'host_address=%s\n' "$HOST_ADDRESS"
	printf 'route_interface=%s\n' "$route_interface"
	printf '__AN_HOST_END__\n'
} >"$output"
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 90 \
	"$DEVICE_ADDRESS" 2323 <"$command_file" >>"$output"
python3 "$script_dir/validate-runtime.py" \
	--capture "$output" \
	--expected-installed-full-sha256 "$installed_full_sha256"
printf 'capture=%s\n' "$output"
