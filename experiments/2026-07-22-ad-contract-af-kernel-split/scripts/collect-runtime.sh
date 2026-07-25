#!/usr/bin/env bash

# Candidate AH keeps AF's exact kernel/configuration but restores AD's exact
# userspace and board contract, except for the two rejecting A72 methods.  This
# collector performs only bounded reads after the USB shell has authenticated
# the exact direct-link interface.

set -euo pipefail
export LC_ALL=C
umask 077

readonly HOST_MAC=42:00:15:19:82:00
readonly HOST_ADDRESS=10.15.19.1
readonly DEVICE_ADDRESS=10.15.19.82
readonly EXPECTED_INSTALLED_FULL_SHA256=f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012

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
		--interface) interface=$2 ;;
		--output) output=$2 ;;
		--installed-full-sha256) installed_full_sha256=$2 ;;
		esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done

[[ "$interface" =~ ^[A-Za-z0-9]+$ && -n "$output" ]] || { usage; exit 2; }
[[ "$installed_full_sha256" == "$EXPECTED_INSTALLED_FULL_SHA256" ]] || \
	die 'installed full-partition checksum is not the exact validated AH value'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite runtime capture'
for command in awk cat dirname ifconfig mktemp nc ping python3 rm route; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
mac="$(ifconfig "$interface" | awk '/^[[:space:]]*ether / { print tolower($2); exit }')"
[[ "$mac" == "$HOST_MAC" ]] || die "interface $interface is not the exact Gemini USB MAC"
ifconfig "$interface" | awk -v address="$HOST_ADDRESS" \
	'$1 == "inet" && $2 == address { found = 1 } END { exit !found }' || \
	die 'host USB address is absent'
route_interface="$(route -n get "$DEVICE_ADDRESS" 2>/dev/null | \
	awk '$1 == "interface:" { print $2; count++ } END { exit count != 1 }')"
[[ "$route_interface" == "$interface" ]] || die 'device route is not the exact Gemini interface'
ping -b "$interface" -c 3 -S "$HOST_ADDRESS" "$DEVICE_ADDRESS" >/dev/null || \
	die 'bounded USB ping failed'

command_file="$(mktemp /tmp/candidate-ah-runtime-command.XXXXXX)"
cleanup() { [[ ! -f "$command_file" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
cat >"$command_file" <<'EOF'
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

read_state() {
	chosen=/sys/firmware/devicetree/base/chosen
	simplefb_node=$chosen/framebuffer@7dfb0000
	reserved_root=/sys/firmware/devicetree/base/reserved-memory
	reserved_fb=$reserved_root/mblock-3-framebuffer
	platform_fb=/sys/bus/platform/devices/7dfb0000.framebuffer

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
	printf 'chosen_address_cells_hex='; property_hex "$chosen/#address-cells"; printf '\n'
	printf 'chosen_size_cells_hex='; property_hex "$chosen/#size-cells"; printf '\n'
	printf 'chosen_ranges_hex='; property_hex "$chosen/ranges"; printf '\n'
	printf 'simplefb_compatible_hex='; property_hex "$simplefb_node/compatible"; printf '\n'
	printf 'simplefb_reg_hex='; property_hex "$simplefb_node/reg"; printf '\n'
	printf 'simplefb_width_hex='; property_hex "$simplefb_node/width"; printf '\n'
	printf 'simplefb_height_hex='; property_hex "$simplefb_node/height"; printf '\n'
	printf 'simplefb_stride_hex='; property_hex "$simplefb_node/stride"; printf '\n'
	printf 'simplefb_format_hex='; property_hex "$simplefb_node/format"; printf '\n'
	printf 'simplefb_clocks_hex='; property_hex "$simplefb_node/clocks"; printf '\n'
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
	printf 'runtime_framebuffer_reservation_count=%s\n' "$runtime_framebuffer_reservation_count"
	[ ! -d "$reserved_fb" ] || printf 'runtime_framebuffer_reservation_present=1\n'
	[ -d "$reserved_fb" ] || printf 'runtime_framebuffer_reservation_present=0\n'
	printf 'runtime_framebuffer_compatible_hex='; property_hex "$reserved_fb/compatible"; printf '\n'
	printf 'runtime_framebuffer_reg_hex='; property_hex "$reserved_fb/reg"; printf '\n'
	if [ -e "$reserved_fb/no-map" ]; then
		printf 'runtime_framebuffer_no_map_present=1\n'
	else
		printf 'runtime_framebuffer_no_map_present=0\n'
	fi

	simplefb_platform_count=0
	for device in /sys/bus/platform/devices/*; do
		[ -d "$device" ] || continue
		node=$(/bin/busybox readlink -f "$device/of_node" 2>/dev/null || true)
		[ "$node" != "$simplefb_node" ] || simplefb_platform_count=$((simplefb_platform_count + 1))
	done
	printf 'simplefb_platform_count=%s\n' "$simplefb_platform_count"
	[ ! -d "$platform_fb" ] || printf 'simplefb_platform_present=1\n'
	[ -d "$platform_fb" ] || printf 'simplefb_platform_present=0\n'
	if [ -L "$platform_fb/driver" ]; then
		printf 'simplefb_platform_driver='; /bin/busybox basename "$(/bin/busybox readlink -f "$platform_fb/driver")"
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
	printf 'fb0_name='; /bin/busybox cat /sys/class/graphics/fb0/name 2>/dev/null || printf 'unavailable\n'
	printf 'fb0_virtual_size='; /bin/busybox cat /sys/class/graphics/fb0/virtual_size 2>/dev/null || printf 'unavailable\n'
	printf 'fb0_bits_per_pixel='; /bin/busybox cat /sys/class/graphics/fb0/bits_per_pixel 2>/dev/null || printf 'unavailable\n'
	printf 'fb0_stride='; /bin/busybox cat /sys/class/graphics/fb0/stride 2>/dev/null || printf 'unavailable\n'

	observer_node=/sys/firmware/devicetree/base/a72-power@10222000
	observer_device=/sys/bus/platform/devices/10222000.a72-power
	[ ! -d "$observer_node" ] || printf 'observer_dt_node_present=1\n'
	[ -d "$observer_node" ] || printf 'observer_dt_node_present=0\n'
	[ ! -d "$observer_device" ] || printf 'observer_device_present=1\n'
	[ -d "$observer_device" ] || printf 'observer_device_present=0\n'
	[ ! -d /sys/bus/platform/drivers/mt6797-a72-power ] || printf 'observer_driver_present=1\n'
	[ -d /sys/bus/platform/drivers/mt6797-a72-power ] || printf 'observer_driver_present=0\n'

	i2c6_node=/sys/firmware/devicetree/base/i2c@1100e000
	[ ! -d "$i2c6_node" ] || printf 'i2c6_dt_node_present=1\n'
	[ -d "$i2c6_node" ] || printf 'i2c6_dt_node_present=0\n'
	printf 'i2c6_status_hex='; property_hex "$i2c6_node/status"; printf '\n'
	i2c6_platform_count=0
	for device in /sys/bus/platform/devices/*; do
		[ -d "$device" ] || continue
		node=$(/bin/busybox readlink -f "$device/of_node" 2>/dev/null || true)
		[ "${node##*/}" != i2c@1100e000 ] || i2c6_platform_count=$((i2c6_platform_count + 1))
	done
	printf 'i2c6_platform_count=%s\n' "$i2c6_platform_count"
	da9214_dt_count=0
	for node in "$i2c6_node"/*; do
		[ -d "$node" ] || continue
		compatible=$(property_hex "$node/compatible")
		[ "$compatible" != 646c672c64613932313400 ] || da9214_dt_count=$((da9214_dt_count + 1))
	done
	printf 'da9214_dt_count=%s\n' "$da9214_dt_count"
	da9214_client_count=0
	for client in /sys/bus/i2c/devices/*-0068; do
		[ -d "$client" ] || continue
		da9214_client_count=$((da9214_client_count + 1))
	done
	printf 'da9214_client_count=%s\n' "$da9214_client_count"
	da9214_bucka_count=0
	vproc_big_count=0
	for name_path in /sys/class/regulator/regulator.*/name; do
		[ -f "$name_path" ] || continue
		name=$(/bin/busybox cat "$name_path")
		[ "$name" != da9214-bucka ] || da9214_bucka_count=$((da9214_bucka_count + 1))
		[ "$name" != vproc-big ] || vproc_big_count=$((vproc_big_count + 1))
	done
	printf 'da9214_bucka_count=%s\n' "$da9214_bucka_count"
	printf 'vproc_big_count=%s\n' "$vproc_big_count"

	aw_node=/sys/firmware/devicetree/base/i2c@1101c000/gpio-expander@5b
	printf 'aw9523_compatible_hex='; property_hex "$aw_node/compatible"; printf '\n'
	printf 'aw9523_status_hex='; property_hex "$aw_node/status"; printf '\n'
	aw9523_client_count=0
	aw9523_driver=unavailable
	for client in /sys/bus/i2c/devices/*-005b; do
		[ -d "$client" ] || continue
		aw9523_client_count=$((aw9523_client_count + 1))
		if [ -L "$client/driver" ]; then
			aw9523_driver=$(/bin/busybox basename "$(/bin/busybox readlink -f "$client/driver")")
		else
			aw9523_driver=unbound
		fi
	done
	printf 'aw9523_client_count=%s\n' "$aw9523_client_count"
	printf 'aw9523_driver=%s\n' "$aw9523_driver"

	matrix_node=/sys/firmware/devicetree/base/keyboard-matrix
	matrix_device=/sys/bus/platform/devices/keyboard-matrix
	printf 'matrix_compatible_hex='; property_hex "$matrix_node/compatible"; printf '\n'
	printf 'matrix_status_hex='; property_hex "$matrix_node/status"; printf '\n'
	printf 'matrix_poll_interval_hex='; property_hex "$matrix_node/poll-interval"; printf '\n'
	printf 'matrix_col_scan_delay_hex='; property_hex "$matrix_node/col-scan-delay-us"; printf '\n'
	[ ! -d "$matrix_device" ] || printf 'matrix_device_present=1\n'
	[ -d "$matrix_device" ] || printf 'matrix_device_present=0\n'
	if [ -L "$matrix_device/driver" ]; then
		printf 'matrix_driver='; /bin/busybox basename "$(/bin/busybox readlink -f "$matrix_device/driver")"
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

	keymap_output=$(/bin/console-keymap-verify --verify /etc/gemini-us.bkeymap 2>&1)
	keymap_rc=$?
	printf 'keymap_verify_rc=%s\n' "$keymap_rc"
	printf 'keymap_verify_output_hex='; printf '%s' "$keymap_output" | /bin/busybox hexdump -v -e '1/1 "%02x"'; printf '\n'
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
	printf 'usb0_address='; /bin/busybox cat /sys/class/net/usb0/address 2>/dev/null || printf 'unavailable\n'
	printf 'usb0_carrier='; /bin/busybox cat /sys/class/net/usb0/carrier 2>/dev/null || printf 'unavailable\n'
	printf 'usb0_operstate='; /bin/busybox cat /sys/class/net/usb0/operstate 2>/dev/null || printf 'unavailable\n'
	usb0_ipv4_total=$(/bin/busybox ip -o -4 address show dev usb0 2>/dev/null | /bin/busybox awk 'END { print NR + 0 }')
	usb0_ipv4_exact=$(/bin/busybox ip -o -4 address show dev usb0 2>/dev/null | \
		/bin/busybox awk '$4 == "10.15.19.82/24" { found++ } END { print found + 0 }')
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
		case "$target" in /dev/watchdog*) watchdog_fd_count=$((watchdog_fd_count + 1)) ;; esac
	done
	printf 'watchdog_fd_count=%s\n' "$watchdog_fd_count"
	printf 'boot_id='; /bin/busybox cat /proc/sys/kernel/random/boot_id
	printf 'uptime_seconds='; /bin/busybox cut -d. -f1 /proc/uptime
	printf 'online='; /bin/busybox cat /sys/devices/system/cpu/online
	printf 'offline='; /bin/busybox cat /sys/devices/system/cpu/offline
}

printf '__AH_IDENTITY_BEGIN__\n'
printf 'boot_id='; /bin/busybox cat /proc/sys/kernel/random/boot_id
printf 'uptime_seconds='; /bin/busybox cut -d. -f1 /proc/uptime
printf 'cmdline='; /bin/busybox cat /proc/cmdline
printf 'possible='; /bin/busybox cat /sys/devices/system/cpu/possible
printf 'present='; /bin/busybox cat /sys/devices/system/cpu/present
printf 'online='; /bin/busybox cat /sys/devices/system/cpu/online
printf 'offline='; /bin/busybox cat /sys/devices/system/cpu/offline
printf 'nproc='; /bin/busybox nproc
printf 'kernel='; /bin/busybox uname -r
printf 'config_sha256='; /bin/busybox zcat /proc/config.gz | /bin/busybox sha256sum | /bin/busybox awk '{ print $1 }'
printf 'config_cmdline='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_CMDLINE='
printf 'config_force='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_CMDLINE_FORCE='
printf 'config_a72_observer='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_MTK_MT6797_A72_POWER='
printf 'config_da9211='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_REGULATOR_DA9211='
printf 'config_simplefb='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_FB_SIMPLE='
printf 'config_aw9523='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_PINCTRL_AW9523='
printf 'config_matrix='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_KEYBOARD_MATRIX='
printf 'cpu8_enable_method='; /bin/busybox tr -d '\000' </sys/firmware/devicetree/base/cpus/cpu@200/enable-method; printf '\n'
printf 'cpu9_enable_method='; /bin/busybox tr -d '\000' </sys/firmware/devicetree/base/cpus/cpu@201/enable-method; printf '\n'
printf 'init_sha256='; file_sha256 /init; printf '\n'
printf 'busybox_sha256='; file_sha256 /bin/busybox; printf '\n'
printf 'ac_record_sha256='; file_sha256 /bin/ac-record; printf '\n'
printf 'usb_net_sha256='; file_sha256 /bin/usb-net; printf '\n'
printf 'usb_shell_sha256='; file_sha256 /bin/usb-shell; printf '\n'
printf 'local_shell_sha256='; file_sha256 /bin/local-shell; printf '\n'
printf 'reboot_sha256='; file_sha256 /bin/reboot; printf '\n'
printf 'keymap_sha256='; file_sha256 /etc/gemini-us.bkeymap; printf '\n'
printf 'keymap_verifier_sha256='; file_sha256 /bin/console-keymap-verify; printf '\n'
printf 'unicode_helper_sha256='; file_sha256 /bin/console-unicode-mode; printf '\n'
printf 'input_helper_sha256='; file_sha256 /bin/input-event-capture; printf '\n'
printf '__AH_IDENTITY_END__\n'

printf '__AH_STATE1_BEGIN__\n'; read_state; printf '__AH_STATE1_END__\n'
printf '__AH_STAT1_BEGIN__\n'; /bin/busybox grep '^cpu[0-9]' /proc/stat; printf '__AH_STAT1_END__\n'
/bin/busybox sleep 5
printf '__AH_STATE2_BEGIN__\n'; read_state; printf '__AH_STATE2_END__\n'
printf '__AH_STAT2_BEGIN__\n'; /bin/busybox grep '^cpu[0-9]' /proc/stat; printf '__AH_STAT2_END__\n'
printf '__AH_DMESG_BEGIN__\n'; /bin/busybox dmesg; printf '__AH_DMESG_END__\n'
exit
EOF

{
	printf '__AH_HOST_BEGIN__\n'
	printf 'installed_full_sha256_input=%s\n' "$installed_full_sha256"
	printf 'attestation_basis=caller-supplied-prior-full-partition-readback\n'
	printf 'device_partition_read_during_collection=no\n'
	printf 'interface=%s\nmac=%s\nhost_address=%s\nroute_interface=%s\n' \
		"$interface" "$mac" "$HOST_ADDRESS" "$route_interface"
	printf '__AH_HOST_END__\n'
} >"$output"
nc -4 -b "$interface" -s "$HOST_ADDRESS" -G 5 -w 90 "$DEVICE_ADDRESS" 2323 \
	<"$command_file" >>"$output"
python3 "$script_dir/validate-runtime.py" --capture "$output"
printf 'capture=%s\n' "$output"
