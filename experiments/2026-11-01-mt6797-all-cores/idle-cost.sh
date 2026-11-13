#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
#
# A72 idle cost on battery: idle-cost.sh SECONDS. Runs on the device from RAM,
# after the A72 module has loaded and with nothing else running. It waits for
# USB power to go, then measures three idle phases of SECONDS each: A72s online,
# both down, online again. With L=1 it measures five: all ten online, A72s
# down, CPU4-7 down as well, CPU4-7 back, A72s back. Each phase skips its first
# 60 s. Exit: 0 finished, 1 a stop. The log is /tmp/idle-cost.log.
set -u

PHASE=$1
SETTLE=${SETTLE:-60}
CPU=${CPU:-/sys/devices/system/cpu}
PS=${PS:-/sys/class/power_supply}
SOC=${SOC:-/sys/class/thermal/thermal_zone0/temp}
BAT=$PS/battery
LOG=/tmp/idle-cost.log
SOC_LIMIT=75000
L=${L:-0}

say() { echo "$(cut -d' ' -f1 /proc/uptime) $*" | tee -a "$LOG"; }
stop() { say "STOP $*"; exit 1; }

# Any power supply other than the battery that reads online.
external() {
	for d in "$PS"/*; do
		[ "$d" = "$BAT" ] && continue
		[ -r "$d/online" ] && [ "$(cat "$d/online")" = 1 ] && return 0
	done
	return 1
}

set_a72() {
	if [ "$1" = up ]; then
		echo 1 > "$CPU/cpu8/online" || stop "cpu8 did not come back"
		echo 1 > "$CPU/cpu9/online" || stop "cpu9 did not come back"
	else
		echo 0 > "$CPU/cpu9/online" || stop "cpu9 did not go down"
		echo 0 > "$CPU/cpu8/online" || stop "cpu8 did not go down"
	fi
	[ "$(cat "$CPU/online")" = "$2" ] || stop "online $(cat "$CPU/online"), wanted $2"
}

set_l() {
	if [ "$1" = up ]; then
		for c in 4 5 6 7; do
			echo 1 > "$CPU/cpu$c/online" || stop "cpu$c did not come back"
		done
	else
		for c in 7 6 5 4; do
			echo 0 > "$CPU/cpu$c/online" || stop "cpu$c did not go down"
		done
	fi
	[ "$(cat "$CPU/online")" = "$2" ] || stop "online $(cat "$CPU/online"), wanted $2"
}

phase() {
	name=$1
	t=0
	while [ $t -lt "$SETTLE" ]; do sleep 10; t=$((t + 10)); done
	c0=$(cat "$BAT/charge_counter")
	t=0
	while [ $t -lt "$PHASE" ]; do
		sleep 10
		t=$((t + 10))
		external && stop "external power returned"
		soc=$(cat "$SOC")
		[ "$soc" -lt $SOC_LIMIT ] || stop "soc $soc"
		say "$name i=$(cat "$BAT/current_now") v=$(cat "$BAT/voltage_now") soc=$soc online=$(cat "$CPU/online")"
	done
	say "$name charge_counter $c0 $(cat "$BAT/charge_counter") over $PHASE s"
}

[ -r "$BAT/current_now" ] && [ -r "$BAT/charge_counter" ] || stop "no gauge"
[ "$(cat "$CPU/online")" = 0-9 ] || stop "online $(cat "$CPU/online"), wanted 0-9"
say "waiting for USB power to go, up to 300 s"
t=0
while external; do
	sleep 5
	t=$((t + 5))
	[ $t -lt 300 ] || stop "USB power never went"
done
say "on battery"

phase online
set_a72 down 0-7
phase down
if [ "$L" = 1 ]; then
	set_l down 0-3
	phase llonly
	set_l up 0-7
	phase down2
fi
set_a72 up 0-9
phase online2

awk '$2 ~ /^online|^down|^llonly/ && $3 ~ /^i=/ { sub("i=", "", $3); n[$2]++; s[$2] += $3 }
     END { for (p in n) printf "mean %s %d uA over %d samples\n", p, s[p] / n[p], n[p] }' \
	"$LOG" | tee -a "$LOG"
say "end, plug USB back in"
