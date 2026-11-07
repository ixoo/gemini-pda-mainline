#!/bin/busybox sh
# SPDX-License-Identifier: GPL-2.0-only
#
# One outdoor gnss-minihost session on the station, with no cable and no
# session, so it stops itself on the limits below. BIN holds gnss-minihost and
# params.txt; IMAGE is the DSP image gemian-firmware put in place. Output goes to the data partition, so that a crash
# leaves it behind. Output holds position: it stays private.
# Exit: 0 finished, 1 did not open, 2 a stop rule fired.
set -u

BIN=${BIN:-/run/gnss-outdoor}
IMAGE=${IMAGE:-/lib/firmware/mediatek/mt6797/gnss_dsp_6797.bin}
OUT=${OUT:-/mnt/data/station/gnss-outdoor}
DELAY=${DELAY:-180}
SECONDS_ON=${SECONDS_ON:-600}
SOC_LIMIT=75000
BATT_LIMIT=450
CAPACITY_MIN=30
FAULTS='STP link stopped|ssert[^=]|assert=[1-9]|Oops|WARNING|Call trace|BUG:|Internal error'
ROOT=${ROOT:-/sys}
BAT=$ROOT/class/power_supply/battery

say() { echo "$(cut -d' ' -f1 /proc/uptime) $*" >>"$OUT/monitor.log"; }
state() {
	soc=$(cat "$ROOT/class/thermal/thermal_zone0/temp")
	batt=$(cat "$BAT/temp")
	cap=$(cat "$BAT/capacity")
	why=
	[ "$soc" -ge $SOC_LIMIT ] && why="soc $soc"
	[ "$batt" -ge $BATT_LIMIT ] && why="battery temperature $batt"
	[ "$cap" -lt $CAPACITY_MIN ] && why="capacity $cap"
	[ -n "$soc" ] && [ -n "$batt" ] && [ -n "$cap" ] || why="unreadable limit"
}

umask 077
mkdir -p "$OUT" || exit 1
say "start boot=$(cut -c1-8 /proc/sys/kernel/random/boot_id) waiting $DELAY s"
sleep "$DELAY"

state
say "soc=$soc batt=$batt cap=$cap power=$(cat "$ROOT/class/power_supply/usb/online" 2>/dev/null)"
if [ -n "$why" ] || [ "$(cat "$ROOT/class/gnss/gnss0/type")" != MT6797 ]; then
	say "not opened: ${why:-gnss0 type}"
	touch "$OUT/done"
	exit 1
fi

mark=$(dmesg | wc -l)
echo "$mark" >"$OUT/dmesg.mark"
"$BIN/gnss-minihost" /dev/gnss0 "$BIN/params.txt" "$IMAGE" "$OUT/frames.log" "$SECONDS_ON" \
	>"$OUT/host.log" 2>&1 &
host=$!

reason=
s=0
while kill -0 "$host" 2>/dev/null; do
	sleep 1
	s=$((s + 1))
	if dmesg | tail -n "+$((mark + 1))" | grep -qE "$FAULTS"; then
		reason="kernel log"
		break
	fi
	[ $((s % 30)) = 0 ] || continue
	state
	sync
	say "t=$s soc=$soc batt=$batt cap=$cap volt=$(cat "$BAT/voltage_now") wlan=$(cat "$ROOT/class/net/wlan0/operstate" 2>/dev/null) bytes=$(wc -c <"$OUT/frames.log")"
	if [ -n "$why" ]; then
		reason=$why
		break
	fi
done

if [ -n "$reason" ]; then
	say "STOP $reason"
	kill "$host" 2>/dev/null
	i=0
	while [ $i -lt 8 ] && kill -0 "$host" 2>/dev/null; do
		sleep 1
		i=$((i + 1))
	done
	kill -KILL "$host" 2>/dev/null
fi
wait "$host"
status=$?
say "elapsed=$s host exit=$status"
echo "exit=$status" >>"$OUT/host.log"
dmesg | tail -n "+$((mark + 1))" >"$OUT/dmesg.txt"
sync
touch "$OUT/done"
[ -z "$reason" ] || exit 2
exit 0
