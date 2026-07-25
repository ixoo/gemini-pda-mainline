#!/usr/bin/env bash

# Source foundation: Candidate AF collector SHA-256
# b90409f127514d9934c37868bd211cc26a09b25985231c0b796ef0c16ee1f3cb.
# Candidate AG adds only read-only live-DT/simplefb/fb0 observations.

set -euo pipefail
export LC_ALL=C
umask 077

readonly EXPECTED_INSTALLED_FULL_SHA256=63e0b3178072b2945a3537e17fda8c50ebce8032ca00110185993b4e2b7b1e14

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
[[ "$interface" =~ ^[a-zA-Z0-9]+$ && -n "$output" ]] || { usage; exit 2; }
[[ "$installed_full_sha256" == "$EXPECTED_INSTALLED_FULL_SHA256" ]] || \
	die 'installed full-partition checksum is not the exact validated AG value'
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite runtime capture'
for command in awk cat dirname grep ifconfig mktemp nc ping python3 rm; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
mac="$(ifconfig "$interface" | awk '/^[[:space:]]*ether / {print tolower($2); exit}')"
[[ "$mac" == 42:00:15:19:82:00 ]] || die "interface $interface is not the exact Gemini USB MAC"
ifconfig "$interface" | grep -Eq 'inet 10\.15\.19\.1[[:space:]]' || die 'host USB address is absent'
ping -c 3 -S 10.15.19.1 10.15.19.82 >/dev/null || die 'bounded USB ping failed'

command_file="$(mktemp /tmp/candidate-ag-simplefb-command.XXXXXX)"
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
	if [ -d "$simplefb_node" ]; then
		printf 'simplefb_node_present=1\n'
	else
		printf 'simplefb_node_present=0\n'
	fi
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
	printf 'simplefb_name_hex='; property_hex "$simplefb_node/name"; printf '\n'
	if [ -e "$simplefb_node/memory-region" ]; then
		printf 'simplefb_memory_region_present=1\n'
	else
		printf 'simplefb_memory_region_present=0\n'
	fi
	simplefb_child_count=0
	simplefb_unexpected_entry_count=0
	for entry in "$simplefb_node"/*; do
		[ -e "$entry" ] || continue
		if [ -d "$entry" ]; then
			simplefb_child_count=$((simplefb_child_count + 1))
			continue
		fi
		property=$(/bin/busybox basename "$entry")
		case "$property" in
		compatible|reg|width|height|stride|format|clocks|name) ;;
		*) simplefb_unexpected_entry_count=$((simplefb_unexpected_entry_count + 1)) ;;
		esac
	done
	printf 'simplefb_child_count=%s\n' "$simplefb_child_count"
	printf 'simplefb_unexpected_entry_count=%s\n' "$simplefb_unexpected_entry_count"

	runtime_framebuffer_reservation_count=0
	for node in "$reserved_root"/*; do
		[ -d "$node" ] || continue
		compatible=$(property_hex "$node/compatible")
		[ "$compatible" != 6d6564696174656b2c6672616d6562756666657200 ] || \
			runtime_framebuffer_reservation_count=$((runtime_framebuffer_reservation_count + 1))
	done
	printf 'runtime_framebuffer_reservation_count=%s\n' "$runtime_framebuffer_reservation_count"
	if [ -d "$reserved_fb" ]; then
		printf 'runtime_framebuffer_reservation_present=1\n'
	else
		printf 'runtime_framebuffer_reservation_present=0\n'
	fi
	printf 'runtime_framebuffer_compatible_hex='; property_hex "$reserved_fb/compatible"; printf '\n'
	printf 'runtime_framebuffer_reg_hex='; property_hex "$reserved_fb/reg"; printf '\n'
	printf 'runtime_framebuffer_name_hex='; property_hex "$reserved_fb/name"; printf '\n'
	if [ -e "$reserved_fb/no-map" ]; then
		printf 'runtime_framebuffer_no_map_present=1\n'
	else
		printf 'runtime_framebuffer_no_map_present=0\n'
	fi
	printf 'runtime_framebuffer_no_map_hex='; property_hex "$reserved_fb/no-map"; printf '\n'
	runtime_framebuffer_child_count=0
	runtime_framebuffer_unexpected_entry_count=0
	for entry in "$reserved_fb"/*; do
		[ -e "$entry" ] || continue
		if [ -d "$entry" ]; then
			runtime_framebuffer_child_count=$((runtime_framebuffer_child_count + 1))
			continue
		fi
		property=$(/bin/busybox basename "$entry")
		case "$property" in
		compatible|reg|no-map|name) ;;
		*) runtime_framebuffer_unexpected_entry_count=$((runtime_framebuffer_unexpected_entry_count + 1)) ;;
		esac
	done
	printf 'runtime_framebuffer_child_count=%s\n' "$runtime_framebuffer_child_count"
	printf 'runtime_framebuffer_unexpected_entry_count=%s\n' \
		"$runtime_framebuffer_unexpected_entry_count"

	simplefb_platform_count=0
	for device in /sys/bus/platform/devices/*; do
		[ -d "$device" ] || continue
		node=$(/bin/busybox readlink -f "$device/of_node" 2>/dev/null || true)
		[ "$node" != "$simplefb_node" ] || simplefb_platform_count=$((simplefb_platform_count + 1))
	done
	printf 'simplefb_platform_count=%s\n' "$simplefb_platform_count"
	if [ -d "$platform_fb" ]; then
		printf 'simplefb_platform_present=1\n'
	else
		printf 'simplefb_platform_present=0\n'
	fi
	if [ -L "$platform_fb/driver" ]; then
		printf 'simplefb_platform_driver='; /bin/busybox basename "$(/bin/busybox readlink -f "$platform_fb/driver")"
	else
		printf 'simplefb_platform_driver=unbound\n'
	fi
	if [ -L "$platform_fb/of_node" ]; then
		printf 'simplefb_platform_of_node='; /bin/busybox readlink -f "$platform_fb/of_node"
	else
		printf 'simplefb_platform_of_node=unavailable\n'
	fi

	fb_count=0
	for fb in /sys/class/graphics/fb[0-9]*; do
		[ -d "$fb" ] || continue
		fb_count=$((fb_count + 1))
	done
	printf 'fb_count=%s\n' "$fb_count"
	if [ -d /sys/class/graphics/fb0 ]; then
		printf 'fb0_present=1\n'
	else
		printf 'fb0_present=0\n'
	fi
	printf 'fb0_name='; /bin/busybox cat /sys/class/graphics/fb0/name 2>/dev/null || printf 'unavailable\n'
	printf 'fb0_virtual_size='; /bin/busybox cat /sys/class/graphics/fb0/virtual_size 2>/dev/null || printf 'unavailable\n'
	printf 'fb0_bits_per_pixel='; /bin/busybox cat /sys/class/graphics/fb0/bits_per_pixel 2>/dev/null || printf 'unavailable\n'
	printf 'fb0_stride='; /bin/busybox cat /sys/class/graphics/fb0/stride 2>/dev/null || printf 'unavailable\n'
	if [ -L /sys/class/graphics/fb0/device ]; then
		printf 'fb0_platform_device='; /bin/busybox basename "$(/bin/busybox readlink -f /sys/class/graphics/fb0/device)"
	else
		printf 'fb0_platform_device=unavailable\n'
	fi

	observer_device=/sys/bus/platform/devices/10222000.a72-power
	if [ -d "$observer_device" ]; then
		printf 'observer_device_present=1\n'
	else
		printf 'observer_device_present=0\n'
	fi
	if [ -L "$observer_device/driver" ]; then
		printf 'observer_device_driver='; /bin/busybox basename "$(/bin/busybox readlink -f "$observer_device/driver")"
	else
		printf 'observer_device_driver=unbound\n'
	fi
	if [ -d /sys/bus/platform/drivers/mt6797-a72-power ]; then
		printf 'observer_driver_present=1\n'
	else
		printf 'observer_driver_present=0\n'
	fi
	observer_attr_count=0
	for attribute in ready resources_ready abi hooks_armed provider_mode snapshot; do
		[ ! -e "$observer_device/$attribute" ] || observer_attr_count=$((observer_attr_count + 1))
	done
	printf 'observer_attr_count=%s\n' "$observer_attr_count"

	i2c6_count=0
	i2c6_device=
	for device in /sys/bus/platform/devices/*; do
		[ -d "$device" ] || continue
		node=$(/bin/busybox readlink -f "$device/of_node" 2>/dev/null || true)
		[ "${node##*/}" = i2c@1100e000 ] || continue
		i2c6_count=$((i2c6_count + 1))
		i2c6_device=$device
	done
	printf 'i2c6_count=%s\n' "$i2c6_count"
	if [ "$i2c6_count" -eq 1 ]; then
		printf 'i2c6_device='; /bin/busybox basename "$i2c6_device"
		if [ -L "$i2c6_device/driver" ]; then
			printf 'i2c6_driver='; /bin/busybox basename "$(/bin/busybox readlink -f "$i2c6_device/driver")"
		else
			printf 'i2c6_driver=unbound\n'
		fi
	else
		printf 'i2c6_device=unavailable\ni2c6_driver=unavailable\n'
	fi

	da9214_count=0
	da9214_device=
	for client in /sys/bus/i2c/devices/*-0068; do
		[ -d "$client" ] || continue
		da9214_count=$((da9214_count + 1))
		da9214_device=$client
	done
	printf 'da9214_count=%s\n' "$da9214_count"
	da9214_basename=unavailable
	if [ "$da9214_count" -eq 1 ]; then
		da9214_basename=$(/bin/busybox basename "$da9214_device")
		printf 'da9214_device=%s\n' "$da9214_basename"
		if /bin/busybox tr '\000' '\n' <"$da9214_device/of_node/compatible" | /bin/busybox grep -qx 'dlg,da9214'; then
			printf 'da9214_compatible=dlg,da9214\n'
		else
			printf 'da9214_compatible=unexpected\n'
		fi
		da_node=$(/bin/busybox readlink -f "$da9214_device/of_node" 2>/dev/null || true)
		printf 'da9214_parent='; /bin/busybox basename "$(/bin/busybox dirname "$da_node")"
		if [ -L "$da9214_device/driver" ]; then
			printf 'da9214_driver='; /bin/busybox basename "$(/bin/busybox readlink -f "$da9214_device/driver")"
		else
			printf 'da9214_driver=unbound\n'
		fi
	else
		printf 'da9214_device=unavailable\nda9214_compatible=unavailable\n'
		printf 'da9214_parent=unavailable\nda9214_driver=unavailable\n'
	fi

	bucka_total=0
	bucka_count=0
	bucka_parent=unavailable
	buckb_total=0
	buckb_count=0
	buckb_parent=unavailable
	for name_path in /sys/class/regulator/regulator.*/name; do
		[ -f "$name_path" ] || continue
		name=$(/bin/busybox cat "$name_path")
		regulator_device=${name_path%/name}
		parent=$(/bin/busybox readlink -f "$regulator_device/device" 2>/dev/null || true)
		parent=${parent##*/}
		if [ "$name" = da9214-bucka ]; then
			bucka_total=$((bucka_total + 1))
			bucka_parent=$parent
			[ "$parent" != "$da9214_basename" ] || bucka_count=$((bucka_count + 1))
		fi
		if [ "$name" = vproc-big ]; then
			buckb_total=$((buckb_total + 1))
			buckb_parent=$parent
			[ "$parent" != "$da9214_basename" ] || buckb_count=$((buckb_count + 1))
		fi
	done
	printf 'da9214_bucka_total=%s\n' "$bucka_total"
	printf 'da9214_bucka_count=%s\n' "$bucka_count"
	printf 'da9214_bucka_parent=%s\n' "$bucka_parent"
	printf 'vproc_big_total=%s\n' "$buckb_total"
	printf 'vproc_big_count=%s\n' "$buckb_count"
	printf 'vproc_big_parent=%s\n' "$buckb_parent"

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

printf '__AG_IDENTITY_BEGIN__\n'
printf 'boot_id='; /bin/busybox cat /proc/sys/kernel/random/boot_id
printf 'uptime_seconds='; /bin/busybox cut -d. -f1 /proc/uptime
printf 'cmdline='; /bin/busybox cat /proc/cmdline
printf 'possible='; /bin/busybox cat /sys/devices/system/cpu/possible
printf 'present='; /bin/busybox cat /sys/devices/system/cpu/present
printf 'online='; /bin/busybox cat /sys/devices/system/cpu/online
printf 'offline='; /bin/busybox cat /sys/devices/system/cpu/offline
printf 'nproc='; /bin/busybox nproc
printf 'kernel='; /bin/busybox uname -r
printf 'config_cmdline='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_CMDLINE='
printf 'config_force='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_CMDLINE_FORCE='
printf 'config_kallsyms='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_KALLSYMS='
printf 'config_da9211='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_REGULATOR_DA9211='
printf 'config_a72_observer='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_MTK_MT6797_A72_POWER='
printf 'config_simplefb='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_FB_SIMPLE='
printf 'cpu8_enable_method='; /bin/busybox tr -d '\000' </sys/firmware/devicetree/base/cpus/cpu@200/enable-method; printf '\n'
printf 'cpu9_enable_method='; /bin/busybox tr -d '\000' </sys/firmware/devicetree/base/cpus/cpu@201/enable-method; printf '\n'
printf '__AG_IDENTITY_END__\n'

printf '__AG_STATE1_BEGIN__\n'
read_state
printf '__AG_STATE1_END__\n'
printf '__AG_STAT1_BEGIN__\n'
/bin/busybox grep '^cpu[0-9]' /proc/stat
printf '__AG_STAT1_END__\n'
/bin/busybox sleep 5
printf '__AG_STATE2_BEGIN__\n'
read_state
printf '__AG_STATE2_END__\n'
printf '__AG_STAT2_BEGIN__\n'
/bin/busybox grep '^cpu[0-9]' /proc/stat
printf '__AG_STAT2_END__\n'

printf '__AG_DMESG_BEGIN__\n'
/bin/busybox dmesg
printf '__AG_DMESG_END__\n'
exit
EOF
{
	printf '__AG_HOST_BEGIN__\n'
	printf 'installed_full_sha256_input=%s\n' "$installed_full_sha256"
	printf 'attestation_basis=caller-supplied-prior-full-partition-readback\n'
	printf 'device_partition_read_during_collection=no\n'
	printf '__AG_HOST_END__\n'
} >"$output"
nc -4 -b "$interface" -s 10.15.19.1 -G 5 -w 90 10.15.19.82 2323 \
	<"$command_file" >>"$output"
python3 "$script_dir/validate-runtime.py" --capture "$output"
printf 'capture=%s\n' "$output"
