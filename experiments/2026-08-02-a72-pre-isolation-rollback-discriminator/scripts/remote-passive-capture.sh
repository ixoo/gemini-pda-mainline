#!/bin/sh

set -eu
export LC_ALL=C
umask 077

fail()
{
	printf 'failure=%s\n' "$1"
	exit 2
}

flat_read()
{
	[ -r "$1" ] || fail "unreadable-$2"
	value=$(cat "$1" 2>/dev/null) || fail "read-failed-$2"
	case "$value" in
	*'
'*) fail "multiline-$2" ;;
	esac
	printf '%s' "$value"
}

optional_read()
{
	[ -r "$1" ] || { printf unavailable; return; }
	value=$(cat "$1" 2>/dev/null) || { printf unreadable; return; }
	case "$value" in *'
'*) printf malformed ;; *) printf '%s' "$value" ;; esac
}

for command in cat cmp cut findmnt grep head id mktemp rm sha256sum sleep stat uname wc; do
	command -v "$command" >/dev/null 2>&1 || fail "missing-command-$command"
done

[ "$(id -u)" = 0 ] || fail not-root
[ "$(uname -m)" = aarch64 ] || fail wrong-architecture
[ "$(uname -r)" = 3.18.41+ ] || fail wrong-release
grep -Fq '#1 SMP PREEMPT Sun Aug 2 22:29:57 UTC 2026' /proc/version ||
	fail wrong-build-identity
[ "$(findmnt -n -o SOURCE / 2>/dev/null)" = /dev/mmcblk0p29 ] ||
	fail wrong-root
[ "$(flat_read /sys/devices/system/cpu/possible possible)" = 0-9 ] ||
	fail wrong-possible
[ "$(flat_read /sys/devices/system/cpu/present present)" = 0-9 ] ||
	fail wrong-present

observer=/proc/mt6797_a72_transition
[ -r "$observer" ] || fail observer-unreadable
[ "$(stat -c %a "$observer")" = 400 ] || fail observer-mode

first=$(mktemp /tmp/.gemian-a72-rollback-first.XXXXXXXX)
second=$(mktemp /tmp/.gemian-a72-rollback-second.XXXXXXXX)
cleanup() { rm -f -- "$first" "$second"; }
trap cleanup EXIT HUP INT TERM

# Copy decision-bearing evidence before optional power reporting.
cat "$observer" >"$first" || fail observer-first-read
case "$(head -n 1 "$first")" in
abi=mt6797-a72-transition-observer-v3\ state=*) ;;
*) fail observer-first-header ;;
esac
sleep 2
cat "$observer" >"$second" || fail observer-second-read
case "$(head -n 1 "$second")" in
abi=mt6797-a72-transition-observer-v3\ state=*) ;;
*) fail observer-second-header ;;
esac

boot_id_before=$(sha256sum /proc/sys/kernel/random/boot_id | cut -c1-64)
cpu8=$(flat_read /sys/devices/system/cpu/cpu8/online cpu8)
cpu9=$(flat_read /sys/devices/system/cpu/cpu9/online cpu9)
online=$(flat_read /sys/devices/system/cpu/online online)
usb=$(optional_read /sys/class/power_supply/usb/online)
battery_status=$(optional_read /sys/class/power_supply/battery/status)
battery_capacity=$(optional_read /sys/class/power_supply/battery/capacity)
battery_health=$(optional_read /sys/class/power_supply/battery/health)
boot_id_after=$(sha256sum /proc/sys/kernel/random/boot_id | cut -c1-64)
[ "$boot_id_after" = "$boot_id_before" ] || fail boot-id-changed

stable=no
cmp -s "$first" "$second" && stable=yes
printf 'experiment=gemian-a72-preiso-rollback-passive\n'
printf 'kernel_release=3.18.41+\narchitecture=aarch64\n'
printf 'build_identity=#1 SMP PREEMPT Sun Aug 2 22:29:57 UTC 2026\n'
printf 'root=/dev/mmcblk0p29\npossible=0-9\npresent=0-9\n'
printf 'observer_path=%s\nobserver_mode=400\n' "$observer"
printf 'boot_id_before_sha256=%s\n' "$boot_id_before"
printf 'state_changing_writes=none\nload_workers=0\ncpu_online_writes=none\n'
printf '__OBSERVER_FIRST_BEGIN__\n'
cat "$first"
printf '__OBSERVER_FIRST_END__\n'
printf '__OBSERVER_SECOND_BEGIN__\n'
cat "$second"
printf '__OBSERVER_SECOND_END__\n'
printf 'observer_first_lines=%s\nobserver_second_lines=%s\n' \
	"$(wc -l <"$first")" "$(wc -l <"$second")"
printf 'observer_snapshots_identical=%s\n' "$stable"
printf 'cpu8=%s\ncpu9=%s\nonline=%s\n' "$cpu8" "$cpu9" "$online"
printf 'power=usb:%s|status:%s|capacity:%s|health:%s\n' \
	"$usb" "$battery_status" "$battery_capacity" "$battery_health"
printf 'boot_id_after_sha256=%s\nboot_id_stable=yes\n' "$boot_id_after"
printf 'runtime_stimulus=none\nstatus=completed\n'
