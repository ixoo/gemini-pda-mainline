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

command_file="$(mktemp /tmp/candidate-ad-runtime-command.XXXXXX)"
cleanup() { [[ ! -f "$command_file" ]] || rm -f -- "$command_file"; }
trap cleanup EXIT
cat >"$command_file" <<'EOF'
printf '__AD_IDENTITY_BEGIN__\n'
printf 'cmdline='; cat /proc/cmdline
printf 'possible='; cat /sys/devices/system/cpu/possible
printf 'present='; cat /sys/devices/system/cpu/present
printf 'online='; cat /sys/devices/system/cpu/online
printf 'offline='; cat /sys/devices/system/cpu/offline
printf 'nproc='; nproc
printf 'kernel='; uname -r
printf 'config_cmdline='; /bin/busybox zcat /proc/config.gz | grep '^CONFIG_CMDLINE='
printf 'config_force='; /bin/busybox zcat /proc/config.gz | grep '^CONFIG_CMDLINE_FORCE='
printf '__AD_IDENTITY_END__\n'
printf '__AD_STAT1_BEGIN__\n'; grep '^cpu[0-9]' /proc/stat; printf '__AD_STAT1_END__\n'
sleep 5
printf '__AD_STAT2_BEGIN__\n'; grep '^cpu[0-9]' /proc/stat; printf '__AD_STAT2_END__\n'
printf '__AD_DMESG_BEGIN__\n'; dmesg; printf '__AD_DMESG_END__\n'
exit
EOF
nc -4 -b "$interface" -s 10.15.19.1 -G 5 -w 30 10.15.19.82 2323 \
	<"$command_file" >"$output"
python3 "$script_dir/validate-runtime.py" --capture "$output"
printf 'capture=%s\n' "$output"
