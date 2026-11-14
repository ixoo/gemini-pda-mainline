#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
#
# A72 soak on the station: soak.sh load|idle SECONDS. Runs on the device from
# RAM, after the A72 module has loaded, and stops itself on the limits below.
# Optional traffic, run every 15 min: PING_TARGET, WGET_URL, TONE_CMD.
# SOC_LIMIT (millidegrees, default 75000) is the SoC stop.
# Exit: 0 finished, 1 a stop rule fired.
set -u

MODE=$1
SECONDS_TO_RUN=$2
SOC_LIMIT=${SOC_LIMIT:-75000}
BATT_LIMIT=450
CAPACITY_MIN=30
FAULTS='WARNING|Oops|BUG:|Internal error|rcu_preempt detected|self-detected|Sending NMI|pwrap.*(err|fail)'
LOG=/tmp/soak-$MODE.log
STOP=/tmp/soak-$MODE.stop
DATA=/tmp/soak.dat
BAT=/sys/class/power_supply/battery

now() { cut -d. -f1 /proc/uptime; }
say() { echo "$(cut -d' ' -f1 /proc/uptime) $*" | tee -a "$LOG"; }
cpu_ticks() { awk -v c="cpu$1" '$1 == c { s = 0; for (i = 2; i <= NF; i++) s += $i; print s }' /proc/stat; }

# Hash one file over and over and compare, so a wrong result counts as a fault.
worker() {
	cpu=$1
	rounds=0
	while [ ! -e "$STOP" ] && [ "$(now)" -lt "$END" ]; do
		got=$(sha256sum <"$DATA")
		if [ "$got" != "$WANT" ]; then
			say "STOP hash mismatch on cpu$cpu round $rounds: $got"
			touch "$STOP"
			return 1
		fi
		rounds=$((rounds + 1))
	done
	say "cpu$cpu rounds=$rounds"
}

# Workers re-enter this script so that taskset pins the whole of each one.
if [ "${SOAK_WORKER:-}" != "" ]; then
	worker "$SOAK_WORKER"
	exit $?
fi

END=$(($(now) + SECONDS_TO_RUN))
export END
rm -f "$STOP"

# Each transfer ends before the next step, so no download outlives this loop.
traffic() {
	while [ ! -e "$STOP" ] && [ "$(now)" -lt "$END" ]; do
		if [ -n "${PING_TARGET:-}" ]; then
			say "ping $(ping -c 5 "$PING_TARGET" | grep 'packets transmitted')"
		fi
		if [ -n "${WGET_URL:-}" ]; then
			wget -q -T 60 -O /dev/null "$WGET_URL"
			say "wget rc=$?"
		fi
		if [ -n "${TONE_CMD:-}" ]; then
			$TONE_CMD >/dev/null 2>&1
			say "tone rc=$?"
		fi
		i=0
		while [ $i -lt 900 ] && [ ! -e "$STOP" ] && [ "$(now)" -lt "$END" ]; do
			sleep 5
			i=$((i + 5))
		done
	done
}

PIDS=
if [ "$MODE" = load ]; then
	dd if=/dev/urandom of="$DATA" bs=1M count=64 2>/dev/null
	WANT=$(taskset -c 0 sha256sum <"$DATA")
	export WANT
	say "want $WANT"
	for c in 7 8 9; do
		SOAK_WORKER=$c taskset -c "$c" "$0" "$MODE" "$SECONDS_TO_RUN" &
		PIDS="$PIDS $!"
	done
fi
traffic &
TRAFFIC=$!

result=0
taint0=$(cat /proc/sys/kernel/tainted)
faults0=$(dmesg | grep -cE "$FAULTS")
last8=$(cpu_ticks 8)
last9=$(cpu_ticks 9)
tick=0
while [ "$(now)" -lt "$END" ] && [ ! -e "$STOP" ]; do
	sleep 10
	tick=$((tick + 1))
	c8=$(cpu_ticks 8)
	c9=$(cpu_ticks 9)
	soc=$(cat /sys/class/thermal/thermal_zone0/temp)
	batt=$(cat $BAT/temp)
	cap=$(cat $BAT/capacity)
	why=
	# /proc/stat moves about 1000 ticks per 10 s; a quiet sample is a frozen CPU.
	[ $((c8 - last8)) -lt 100 ] && why="cpu8 frozen"
	[ $((c9 - last9)) -lt 100 ] && why="cpu9 frozen"
	[ "$soc" -ge $SOC_LIMIT ] && why="soc $soc"
	[ "$batt" -ge $BATT_LIMIT ] && why="battery temperature $batt"
	[ "$cap" -lt $CAPACITY_MIN ] && why="capacity $cap"
	[ "$(cat /sys/devices/system/cpu/online)" = 0-9 ] || why="online changed"
	last8=$c8
	last9=$c9
	if [ $((tick % 6)) = 0 ] || [ -n "$why" ]; then
		taint=$(cat /proc/sys/kernel/tainted)
		faults=$(dmesg | grep -cE "$FAULTS")
		[ "$taint" = "$taint0" ] || why="taint $taint"
		[ "$faults" = "$faults0" ] || why="fault lines $faults"
		say "$MODE soc=$soc batt=$batt cap=$cap volt=$(cat $BAT/voltage_now) taint=$taint faults=$faults"
	fi
	if [ -n "$why" ]; then
		say "STOP $why"
		result=1
		touch "$STOP"
	fi
done

touch "$STOP"
for p in $PIDS; do
	wait "$p" || result=1
done
wait "$TRAFFIC"
killall wget 2>/dev/null
[ -z "$(pidof wget)" ] || { say "wget still running"; result=1; }
[ "$MODE" = load ] && rm -f "$DATA"
say "end result=$result online=$(cat /sys/devices/system/cpu/online)"
grep -E '^cpu[89] ' /proc/stat | tee -a "$LOG"
exit $result
