#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
usage() { printf 'usage: %s --interface IFACE --output FILE\n' "$0" >&2; }

interface=
output=
while (($#)); do
	case "$1" in
	--interface|--output)
		(($# >= 2)) || die "$1 requires a value"
		case "$1" in --interface) interface=$2 ;; --output) output=$2 ;; esac
		shift 2
		;;
	-h|--help) usage; exit 0 ;;
	*) usage; die "unknown option: $1" ;;
	esac
done
[[ "$interface" =~ ^[a-zA-Z0-9]+$ && -n "$output" ]] || { usage; exit 2; }
[[ ! -e "$output" && ! -L "$output" ]] || die 'refusing to overwrite runtime capture'
for command in awk grep ifconfig mktemp nc ping python3 rm; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
mac="$(ifconfig "$interface" | awk '/^[[:space:]]*ether / {print tolower($2); exit}')"
[[ "$mac" == 42:00:15:19:82:00 ]] || die "interface $interface is not the exact Gemini USB MAC"
ifconfig "$interface" | grep -Eq 'inet 10\.15\.19\.1[[:space:]]' || die 'host USB address is absent'
ping -c 3 -S 10.15.19.1 10.15.19.82 >/dev/null || die 'bounded USB ping failed'

command_file="$(mktemp /tmp/candidate-af-initcall-command.XXXXXX)"
cleanup() { [[ ! -f "$command_file" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
cat >"$command_file" <<'EOF'
uptime_seconds=$(/bin/busybox cut -d. -f1 /proc/uptime)
if [ "$uptime_seconds" -lt 45 ]; then
	/bin/busybox sleep $((45 - uptime_seconds))
fi

read_state() {
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

printf '__AF_IDENTITY_BEGIN__\n'
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
printf 'cpu8_enable_method='; /bin/busybox tr -d '\000' </sys/firmware/devicetree/base/cpus/cpu@200/enable-method; printf '\n'
printf 'cpu9_enable_method='; /bin/busybox tr -d '\000' </sys/firmware/devicetree/base/cpus/cpu@201/enable-method; printf '\n'
printf '__AF_IDENTITY_END__\n'

printf '__AF_STATE1_BEGIN__\n'
read_state
printf '__AF_STATE1_END__\n'
printf '__AF_STAT1_BEGIN__\n'
/bin/busybox grep '^cpu[0-9]' /proc/stat
printf '__AF_STAT1_END__\n'
/bin/busybox sleep 5
printf '__AF_STATE2_BEGIN__\n'
read_state
printf '__AF_STATE2_END__\n'
printf '__AF_STAT2_BEGIN__\n'
/bin/busybox grep '^cpu[0-9]' /proc/stat
printf '__AF_STAT2_END__\n'

printf '__AF_DMESG_BEGIN__\n'
/bin/busybox dmesg
printf '__AF_DMESG_END__\n'
exit
EOF
nc -4 -b "$interface" -s 10.15.19.1 -G 5 -w 90 10.15.19.82 2323 \
	<"$command_file" >"$output"
python3 "$script_dir/validate-runtime.py" --capture "$output"
printf 'capture=%s\n' "$output"
