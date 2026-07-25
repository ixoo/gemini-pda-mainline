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

command_file="$(mktemp /tmp/candidate-ae-observer-command.XXXXXX)"
cleanup() { [[ ! -f "$command_file" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
cat >"$command_file" <<'EOF'
uptime_seconds=$(/bin/busybox cut -d. -f1 /proc/uptime)
if [ "$uptime_seconds" -lt 45 ]; then
	/bin/busybox sleep $((45 - uptime_seconds))
fi

read_observer() {
	observer_driver=/sys/bus/platform/drivers/mt6797-a72-power
	observer_count=0
	observer_device=
	for provider_mode_path in "$observer_driver"/*/provider_mode; do
		[ -f "$provider_mode_path" ] || continue
		observer_count=$((observer_count + 1))
		observer_device=${provider_mode_path%/provider_mode}
	done
	printf 'observer_count=%s\n' "$observer_count"
	if [ "$observer_count" -eq 1 ]; then
		printf 'observer_device='; /bin/busybox basename "$observer_device"
		for attribute in ready resources_ready abi hooks_armed provider_mode; do
			printf '%s=' "$attribute"
			/bin/busybox cat "$observer_device/$attribute"
		done
		printf 'snapshot_begin\n'
		/bin/busybox cat "$observer_device/snapshot"
		printf 'snapshot_end\n'
	else
		printf 'observer_device=unavailable\n'
	fi
	printf 'boot_id='; /bin/busybox cat /proc/sys/kernel/random/boot_id
	printf 'uptime_seconds='; /bin/busybox cut -d. -f1 /proc/uptime
	printf 'online='; /bin/busybox cat /sys/devices/system/cpu/online
	printf 'offline='; /bin/busybox cat /sys/devices/system/cpu/offline
}

printf '__AE_IDENTITY_BEGIN__\n'
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
printf 'config_da9211='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_REGULATOR_DA9211='
printf 'config_a72_observer='; /bin/busybox zcat /proc/config.gz | /bin/busybox grep '^CONFIG_MTK_MT6797_A72_POWER='
printf 'cpu8_enable_method='; /bin/busybox tr -d '\000' </sys/firmware/devicetree/base/cpus/cpu@200/enable-method; printf '\n'
printf 'cpu9_enable_method='; /bin/busybox tr -d '\000' </sys/firmware/devicetree/base/cpus/cpu@201/enable-method; printf '\n'
printf '__AE_IDENTITY_END__\n'

printf '__AE_OBSERVER1_BEGIN__\n'
read_observer
printf '__AE_OBSERVER1_END__\n'
/bin/busybox sleep 5
printf '__AE_OBSERVER2_BEGIN__\n'
read_observer
printf '__AE_OBSERVER2_END__\n'

printf '__AE_DMESG_BEGIN__\n'
/bin/busybox dmesg
printf '__AE_DMESG_END__\n'
exit
EOF
nc -4 -b "$interface" -s 10.15.19.1 -G 5 -w 75 10.15.19.82 2323 \
	<"$command_file" >"$output"
python3 "$script_dir/validate-runtime.py" --capture "$output"
printf 'capture=%s\n' "$output"
