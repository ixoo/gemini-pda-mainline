#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
#
# T7 on the station: t7.sh SECONDS (of uptime). Loads all ten CPUs with hashes under the
# governors and thermal policy already set, and samples once a second: every
# thermal zone, each policy's rate, the CCI, the four CPU rails, and the
# battery's current and voltage. At the first limit it caps the A72s at
# 845 MHz, stops the load and exits 1. Runs after the six modules, with the
# policies on schedutil and the SoC zone on the power allocator.
# Limits (env): SOC_LIMIT 80000, VBAT_MIN 3500000 uV, IBAT_MAX 2500000 uA,
# BATT_LIMIT 450 (battery temperature, tenths of C).
# VBAT_START (uV), if set, is the least battery voltage at rest to start.
# CPU_MHZ is the cpu-mhz tool (default /tmp/cpu-mhz). LOG (default
# /tmp/t7.log) gets one line a second, synced, so put it on persistent storage.
set -u

CPU=${CPU:-/sys/devices/system/cpu}
THERMAL=${THERMAL:-/sys/class/thermal}
REGULATORS=${REGULATORS:-/sys/class/regulator}
DEVFREQ=${DEVFREQ:-/sys/class/devfreq}
BAT=${BAT:-/sys/class/power_supply/battery}
DMESG=${DMESG:-dmesg}
TOOL=${CPU_MHZ:-/tmp/cpu-mhz}
SOC_LIMIT=${SOC_LIMIT:-80000}
VBAT_MIN=${VBAT_MIN:-3500000}
IBAT_MAX=${IBAT_MAX:-2500000}
VBAT_START=${VBAT_START:-0}
BATT_LIMIT=${BATT_LIMIT:-450}
LOG=${LOG:-/tmp/t7.log}
RUN=/tmp/t7.run
BAD=/tmp/t7.bad
FAULTS='WARNING|Oops|BUG:|Internal error|rcu_.*stall|self-detected|Sending NMI|panfrost.*(timeout|fault)|failed to update|BUCKB|SRAM LDO|B PLL reads|not restored|not prepared|coupl'
SAFE=845000
P=$CPU/cpufreq

say() { echo "$(cut -d' ' -f1 /proc/uptime) $*" | tee -a "$LOG"; sync "$LOG" 2>/dev/null || sync; }

rail_path() {
	for r in "$REGULATORS"/regulator.*; do
		[ "$(cat "$r/name" 2>/dev/null)" = "$1" ] && { echo "$r/microvolts"; return; }
	done
	echo /dev/null
}

# Cap the A72s first, then stop the load.
halt() {
	echo $SAFE >"$P/policy8/scaling_max_freq" 2>/dev/null
	rm -f "$RUN"
	say "STOP $*"
	wait
	exit 1
}

hash_on() { "$TOOL" "$1" hash | awk '$1 == "hash" { print $2 }'; }

worker() {
	while [ -e "$RUN" ]; do
		h=$(hash_on "$1")
		[ -e "$RUN" ] || break
		[ "$h" = "$REF" ] || { echo "cpu$1 $h" >"$BAD"; break; }
	done
}

sample() {
	zones=
	for z in "$THERMAL"/thermal_zone*; do
		zt=$(cat "$z/temp" 2>/dev/null) || continue
		zones="$zones ${z##*thermal_zone}:$zt"
	done
	soc=$(cat "$THERMAL/thermal_zone0/temp")
	i=$(cat "$BAT/current_now")
	v=$(cat "$BAT/voltage_now")
	bt=$(cat "$BAT/temp")
	cci=$(cat "$CCI" 2>/dev/null)
	say "p0=$(cat "$P/policy0/scaling_cur_freq") p4=$(cat "$P/policy4/scaling_cur_freq") p8=$(cat "$P/policy8/scaling_cur_freq") cci=$cci vproc1=$(cat "$VPROC1") vsram_l=$(cat "$VSRAML") vproc2=$(cat "$VPROC2") vsram_b=$(cat "$VSRAMB") i=$i v=$v bt=$bt zones=$zones"
	[ "$soc" -lt "$SOC_LIMIT" ] || halt "soc $soc"
	[ "${i#-}" -le "$IBAT_MAX" ] || halt "battery current $i"
	[ "$v" -ge "$VBAT_MIN" ] || halt "battery voltage $v"
	[ "$bt" -lt "$BATT_LIMIT" ] || halt "battery temperature $bt"
	[ ! -e "$BAD" ] || halt "hash mismatch $(cat "$BAD")"
	[ "$($DMESG | grep -cE "$FAULTS")" = "$BASE" ] || halt "new fault lines in dmesg"
	[ "$(cat "$CPU/online")" = 0-9 ] || halt "online $(cat "$CPU/online")"
}

[ $# -eq 1 ] || { echo "usage: t7.sh SECONDS"; exit 1; }
rm -f "$RUN" "$BAD"
[ -x "$TOOL" ] || { say "STOP no cpu-mhz at $TOOL"; exit 1; }
for p in policy0 policy4 policy8; do
	[ "$(cat "$P/$p/scaling_governor")" = schedutil ] || { say "STOP $p not on schedutil"; exit 1; }
done
[ "$(cat "$CPU/online")" = 0-9 ] || { say "STOP online $(cat "$CPU/online")"; exit 1; }
VPROC1=$(rail_path vproc1)
VSRAML=$(rail_path vsram_l)
VPROC2=$(rail_path vproc-big)
VSRAMB=$(rail_path vsram_b)
CCI=/dev/null
for d in "$DEVFREQ"/*; do
	case $(readlink -f "$d/device" 2>/dev/null) in *cci*) CCI=$d/cur_freq ;; esac
done
v=$(cat "$BAT/voltage_now")
[ "$v" -ge "$VBAT_START" ] || { say "STOP battery at rest $v, below $VBAT_START"; exit 1; }
REF=$(hash_on 0)
[ -n "$REF" ] || { say "STOP reference hash failed"; exit 1; }
BASE=$($DMESG | grep -cE "$FAULTS")
trap 'halt "interrupted"' INT TERM
say "start seconds=$1 soc_limit=$SOC_LIMIT batt_limit=$BATT_LIMIT vbat_min=$VBAT_MIN ibat_max=$IBAT_MAX boost=$(cat "$P/boost" 2>/dev/null) p8_max=$(cat "$P/policy8/scaling_max_freq") ref=$REF"
touch "$RUN"
for c in 0 1 2 3 4 5 6 7 8 9; do worker "$c" & done
# Run for SECONDS of uptime, not a count of samples: a sample takes over a second.
END=$(($(cut -d. -f1 /proc/uptime) + $1))
while [ "$(cut -d. -f1 /proc/uptime)" -lt "$END" ]; do
	sleep 1
	sample
done
rm -f "$RUN"
wait
say "end passed after $1 s"
