#!/bin/sh
# SPDX-License-Identifier: MIT
# One WMT firmware-load window on the identified primary Gemian boot.
set -eu
export LC_ALL=C
umask 077

expected_boot=636e12fb-65de-4eb3-88c8-70c3e4cec71e
output=/var/tmp/gemini-emi-wmt-watch-20260928
wp_adr=0x102035e0
wp_ctrl=0x102035e8
chker=0x102035f0
chker_type=0x102035f4
chker_adr=0x102035f8
baseline_chker=0x00800000
modified=0
connman_disabled=0
wmt_off_attempted=0
wmt_on_attempted=0

read32() { /bin/busybox devmem "$1" 32 | tr '[:upper:]' '[:lower:]'; }
write32() { /bin/busybox devmem "$1" 32 "$2" >/dev/null; }
log_regs() {
	printf '%s_wp_adr=%s\n' "$1" "$(read32 "$wp_adr")"
	printf '%s_wp_ctrl=%s\n' "$1" "$(read32 "$wp_ctrl")"
	printf '%s_chker=%s\n' "$1" "$(read32 "$chker")"
	printf '%s_type=%s\n' "$1" "$(read32 "$chker_type")"
	printf '%s_addr=%s\n' "$1" "$(read32 "$chker_adr")"
}
cleanup() {
	status=$?
	trap - EXIT
	set +e
	if [ "$modified" -eq 1 ]; then
		log_regs cleanup_hit || status=1
		# Stop observation before restoring the radio. Clear only our hit.
		write32 "$chker" "$baseline_chker" || status=1
		write32 "$wp_ctrl" 0x00000000 || status=1
		write32 "$wp_adr" 0x00000000 || status=1
		write32 "$chker" 0x01800000 || status=1
		log_regs post || status=1
		[ "$(read32 "$wp_adr")" = 0x00000000 ] || status=1
		[ "$(read32 "$wp_ctrl")" = 0x00000000 ] || status=1
		[ "$(read32 "$chker")" = "$baseline_chker" ] || status=1
		[ "$(read32 "$chker_type")" = 0x00000000 ] || status=1
		[ "$(read32 "$chker_adr")" = 0x00000000 ] || status=1
	fi
	if [ "$wmt_off_attempted" -eq 1 ] && [ "$wmt_on_attempted" -eq 0 ]; then
		wmt_on_attempted=1
		timeout 15 sh -c 'printf 1 > /dev/wmtWifi' || status=1
	fi
	if [ "$connman_disabled" -eq 1 ]; then
		timeout 15 connmanctl enable wifi || status=1
		i=0
		while [ "$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo 0)" != 1 ] &&
		      [ "$i" -lt 90 ]; do
			sleep 1
			i=$((i + 1))
		done
		[ "$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo 0)" = 1 ] || status=1
	fi
	if [ -d "$output" ]; then
		printf 'boot_after=%s\n' "$(cat /proc/sys/kernel/random/boot_id)"
		printf 'carrier_after=%s\n' "$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo unavailable)"
		printf 'exit_code=%s\n' "$status"
		dmesg >"$output/dmesg-after.log"
	fi
	exit "$status"
}
trap cleanup EXIT
trap 'exit 143' TERM

[ "$(id -u)" -eq 0 ] || exit 2
[ "$(uname -r)" = '3.18.41+' ] || exit 2
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$expected_boot" ] || exit 2
[ "$(cat /sys/class/net/wlan0/carrier)" = 1 ] || exit 2
[ "$(cat /sys/class/power_supply/battery/health)" = Good ] || exit 2
capacity=$(cat /sys/class/power_supply/battery/capacity)
case "$capacity" in *[!0-9]*|'') exit 2;; esac
[ "$capacity" -ge 40 ] || exit 2
[ "$(stat -c '%t:%T' /dev/wmtWifi)" = 99:0 ] || exit 2
for cmd in connmanctl iw timeout; do command -v "$cmd" >/dev/null || exit 2; done
mpu=/sys/bus/platform/drivers/emi_mpu_ctrl/mpu_config
grep -Fx 'R18-> 0xbfa00000 to 0xbfa7ffff' "$mpu" >/dev/null
grep -Fx 'R23-> 0x0 to 0xffffffff' "$mpu" >/dev/null
[ "$(read32 "$wp_adr")" = 0x00000000 ] || exit 2
[ "$(read32 "$wp_ctrl")" = 0x00000000 ] || exit 2
[ "$(read32 "$chker")" = "$baseline_chker" ] || exit 2
[ "$(read32 "$chker_type")" = 0x00000000 ] || exit 2
[ "$(read32 "$chker_adr")" = 0x00000000 ] || exit 2
[ ! -e "$output" ] && [ ! -L "$output" ] || exit 2
[ "$#" -eq 0 ] || { [ "$#" -eq 1 ] && [ "$1" = --preflight ]; } || exit 2
[ "$#" -eq 0 ] || { printf 'preflight=pass boot=%s\n' "$expected_boot"; exit 0; }
mkdir -m 0700 "$output"
exec >"$output/control.log" 2>&1
printf 'boot=%s\n' "$expected_boot"
log_regs pre
dmesg >"$output/dmesg-before.log"

connman_disabled=1
timeout 15 connmanctl disable wifi
disconnected=0
i=0
while [ "$i" -lt 25 ]; do
	if [ "$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo 0)" = 0 ] &&
	   iw dev wlan0 link | grep -Fxq 'Not connected.'; then
		disconnected=$((disconnected + 1))
	else
		disconnected=0
	fi
	[ "$disconnected" -ge 3 ] && break
	sleep 1
	i=$((i + 1))
done
[ "$disconnected" -ge 3 ] || exit 1
printf 'disconnected_before_wmt=yes\n'

wmt_off_attempted=1
timeout 15 sh -c 'printf 0 > /dev/wmtWifi'
i=0
while [ -e /sys/class/net/wlan0 ] && [ "$i" -lt 20 ]; do sleep 1; i=$((i + 1)); done
[ ! -e /sys/class/net/wlan0 ] || exit 1
[ "$(read32 "$chker")" = "$baseline_chker" ] || exit 1

modified=1
# 512 KiB at 0xbfa00000, relative to 0x40000000; read/write, no
# interrupt, slave error, read suppression or write suppression.
write32 "$wp_adr" 0x7fa00000
write32 "$wp_ctrl" 0x000000d3
[ "$(read32 "$wp_adr")" = 0x7fa00000 ] || exit 1
[ "$(read32 "$wp_ctrl")" = 0x000000d3 ] || exit 1
write32 "$chker" 0x00880000
printf 'armed_chker=%s\n' "$(read32 "$chker")"

wmt_on_attempted=1
timeout 15 sh -c 'printf 1 > /dev/wmtWifi'
log_regs hit
[ -e /sys/class/net/wlan0 ] || exit 1
printf 'wmt_on_returned=yes\n'
