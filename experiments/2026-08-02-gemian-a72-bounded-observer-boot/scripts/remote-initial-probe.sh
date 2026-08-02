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

find_thermal_zone()
{
	wanted=$1
	for zone in /sys/class/thermal/thermal_zone*; do
		[ -d "$zone" ] || continue
		[ -r "$zone/type" ] || continue
		[ "$(cat "$zone/type" 2>/dev/null || true)" = "$wanted" ] || continue
		printf '%s' "$zone"
		return 0
	done
	return 1
}

for command in awk cat cut findmnt grep head id mktemp rm sha256sum sleep stat \
	tail uname wc; do
	command -v "$command" >/dev/null 2>&1 || fail "missing-command-$command"
done

[ "$(id -u)" = 0 ] || fail not-root
[ "$(uname -m)" = aarch64 ] || fail wrong-architecture
[ "$(uname -r)" = 3.18.41+ ] || fail wrong-release
grep -Fq '#1 SMP PREEMPT Sun Aug 2 14:14:43 UTC 2026' /proc/version ||
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

cpu_zone=$(find_thermal_zone mtktscpu) || fail missing-cpu-zone
ap_zone=$(find_thermal_zone mtktsAP) || fail missing-ap-zone
pmic_zone=$(find_thermal_zone mtktspmic) || fail missing-pmic-zone
da9214_zone=$(find_thermal_zone tsda9214) || fail missing-da9214-zone

boot_id_before=$(sha256sum /proc/sys/kernel/random/boot_id | cut -c1-64)
case "$boot_id_before" in
????????????????????????????????????????????????????????????????) ;;
*) fail boot-id-hash ;;
esac

usb_online=$(flat_read /sys/class/power_supply/usb/online usb-online)
battery_status=$(flat_read /sys/class/power_supply/battery/status battery-status)
battery_capacity=$(flat_read /sys/class/power_supply/battery/capacity battery-capacity)
battery_health=$(flat_read /sys/class/power_supply/battery/health battery-health)
[ "$usb_online" = 1 ] || fail usb-power-absent
[ "$battery_status" = Full ] || fail battery-not-full
[ "$battery_capacity" = 100 ] || fail battery-not-100
[ "$battery_health" = Good ] || fail battery-health

printf 'experiment=gemian-a72-bounded-observer-initial\n'
printf 'kernel_release=3.18.41+\narchitecture=aarch64\n'
printf 'build_identity=#1 SMP PREEMPT Sun Aug 2 14:14:43 UTC 2026\n'
printf 'root=/dev/mmcblk0p29\npossible=0-9\npresent=0-9\n'
printf 'observer_path=%s\nobserver_mode=400\n' "$observer"
printf 'boot_id_before_sha256=%s\n' "$boot_id_before"
printf 'power=usb:%s|status:%s|capacity:%s|health:%s\n' \
	"$usb_online" "$battery_status" "$battery_capacity" "$battery_health"
printf 'state_changing_writes=none\nload_workers=0\ncpu_online_writes=none\n'

all_offline=yes
i=1
while [ "$i" -le 5 ]; do
	cpu8=$(flat_read /sys/devices/system/cpu/cpu8/online cpu8)
	cpu9=$(flat_read /sys/devices/system/cpu/cpu9/online cpu9)
	online=$(flat_read /sys/devices/system/cpu/online online)
	printf 'baseline_sample=%s cpu8=%s cpu9=%s online=%s\n' \
		"$i" "$cpu8" "$cpu9" "$online"
	[ "$cpu8" = 0 ] && [ "$cpu9" = 0 ] || all_offline=no
	i=$((i + 1))
	sleep 0.2
done

snapshot=$(mktemp /tmp/.gemian-a72-observer-initial.XXXXXXXX)
cleanup() { rm -f -- "$snapshot"; }
trap cleanup EXIT HUP INT TERM
cat "$observer" >"$snapshot" || fail observer-read
header=$(head -n 1 "$snapshot")
case "$header" in
abi=mt6797-a72-transition-observer-v1\ count=*\ overwritten=*) ;;
*) fail observer-header ;;
esac
count=$(printf '%s\n' "$header" | awk '{sub(/^count=/, "", $2); print $2}')
overwritten=$(printf '%s\n' "$header" | awk '{sub(/^overwritten=/, "", $3); print $3}')
case "$count:$overwritten" in
*[!0-9:]*|:*|*:) fail observer-count ;;
esac
[ "$(wc -l <"$snapshot" | awk '{print $1}')" -eq $((count + 1)) ] ||
	fail observer-line-count

printf '__OBSERVER_INITIAL_BEGIN__\n'
cat "$snapshot"
printf '__OBSERVER_INITIAL_END__\n'

cpu8_after=$(flat_read /sys/devices/system/cpu/cpu8/online cpu8-after)
cpu9_after=$(flat_read /sys/devices/system/cpu/cpu9/online cpu9-after)
online_after=$(flat_read /sys/devices/system/cpu/online online-after)
boot_id_after=$(sha256sum /proc/sys/kernel/random/boot_id | cut -c1-64)
[ "$boot_id_after" = "$boot_id_before" ] || fail boot-id-changed

cpu_temp=$(flat_read "$cpu_zone/temp" cpu-temp)
ap_temp=$(flat_read "$ap_zone/temp" ap-temp)
pmic_temp=$(flat_read "$pmic_zone/temp" pmic-temp)
da9214_temp=$(flat_read "$da9214_zone/temp" da9214-temp)
for pair in "$cpu_temp:50000:cpu" "$ap_temp:50000:ap" \
	"$pmic_temp:60000:pmic" "$da9214_temp:80000:da9214"; do
	value=${pair%%:*}
	rest=${pair#*:}
	limit=${rest%%:*}
	name=${rest##*:}
	case "$value" in ''|*[!0-9-]*) fail "temperature-$name" ;; esac
	[ "$value" -lt "$limit" ] || fail "temperature-limit-$name"
done

disposition=blocked-cpu-state
if [ "$all_offline" = yes ] && [ "$cpu8_after" = 0 ] && [ "$cpu9_after" = 0 ]; then
	if [ "$overwritten" -ne 0 ]; then
		disposition=blocked-overwritten
	elif [ "$count" -eq 0 ]; then
		disposition=empty-offline
	else
		disposition=boot-records-present
	fi
fi

printf 'post_cpu8=%s\npost_cpu9=%s\npost_online=%s\n' \
	"$cpu8_after" "$cpu9_after" "$online_after"
printf 'temperatures_millic=cpu:%s|ap:%s|pmic:%s|da9214:%s\n' \
	"$cpu_temp" "$ap_temp" "$pmic_temp" "$da9214_temp"
printf 'boot_id_after_sha256=%s\nboot_id_stable=yes\n' "$boot_id_after"
printf 'observer_count=%s\nobserver_overwritten=%s\n' "$count" "$overwritten"
printf 'initial_disposition=%s\nload_permitted_by_initial=no\n' "$disposition"
printf 'status=completed\n'
