#!/bin/sh
# SPDX-License-Identifier: MIT
# Compare battery draw awake, with the backlight off, and with the console blanked.
# Meant to run on battery with USB out, so it detaches from the shell, runs on a fixed
# schedule and logs to a file. It only writes the backlight's power state and the
# framebuffer's blank state, and restores both. Markers on the console show progress.
# usage: display-power.sh LOG [SECONDS_PER_PHASE] [ROUNDS]
#   run through: setsid sh display-power.sh /run/log 60 2 </dev/null >/dev/null 2>&1 &
set -u
log=$1
secs=${2:-60}
rounds=${3:-2}
exec >> "$log" 2>&1
B=/sys/class/backlight/backlight
G=/sys/class/power_supply/battery

say() { echo "$1" > /dev/tty0; echo "marker $1"; }
sample() { # phase
	i=0
	while [ "$i" -lt "$secs" ]; do
		echo "$1 $(cut -d' ' -f1 /proc/uptime) cur $(cat $G/current_now) v $(cat $G/voltage_now) ch $(cat $G/charge_counter) st $(cat $G/status)"
		sleep 1
		i=$((i + 1))
	done
}
regs() { # phase
	echo "$1 regs CG0 $(devmem 0x14000100 32) CG1 $(devmem 0x14000110 32) PWM_EN $(devmem 0x1100f000 32) CON1 $(devmem 0x1100f014 32) DBG $(devmem 0x1100f028 32) MOD $(devmem 0x1401f02c 32) PWR $(devmem 0x10006180 32) GPIO_MODE62 $(devmem 0x10005370 32) GPIO_DO62 $(devmem 0x10005100 32) GPIO_DIR62 $(devmem 0x10005000 32) GPIO_DO60_62 $(devmem 0x10005130 32) bl_power $(cat $B/bl_power) brightness $(cat $B/brightness) usb $(cat /sys/class/power_supply/*/online 2>/dev/null | tr '\n' ' ')"
}

echo "start $(cat /proc/sys/kernel/random/boot_id) $(uname -r) mutex $(sha256sum /sys/module/mtk_mutex/srcversion 2>/dev/null | cut -c1-8) tainted $(cat /proc/sys/kernel/tainted)"
say "display-power: unplug USB now; 60 s to start"
sleep 60
cat $G/capacity
r=1
while [ "$r" -le "$rounds" ]; do
	say "display-power $r: awake"
	sleep 3
	regs "awake$r"
	sample "awake$r"
	say "display-power $r: backlight off"
	sleep 1
	echo 4 > $B/bl_power
	sleep 3
	regs "bloff$r"
	sample "bloff$r"
	echo 0 > $B/bl_power
	echo 4 > /sys/class/graphics/fb0/blank
	sleep 3
	regs "blank$r"
	sample "blank$r"
	echo 0 > /sys/class/graphics/fb0/blank
	sleep 2
	r=$((r + 1))
done
say "display-power: awake, control"
sleep 3
regs control
sample control
echo 0 > $B/bl_power
say "display-power: done, plug USB back in"
echo "tainted $(cat /proc/sys/kernel/tainted)"
dmesg | grep -i -E 'Timeout|WARNING|sleep failed|\*ERROR\*' | tail -5
echo finished
