#!/bin/sh
# SPDX-License-Identifier: MIT
# One-use, non-blocking EMI watchpoint on this exact known-good Gemian boot.
set -eu

expected_boot=636e12fb-65de-4eb3-88c8-70c3e4cec71e
wp_adr=0x102035e0
wp_ctrl=0x102035e8
chker=0x102035f0
chker_type=0x102035f4
chker_adr=0x102035f8
baseline_chker=0x00800000
marker=/run/gemini-emi-wp-20260928
modified=0

read32() {
	/bin/busybox devmem "$1" 32 | tr '[:upper:]' '[:lower:]'
}

write32() {
	/bin/busybox devmem "$1" 32 "$2" >/dev/null
}

cleanup() {
	failed=0
	[ "$modified" -eq 1 ] || return 0
	# Disable first. The sole status-clear happens after all raw hit words
	# have been printed; never clear a pre-existing status.
	write32 "$chker" "$baseline_chker" || failed=1
	write32 "$wp_ctrl" 0x00000000 || failed=1
	write32 "$wp_adr" 0x00000000 || failed=1
	write32 "$chker" 0x01800000 || failed=1
	printf 'post_wp_adr=%s\n' "$(read32 "$wp_adr")"
	printf 'post_wp_ctrl=%s\n' "$(read32 "$wp_ctrl")"
	printf 'post_chker=%s\n' "$(read32 "$chker")"
	printf 'post_chker_type=%s\n' "$(read32 "$chker_type")"
	printf 'post_chker_adr=%s\n' "$(read32 "$chker_adr")"
	[ "$(read32 "$wp_adr")" = 0x00000000 ] || failed=1
	[ "$(read32 "$wp_ctrl")" = 0x00000000 ] || failed=1
	[ "$(read32 "$chker")" = "$baseline_chker" ] || failed=1
	[ "$(read32 "$chker_type")" = 0x00000000 ] || failed=1
	[ "$(read32 "$chker_adr")" = 0x00000000 ] || failed=1
	return "$failed"
}

finish() {
	status=$?
	trap - EXIT
	cleanup || status=1
	exit "$status"
}

trap finish EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM

mode=run
if [ "$#" -eq 1 ] && [ "$1" = --preflight ]; then
	mode=preflight
else
	[ "$#" -eq 0 ] || exit 2
fi
[ "$(id -u)" -eq 0 ] || exit 2
[ "$(uname -r)" = '3.18.41+' ] || exit 2
[ "$(cat /proc/sys/kernel/random/boot_id)" = "$expected_boot" ] || exit 2
[ "$(cat /sys/class/net/wlan0/carrier)" = 1 ] || exit 2
mpu=/sys/bus/platform/drivers/emi_mpu_ctrl/mpu_config
grep -Fx 'R18-> 0xbfa00000 to 0xbfa7ffff' "$mpu" >/dev/null
grep -Fx 'R23-> 0x0 to 0xffffffff' "$mpu" >/dev/null
[ "$(read32 "$wp_adr")" = 0x00000000 ] || exit 2
[ "$(read32 "$wp_ctrl")" = 0x00000000 ] || exit 2
[ "$(read32 "$chker")" = "$baseline_chker" ] || exit 2
[ "$(read32 "$chker_type")" = 0x00000000 ] || exit 2
[ "$(read32 "$chker_adr")" = 0x00000000 ] || exit 2
if [ "$mode" = preflight ]; then
	printf 'preflight=pass boot=%s\n' "$expected_boot"
	exit 0
fi

# One attempt in the current boot. This marker is tmpfs-only and is never
# removed by a retry, even if setup or the host link later fails.
mkdir -m 0700 "$marker"
printf 'boot=%s\n' "$expected_boot"
printf 'pre_chker=%s\n' "$baseline_chker"
modified=1
# Region 18 is 512 KiB at 0xbfa00000. WP_ADR is relative to 0x40000000.
# CTRL: range=19, read+write type=3; error, read/write suppression and IRQ
# bits all remain zero. CHKER only adds WP_EN to the observed baseline.
write32 "$wp_adr" 0x7fa00000
write32 "$wp_ctrl" 0x000000d3
[ "$(read32 "$wp_adr")" = 0x7fa00000 ] || exit 1
[ "$(read32 "$wp_ctrl")" = 0x000000d3 ] || exit 1
[ "$(read32 "$chker")" = "$baseline_chker" ] || exit 1
write32 "$chker" 0x00880000
sleep 1
printf 'hit_chker=%s\n' "$(read32 "$chker")"
printf 'hit_type=%s\n' "$(read32 "$chker_type")"
printf 'hit_addr=%s\n' "$(read32 "$chker_adr")"
printf 'boot_after=%s\n' "$(cat /proc/sys/kernel/random/boot_id)"
