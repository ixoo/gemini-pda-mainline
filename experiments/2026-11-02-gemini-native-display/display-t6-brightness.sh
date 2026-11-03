#!/bin/sh
# SPDX-License-Identifier: MIT
# Does a brightness change latch once PWM0 is back in mutex 0? Needs no one at the
# device. Run with the mtk-mutex without patch 0510 loaded and the output on. It sets
# the one bit that patch cleared, the value the loader leaves, then steps brightness and
# reads the live level. Restores brightness. Exits non-zero if the level did not follow.
set -u
B=/sys/class/backlight/backlight
rd() { devmem "$1" 32; }
show() { echo "$1 $(cut -d' ' -f1 /proc/uptime) brightness $(cat $B/brightness) bl_power $(cat $B/bl_power) EN $(rd 0x1100f000) CON1 $(rd 0x1100f014) LIVE $(rd 0x1100f028) M_EN $(rd 0x1401f020) MOD $(rd 0x1401f02c) tainted $(cat /proc/sys/kernel/tainted)"; }
fail=0
step() { # level
	echo "$1" > $B/brightness
	sleep 1
	show "level$1"
	[ "$(($(rd 0x1100f028) & 0x1fff))" -eq "$1" ] || { echo "LIVE did not follow $1"; fail=1; }
}

saved=$(cat $B/brightness)
show before
[ "$(rd 0x1401f020)" = 0x00000001 ] || { echo "STOP: mutex off, no frames: is the lid closed or the console blanked?"; exit 3; }
mod=$(rd 0x1401f02c)
devmem 0x1401f02c 32 $((mod | 0x04000000))
sleep 1
show bit-set
for l in 128 384 700 512; do step "$l"; done

echo 4 > /sys/class/graphics/fb0/blank
sleep 2
show blanked
[ "$(($(rd 0x1100f000) & 1))" -eq 0 ] || { echo "EN still on while blanked"; fail=1; }
echo 0 > /sys/class/graphics/fb0/blank
sleep 2
show woken
for l in 256 512; do step "$l"; done

echo "$saved" > $B/brightness
sleep 1
show restored
dmesg | grep -i -E 'Timeout|WARNING|sleep failed|\*ERROR\*' | tail -5
echo "finished fail=$fail"
exit "$fail"
