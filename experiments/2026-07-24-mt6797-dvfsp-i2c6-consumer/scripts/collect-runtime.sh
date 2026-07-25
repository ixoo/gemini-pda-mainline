#!/usr/bin/env bash

# Collect Candidate AP's handoff-gated, childless I2C6 publication over the inherited
# USB-only development shell. The remote script performs read-only observation:
# it never reads a partition, operates I2C/regulators/CPU hotplug, arms a
# watchdog, or requests reboot. The keymap verifier opens tty1 O_RDWR but uses
# only KDGKBMODE/KDGKBENT readback ioctls.

set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_MAC=42:00:15:19:82:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() {
	printf 'usage: %s --interface IFACE --output FILE --installed-full-sha256 SHA256 --expected-config-sha256 SHA256 --expected-live-fdt-sha256 SHA256 --expected-boot-id UUID\n' "$0" >&2
}

interface=
output=
installed_full_sha256=
expected_config_sha256=
expected_live_fdt_sha256=
expected_boot_id=
while (($#)); do
	case "$1" in
	--interface|--output|--installed-full-sha256|--expected-config-sha256|--expected-live-fdt-sha256|--expected-boot-id)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in
		--interface) [[ -z "$interface" ]] || die "$1 duplicated"; interface=$2 ;;
		--output) [[ -z "$output" ]] || die "$1 duplicated"; output=$2 ;;
		--installed-full-sha256)
			[[ -z "$installed_full_sha256" ]] || die "$1 duplicated"
			installed_full_sha256=$2
			;;
		--expected-config-sha256)
			[[ -z "$expected_config_sha256" ]] || die "$1 duplicated"
			expected_config_sha256=$2
			;;
		--expected-live-fdt-sha256)
			[[ -z "$expected_live_fdt_sha256" ]] || die "$1 duplicated"
			expected_live_fdt_sha256=$2
			;;
		--expected-boot-id)
			[[ -z "$expected_boot_id" ]] || die "$1 duplicated"
			expected_boot_id=$2
			;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$interface" =~ ^[A-Za-z0-9]+$ && -n "$output" ]] || {
	usage
	exit 2
}
for value in "$installed_full_sha256" "$expected_config_sha256" \
	"$expected_live_fdt_sha256"; do
	[[ "$value" =~ ^[0-9a-f]{64}$ ]] || \
		die 'each expected identity must be one lowercase SHA-256 value'
done
[[ "$expected_boot_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$ ]] || \
	die 'expected boot ID must be one lowercase RFC 4122 UUID'
[[ ! -e "$output" && ! -L "$output" ]] || \
	die 'refusing to overwrite runtime capture'
for command in awk dirname ifconfig mktemp nc ping python3 rm route; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
mac="$(ifconfig "$interface" | \
	awk '/^[[:space:]]*ether / { print tolower($2); exit }')"
[[ "$mac" == "$HOST_MAC" ]] || die "interface $interface is not the Gemini USB MAC"
ifconfig "$interface" | awk -v address="$HOST_ADDRESS" \
	'$1 == "inet" && $2 == address { found = 1 } END { exit !found }' || \
	die 'host USB address is absent'
route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | \
	awk '$1 == "interface:" { print $2; count++ } END { exit count != 1 }')"
[[ "$route_interface" == "$interface" ]] || \
	die 'device route is not the exact Gemini interface'
ping -b "$interface" -c 3 -S "$HOST_ADDRESS" "$DEVICE_ADDRESS" >/dev/null || \
	die 'bounded USB ping failed'

command_file="$(mktemp /tmp/candidate-ap-runtime-command.XXXXXX)"
cleanup() { [[ ! -f "$command_file" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
cat >"$command_file" <<'EOF'
/bin/busybox sh <<'__AP_REMOTE_SCRIPT__'
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
		[ "$(property_hex "$property")" != "$wanted" ] || count=$((count + 1))
	done
	printf '%s' "$count"
}
config_flag() {
	if /bin/busybox zcat /proc/config.gz | \
	   /bin/busybox grep -q "^$1=y$"; then
		printf 'y'
	else
		printf 'n'
	fi
}

handoff=/sys/bus/platform/devices/11015000.dvfsp-handoff
i2c6_device=/sys/bus/platform/devices/1100e000.i2c
deadline=$(( $(/bin/busybox cut -d. -f1 /proc/uptime) + 80 ))
while :; do
	state=$(/bin/busybox cat "$handoff/state" 2>/dev/null || true)
	case "$state" in
	ready)
		[ ! -f "$i2c6_device/handoff_status" ] || break
		;;
	inconclusive)
		/bin/busybox dmesg | /bin/busybox grep -q \
			'GEMINI_MT6797_I2C6_GUARD handoff=denied probe_attempts=1 reason=supplier-not-ready' && break
		;;
	faulted)
		break
		;;
	esac
	now=$(/bin/busybox cut -d. -f1 /proc/uptime)
	[ "$now" -lt "$deadline" ] || break
	/bin/busybox sleep 1
done

read_state() {
	dt=/sys/firmware/devicetree/base
	node=$dt/dvfsp-handoff@11015000
	i2c6=$dt/i2c@1100e000
	printf 'live_fdt_sha256='; file_sha256 /sys/firmware/fdt; printf '\n'
	printf 'live_fdt_size='
	/bin/busybox stat -c '%s' /sys/firmware/fdt 2>/dev/null || printf 'missing\n'
	printf 'handoff_dt_count='
	compatible_count 6d6564696174656b2c6d74363739372d64766673702d68616e646f666600
	printf '\n'
	[ ! -d "$node" ] || printf 'handoff_dt_node_present=1\n'
	[ -d "$node" ] || printf 'handoff_dt_node_present=0\n'
	printf 'handoff_compatible_hex='; property_hex "$node/compatible"; printf '\n'
	printf 'handoff_reg_hex='; property_hex "$node/reg"; printf '\n'
	printf 'handoff_clocks_hex='; property_hex "$node/clocks"; printf '\n'
	printf 'handoff_clock_names_hex='; property_hex "$node/clock-names"; printf '\n'
	printf 'handoff_infracfg_hex='
	property_hex "$node/mediatek,infracfg"
	printf '\n'
	printf 'handoff_status_hex='; property_hex "$node/status"; printf '\n'
	printf 'handoff_access_controller_cells_hex='
	property_hex "$node/#access-controller-cells"
	printf '\n'
	printf 'handoff_phandle_hex='; property_hex "$node/phandle"; printf '\n'

	node_canonical=$(/bin/busybox readlink -f "$node" 2>/dev/null || true)
	platform_count=0
	for device in /sys/bus/platform/devices/*; do
		[ -d "$device" ] || continue
		[ "$(/bin/busybox readlink -f "$device/of_node" 2>/dev/null || true)" \
			!= "$node_canonical" ] || platform_count=$((platform_count + 1))
	done
	printf 'handoff_platform_count=%s\n' "$platform_count"
	printf 'handoff_device=11015000.dvfsp-handoff\n'
	if [ -L "$handoff/driver" ]; then
		printf 'handoff_driver='
		/bin/busybox basename "$(/bin/busybox readlink -f "$handoff/driver")"
		printf 'handoff_driver_is_symlink=1\n'
		printf 'handoff_driver_target=%s\n' \
			"$(/bin/busybox readlink -f "$handoff/driver")"
	else
		printf 'handoff_driver=unbound\n'
		printf 'handoff_driver_is_symlink=0\n'
		printf 'handoff_driver_target=unavailable\n'
	fi
	if [ -L "$handoff/of_node" ]; then
		printf 'handoff_of_node_is_symlink=1\n'
		printf 'handoff_of_node_target=%s\n' \
			"$(/bin/busybox readlink -f "$handoff/of_node")"
	else
		printf 'handoff_of_node_is_symlink=0\n'
		printf 'handoff_of_node_target=unavailable\n'
	fi
	[ ! -d /sys/bus/platform/drivers/mt6797-dvfsp-handoff ] || \
		printf 'handoff_driver_present=1\n'
	[ -d /sys/bus/platform/drivers/mt6797-dvfsp-handoff ] || \
		printf 'handoff_driver_present=0\n'
	[ ! -e /sys/bus/platform/drivers/mt6797-dvfsp-handoff/bind ] || \
		printf 'handoff_bind_present=1\n'
	[ -e /sys/bus/platform/drivers/mt6797-dvfsp-handoff/bind ] || \
		printf 'handoff_bind_present=0\n'
	[ ! -e /sys/bus/platform/drivers/mt6797-dvfsp-handoff/unbind ] || \
		printf 'handoff_unbind_present=1\n'
	[ -e /sys/bus/platform/drivers/mt6797-dvfsp-handoff/unbind ] || \
		printf 'handoff_unbind_present=0\n'
	printf 'handoff_state='
	/bin/busybox cat "$handoff/state" 2>/dev/null || true
	printf '\n'
	printf 'handoff_status='
	/bin/busybox cat "$handoff/status" 2>/dev/null || true
	printf '\n'
	printf 'handoff_snapshots_hex='
	/bin/busybox hexdump -v -e '1/1 "%02x"' "$handoff/snapshots" 2>/dev/null
	printf '\n'
	printf 'handoff_snapshots_sha256='
	file_sha256 "$handoff/snapshots"
	printf '\n'
	printf 'handoff_snapshot_line_count='
	/bin/busybox grep -c '^sample=' "$handoff/snapshots" 2>/dev/null || printf '0\n'
	printf 'handoff_consumer_cleanup_hex='
	/bin/busybox hexdump -v -e '1/1 "%02x"' \
		"$handoff/consumer_cleanup" 2>/dev/null
	printf '\n'
	printf 'handoff_consumer_cleanup_sha256='
	file_sha256 "$handoff/consumer_cleanup"
	printf '\n'
	printf 'handoff_consumer_cleanup_line_count='
	/bin/busybox awk \
		'/^i=/ { count++ } END { print count + 0 }' \
		"$handoff/consumer_cleanup" 2>/dev/null
	for attribute in state status snapshots consumer_cleanup; do
		printf 'handoff_%s_mode=' "$attribute"
		/bin/busybox stat -c '%a' "$handoff/$attribute" 2>/dev/null || printf 'missing\n'
		printf 'handoff_%s_uid=' "$attribute"
		/bin/busybox stat -c '%u' "$handoff/$attribute" 2>/dev/null || printf 'missing\n'
		printf 'handoff_%s_gid=' "$attribute"
		/bin/busybox stat -c '%g' "$handoff/$attribute" 2>/dev/null || printf 'missing\n'
	done

	[ ! -d "$i2c6" ] || printf 'i2c6_dt_node_present=1\n'
	[ -d "$i2c6" ] || printf 'i2c6_dt_node_present=0\n'
	printf 'i2c6_status_hex='; property_hex "$i2c6/status"; printf '\n'
	printf 'i2c6_access_controllers_hex='
	property_hex "$i2c6/access-controllers"
	printf '\n'
	count=0
	for child in "$i2c6"/*; do [ ! -d "$child" ] || count=$((count + 1)); done
	printf 'i2c6_child_count=%s\n' "$count"
	i2c6_canonical=$(/bin/busybox readlink -f "$i2c6" 2>/dev/null || true)
	platform_count=0
	for device in /sys/bus/platform/devices/*; do
		[ -d "$device" ] || continue
		[ "$(/bin/busybox readlink -f "$device/of_node" 2>/dev/null || true)" \
			!= "$i2c6_canonical" ] || platform_count=$((platform_count + 1))
	done
	printf 'i2c6_platform_count=%s\n' "$platform_count"
	if [ -L "$i2c6_device/driver" ]; then
		printf 'i2c6_driver='
		/bin/busybox basename "$(/bin/busybox readlink -f "$i2c6_device/driver")"
	else
		printf 'i2c6_driver=unbound\n'
	fi
	handoff_canonical=$(/bin/busybox readlink -f "$handoff" 2>/dev/null || true)
	i2c6_device_canonical=$(
		/bin/busybox readlink -f "$i2c6_device" 2>/dev/null || true
	)
	printf 'handoff_device_canonical=%s\n' "$handoff_canonical"
	printf 'i2c6_device_canonical=%s\n' "$i2c6_device_canonical"
	link_count=0
	link_status=missing
	link_auto_remove_on=missing
	link_runtime_pm=missing
	link_sync_state_only=missing
	link_inferred_attr_present=missing
	link_consumer_target=missing
	link_supplier_target=missing
	for class_link in /sys/class/devlink/*; do
		[ -L "$class_link" ] || continue
		link=$(/bin/busybox readlink -f "$class_link" 2>/dev/null || true)
		[ -d "$link" ] || continue
		[ "$(/bin/busybox readlink -f "$link/consumer" 2>/dev/null || true)" \
			= "$i2c6_device_canonical" ] || continue
		[ "$(/bin/busybox readlink -f "$link/supplier" 2>/dev/null || true)" \
			= "$handoff_canonical" ] || continue
		link_count=$((link_count + 1))
		link_status=$(/bin/busybox cat "$link/status" 2>/dev/null || printf missing)
		link_auto_remove_on=$(
			/bin/busybox cat "$link/auto_remove_on" 2>/dev/null || printf missing
		)
		link_runtime_pm=$(
			/bin/busybox cat "$link/runtime_pm" 2>/dev/null || printf missing
		)
		link_sync_state_only=$(
			/bin/busybox cat "$link/sync_state_only" 2>/dev/null || printf missing
		)
		if [ -e "$link/inferred" ]; then
			link_inferred_attr_present=1
		else
			link_inferred_attr_present=0
		fi
		link_consumer_target=$(
			/bin/busybox readlink -f "$link/consumer" 2>/dev/null || printf missing
		)
		link_supplier_target=$(
			/bin/busybox readlink -f "$link/supplier" 2>/dev/null || printf missing
		)
	done
	printf 'i2c6_handoff_link_count=%s\n' "$link_count"
	printf 'i2c6_handoff_link_status=%s\n' "$link_status"
	printf 'i2c6_handoff_link_auto_remove_on=%s\n' "$link_auto_remove_on"
	printf 'i2c6_handoff_link_runtime_pm=%s\n' "$link_runtime_pm"
	printf 'i2c6_handoff_link_sync_state_only=%s\n' "$link_sync_state_only"
	printf 'i2c6_handoff_link_inferred_attr_present=%s\n' \
		"$link_inferred_attr_present"
	printf 'i2c6_handoff_link_consumer_target=%s\n' "$link_consumer_target"
	printf 'i2c6_handoff_link_supplier_target=%s\n' "$link_supplier_target"
	printf 'i2c6_handoff_status='
	/bin/busybox cat "$i2c6_device/handoff_status" 2>/dev/null || true
	printf '\n'
	printf 'i2c6_handoff_status_mode='
	/bin/busybox stat -c '%a' "$i2c6_device/handoff_status" 2>/dev/null || \
		printf 'missing\n'
	printf 'i2c6_handoff_status_uid='
	/bin/busybox stat -c '%u' "$i2c6_device/handoff_status" 2>/dev/null || \
		printf 'missing\n'
	printf 'i2c6_handoff_status_gid='
	/bin/busybox stat -c '%g' "$i2c6_device/handoff_status" 2>/dev/null || \
		printf 'missing\n'
	adapter_count=0
	adapter_id=
	for adapter in /sys/class/i2c-adapter/i2c-*; do
		[ -d "$adapter" ] || continue
		if [ "$(/bin/busybox readlink -f "$adapter/of_node" 2>/dev/null || true)" \
		     = "$i2c6_canonical" ]; then
			adapter_count=$((adapter_count + 1))
			adapter_id=${adapter##*/i2c-}
		fi
	done
	printf 'i2c6_adapter_count=%s\n' "$adapter_count"
	client_count=0
	if [ "$adapter_count" -eq 1 ]; then
		for client in /sys/bus/i2c/devices/"$adapter_id"-*; do
			[ ! -d "$client" ] || client_count=$((client_count + 1))
		done
	fi
	printf 'i2c6_client_count=%s\n' "$client_count"
	regulator_count=0
	for regulator in /sys/class/regulator/regulator.*; do
		[ -d "$regulator" ] || continue
		reg_node=$(/bin/busybox readlink -f "$regulator/device/of_node" 2>/dev/null || true)
		case "$reg_node" in "$i2c6_canonical"/*) regulator_count=$((regulator_count + 1));; esac
	done
	printf 'i2c6_regulator_count=%s\n' "$regulator_count"
	address_count=0
	bound_count=0
	address_regulators=0
	for client in /sys/bus/i2c/devices/*-0068; do
		[ -d "$client" ] || continue
		address_count=$((address_count + 1))
		[ ! -L "$client/driver" ] || bound_count=$((bound_count + 1))
	done
	for regulator in /sys/class/regulator/regulator.*; do
		[ -d "$regulator" ] || continue
		case "$(/bin/busybox readlink -f "$regulator/device" 2>/dev/null || true)" in
		*/[0-9]*-0068/*) address_regulators=$((address_regulators + 1));;
		esac
	done
	printf 'address_0068_client_count=%s\n' "$address_count"
	printf 'address_0068_bound_driver_count=%s\n' "$bound_count"
	printf 'address_0068_regulator_count=%s\n' "$address_regulators"
	printf 'da9214_live_client_count=%s\n' "$address_count"
	printf 'da9214_dt_count='; compatible_count 646c672c64613932313400; printf '\n'
	[ ! -d "$i2c6/regulator@68" ] || printf 'da9214_named_node_present=1\n'
	[ -d "$i2c6/regulator@68" ] || printf 'da9214_named_node_present=0\n'
	printf 'a72_power_dt_count='
	compatible_count 6d6564696174656b2c6d74363739372d6137322d706f77657200
	printf '\n'
	[ ! -d "$dt/a72-power@10222000" ] || printf 'a72_power_named_node_present=1\n'
	[ -d "$dt/a72-power@10222000" ] || printf 'a72_power_named_node_present=0\n'

	fb=/sys/bus/platform/devices/7dfb0000.framebuffer
	printf 'simplefb_platform_count='
	if [ -d "$fb" ]; then printf '1\n'; else printf '0\n'; fi
	printf 'simplefb_platform_driver='
	if [ -L "$fb/driver" ]; then
		/bin/busybox basename "$(/bin/busybox readlink -f "$fb/driver")"
	else
		printf 'unbound\n'
	fi
	count=0
	for item in /sys/class/graphics/fb[0-9]*; do [ ! -d "$item" ] || count=$((count + 1)); done
	printf 'fb_count=%s\n' "$count"
	for property in name virtual_size bits_per_pixel stride; do
		printf 'fb0_%s=' "$property"
		/bin/busybox cat "/sys/class/graphics/fb0/$property" 2>/dev/null || printf 'unavailable\n'
	done
	if [ -c /dev/tty1 ]; then
		printf 'tty1_char_device=1\n'
	else
		printf 'tty1_char_device=0\n'
	fi
	printf 'tty1_shell_ready_count='
	/bin/busybox grep -c 'tty1_shell=ready' /run/x-status 2>/dev/null || printf '0\n'

	aw_count=0
	aw_driver=unavailable
	for client in /sys/bus/i2c/devices/*-005b; do
		[ -d "$client" ] || continue
		aw_count=$((aw_count + 1))
		[ ! -L "$client/driver" ] || aw_driver=$(/bin/busybox basename \
			"$(/bin/busybox readlink -f "$client/driver")")
	done
	printf 'aw9523_client_count=%s\n' "$aw_count"
	printf 'aw9523_driver=%s\n' "$aw_driver"
	matrix=/sys/bus/platform/devices/keyboard-matrix
	if [ -d "$matrix" ]; then
		printf 'matrix_device_present=1\n'
	else
		printf 'matrix_device_present=0\n'
	fi
	printf 'matrix_driver='
	if [ -L "$matrix/driver" ]; then
		/bin/busybox basename "$(/bin/busybox readlink -f "$matrix/driver")"
	else
		printf 'unbound\n'
	fi
	event_count=0
	event_node=unavailable
	for event in /sys/class/input/event*; do
		[ -d "$event" ] || continue
		if [ "$(/bin/busybox cat "$event/device/name" 2>/dev/null || true)" = keyboard-matrix ]; then
			event_count=$((event_count + 1))
			event_node=/dev/input/${event##*/}
		fi
	done
	printf 'matrix_event_count=%s\n' "$event_count"
	printf 'matrix_event_node=%s\n' "$event_node"
	if [ -c "$event_node" ]; then
		printf 'matrix_event_char_device=1\n'
	else
		printf 'matrix_event_char_device=0\n'
	fi
	keymap_output=$(/bin/console-keymap-verify --verify /etc/gemini-us.bkeymap 2>&1)
	keymap_rc=$?
	printf 'keymap_verify_rc=%s\n' "$keymap_rc"
	printf 'keymap_verify_output_hex='
	printf '%s' "$keymap_output" | /bin/busybox hexdump -v -e '1/1 "%02x"'
	printf '\n'
	printf 'keymap_ready_count='
	/bin/busybox grep -c 'keyboard_map=loaded.*reboot_dispatch=validated' \
		/run/x-status 2>/dev/null || printf '0\n'

	if [ -d /sys/class/net/usb0 ]; then
		printf 'usb0_count=1\n'
	else
		printf 'usb0_count=0\n'
	fi
	printf 'usb0_address='; /bin/busybox cat /sys/class/net/usb0/address 2>/dev/null || printf 'unavailable\n'
	printf 'usb0_carrier='; /bin/busybox cat /sys/class/net/usb0/carrier 2>/dev/null || printf 'unavailable\n'
	printf 'usb0_operstate='; /bin/busybox cat /sys/class/net/usb0/operstate 2>/dev/null || printf 'unavailable\n'
	printf 'usb0_ipv4_total='
	/bin/busybox ip -o -4 address show dev usb0 2>/dev/null | /bin/busybox awk 'END { print NR + 0 }'
	printf 'usb0_ipv4_exact='
	/bin/busybox ip -o -4 address show dev usb0 2>/dev/null | \
		/bin/busybox awk '$4 == "10.15.19.82/24" { n++ } END { print n + 0 }'
	udc_count=0
	udc_name=unavailable
	udc_state=unavailable
	for udc in /sys/class/udc/*; do
		[ -d "$udc" ] || continue
		udc_count=$((udc_count + 1)); udc_name=${udc##*/}
		udc_state=$(/bin/busybox cat "$udc/state" 2>/dev/null || true)
	done
	printf 'udc_count=%s\nudc_name=%s\nudc_state=%s\n' "$udc_count" "$udc_name" "$udc_state"
	printf 'ac_service_count='
	/bin/busybox grep -c 'service=nc status=listening' /run/ac-status 2>/dev/null || printf '0\n'
	printf 'ac_ready_count='
	/bin/busybox grep -c 'usb_shell=ready reboot_dispatch=validated' /run/ac-status 2>/dev/null || printf '0\n'
	watchdog_count=0
	for fd in /proc/[0-9]*/fd/*; do
		[ -L "$fd" ] || continue
		case "$(/bin/busybox readlink "$fd" 2>/dev/null || true)" in
		/dev/watchdog*) watchdog_count=$((watchdog_count + 1));;
		esac
	done
	printf 'watchdog_fd_count=%s\n' "$watchdog_count"
	printf 'boot_id='; /bin/busybox cat /proc/sys/kernel/random/boot_id
	printf 'uptime_seconds='; /bin/busybox cut -d. -f1 /proc/uptime
	printf 'online='; /bin/busybox cat /sys/devices/system/cpu/online
	printf 'offline='; /bin/busybox cat /sys/devices/system/cpu/offline
}

printf '__AP_IDENTITY_BEGIN__\n'
printf 'boot_id='; /bin/busybox cat /proc/sys/kernel/random/boot_id
printf 'uptime_seconds='; /bin/busybox cut -d. -f1 /proc/uptime
printf 'cmdline='; /bin/busybox cat /proc/cmdline
printf 'possible='; /bin/busybox cat /sys/devices/system/cpu/possible
printf 'present='; /bin/busybox cat /sys/devices/system/cpu/present
printf 'online='; /bin/busybox cat /sys/devices/system/cpu/online
printf 'offline='; /bin/busybox cat /sys/devices/system/cpu/offline
printf 'nproc='; /bin/busybox nproc
printf 'kernel='; /bin/busybox uname -r
printf 'config_sha256='
/bin/busybox zcat /proc/config.gz | /bin/busybox sha256sum | /bin/busybox awk '{ print $1 }'
printf 'config_cmdline='
/bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_CMDLINE='
for item in \
	config_force:CONFIG_CMDLINE_FORCE \
	config_a72_power:CONFIG_MTK_MT6797_A72_POWER \
	config_dvfsp_handoff:CONFIG_MTK_MT6797_DVFSP_HANDOFF \
	config_dvfsp_observer:CONFIG_MTK_MT6797_DVFSP_HANDOFF_OBSERVER \
	config_da9211:CONFIG_REGULATOR_DA9211 \
	config_simplefb:CONFIG_FB_SIMPLE \
	config_aw9523:CONFIG_PINCTRL_AW9523 \
	config_matrix:CONFIG_KEYBOARD_MATRIX \
	config_suspend:CONFIG_SUSPEND; do
	printf '%s=' "${item%%:*}"
	config_flag "${item#*:}"
	printf '\n'
done
printf 'cpu8_enable_method='
/bin/busybox tr -d '\000' </sys/firmware/devicetree/base/cpus/cpu@200/enable-method
printf '\ncpu9_enable_method='
/bin/busybox tr -d '\000' </sys/firmware/devicetree/base/cpus/cpu@201/enable-method
printf '\n'
for item in \
	init:/init busybox:/bin/busybox ac_record:/bin/ac-record \
	usb_net:/bin/usb-net usb_shell:/bin/usb-shell \
	local_shell:/bin/local-shell reboot:/bin/reboot \
	keymap:/etc/gemini-us.bkeymap \
	keymap_verifier:/bin/console-keymap-verify \
	unicode_helper:/bin/console-unicode-mode \
	input_helper:/bin/input-event-capture; do
	printf '%s_sha256=' "${item%%:*}"; file_sha256 "${item#*:}"; printf '\n'
done
printf '__AP_IDENTITY_END__\n'
printf '__AP_STATE1_BEGIN__\n'; read_state; printf '__AP_STATE1_END__\n'
printf '__AP_STAT1_BEGIN__\n'
/bin/busybox grep '^cpu[0-9]' /proc/stat
printf '__AP_STAT1_END__\n'
/bin/busybox sleep 5
printf '__AP_STATE2_BEGIN__\n'; read_state; printf '__AP_STATE2_END__\n'
printf '__AP_STAT2_BEGIN__\n'
/bin/busybox grep '^cpu[0-9]' /proc/stat
printf '__AP_STAT2_END__\n'
printf '__AP_DMESG_BEGIN__\n'; /bin/busybox dmesg; printf '__AP_DMESG_END__\n'
exit
__AP_REMOTE_SCRIPT__
exit
EOF

{
	printf '__AP_HOST_BEGIN__\n'
	printf 'installed_full_sha256_input=%s\n' "$installed_full_sha256"
	printf 'expected_boot_id_input=%s\n' "$expected_boot_id"
	printf 'attestation_basis=caller-supplied-prior-full-partition-readback\n'
	printf 'device_partition_read_during_collection=no\n'
	printf 'handoff_access_path=platform-device-read-only-sysfs\n'
	printf 'i2c_transaction_or_controller_control=none\n'
	printf 'regulator_control_or_value_read=none\n'
	printf 'cpu_online_control_access=none\n'
	printf 'watchdog_control_access=none\n'
	printf 'reboot_executed=no\n'
	printf 'power_state_transition_requested=no\n'
	printf 'keymap_helper_tty_open_mode=O_RDWR\n'
	printf 'keymap_helper_ioctl_scope=KDGKBMODE-plus-KDGKBENT-readback-only\n'
	printf 'keymap_helper_mutating_ioctl=none\n'
	printf 'interface=%s\nmac=%s\nhost_address=%s\nroute_interface=%s\n' \
		"$interface" "$mac" "$HOST_ADDRESS" "$route_interface"
	printf '__AP_HOST_END__\n'
} >"$output"
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 110 \
	"$DEVICE_ADDRESS" 2323 <"$command_file" >>"$output"
python3 "$script_dir/validate-runtime.py" \
	--capture "$output" \
	--expected-installed-full-sha256 "$installed_full_sha256" \
	--expected-config-sha256 "$expected_config_sha256" \
	--expected-live-fdt-sha256 "$expected_live_fdt_sha256" \
	--expected-boot-id "$expected_boot_id"
printf 'capture=%s\n' "$output"
