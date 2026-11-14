#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
#
# T4c on the station: t4c.sh [MHZ...]. Loads CPU8 and CPU9 with hashes at one
# A72 point after another (default 1495 up to 2522 MHz), HOLD seconds each,
# and samples once a second: every thermal zone, the battery's current and
# voltage, VPROC2 and VSRAM_B, and policy8. At the first limit it caps policy8
# at 845 MHz, stops the load and exits 1. Between points it waits for the SoC
# to cool to COOL. Runs after the six modules, with policy8 on userspace.
# Limits (env): SOC_LIMIT 70000, VBAT_MIN 3500000 uV, IBAT_MAX 2500000 uA,
# HOLD 60 s, COOL 45000. VBAT_START (uV), if set, is the least battery voltage
# at rest to start, for a run on battery. CPU_MHZ is the cpu-mhz tool (default
# /tmp/cpu-mhz). LOG (default /tmp/t4c.log) gets one line a second and is synced
# each time, so put it on persistent storage to keep it through a power cut.
set -u

CPU=${CPU:-/sys/devices/system/cpu}
P8=$CPU/cpufreq/policy8
THERMAL=${THERMAL:-/sys/class/thermal}
REGULATORS=${REGULATORS:-/sys/class/regulator}
BAT=${BAT:-/sys/class/power_supply/battery}
DMESG=${DMESG:-dmesg}
TOOL=${CPU_MHZ:-/tmp/cpu-mhz}
SOC_LIMIT=${SOC_LIMIT:-70000}
VBAT_MIN=${VBAT_MIN:-3500000}
IBAT_MAX=${IBAT_MAX:-2500000}
HOLD=${HOLD:-60}
COOL=${COOL:-45000}
LOG=${LOG:-/tmp/t4c.log}
VBAT_START=${VBAT_START:-0}
RUN=/tmp/t4c.run
BAD=/tmp/t4c.bad
FAULTS='WARNING|Oops|BUG:|Internal error|rcu_.*stall|self-detected|Sending NMI|failed to update|BUCKB|SRAM LDO|B PLL reads|coupl'
SAFE=845000

say() { echo "$(cut -d' ' -f1 /proc/uptime) $*" | tee -a "$LOG"; sync "$LOG" 2>/dev/null || sync; }

rail_path() {
	for r in "$REGULATORS"/regulator.*; do
		[ "$(cat "$r/name" 2>/dev/null)" = "$1" ] && { echo "$r/microvolts"; return; }
	done
}

# Cap first, then stop the load, so the A72s slow down before anything else.
halt() {
	echo $SAFE >"$P8/scaling_max_freq" 2>/dev/null
	echo $SAFE >"$P8/scaling_setspeed" 2>/dev/null
	rm -f "$RUN"
	say "STOP $*"
	wait
	exit 1
}

hash_on() { "$TOOL" "$1" hash | awk '$1 == "hash" { print $2 }'; }

# One worker per A72: hash until the run file goes, flag any wrong result.
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
	say "$1 cur=$(cat "$P8/scaling_cur_freq") vproc=$(cat "$VPROC") vsram=$(cat "$VSRAM") i=$i v=$v zones=$zones"
	[ "$soc" -lt "$SOC_LIMIT" ] || halt "soc $soc"
	[ "${i#-}" -le "$IBAT_MAX" ] || halt "battery current $i"
	[ "$v" -ge "$VBAT_MIN" ] || halt "battery voltage $v"
	[ ! -e "$BAD" ] || halt "hash mismatch $(cat "$BAD")"
	[ "$($DMESG | grep -cE "$FAULTS")" = "$BASE" ] || halt "new fault lines in dmesg"
	[ "$(cat "$CPU/online")" = 0-9 ] || halt "online $(cat "$CPU/online")"
}

POINTS=${*:-1495 1677 1885 2093 2158 2223 2262 2327 2392 2522}
rm -f "$RUN" "$BAD"
[ -x "$TOOL" ] || { say "STOP no cpu-mhz at $TOOL"; exit 1; }
[ "$(cat "$P8/scaling_governor")" = userspace ] || { say "STOP policy8 not on userspace"; exit 1; }
VPROC=$(rail_path vproc-big)
VSRAM=$(rail_path vsram_b)
[ -n "$VPROC" ] && [ -n "$VSRAM" ] || { say "STOP no vproc-big or vsram_b"; exit 1; }
v=$(cat "$BAT/voltage_now")
[ "$v" -ge "$VBAT_START" ] || { say "STOP battery at rest $v, below $VBAT_START"; exit 1; }
REF=$(hash_on 0)
[ -n "$REF" ] || { say "STOP reference hash failed"; exit 1; }
BASE=$($DMESG | grep -cE "$FAULTS")
trap 'halt "interrupted"' INT TERM
say "start points=$POINTS hold=$HOLD soc_limit=$SOC_LIMIT vbat_min=$VBAT_MIN ibat_max=$IBAT_MAX ref=$REF"
echo $SAFE >"$P8/scaling_setspeed"
for mhz in $POINTS; do
	t=0
	while [ "$(cat "$THERMAL/thermal_zone0/temp")" -ge "$COOL" ]; do
		sample cool
		sleep 1
		t=$((t + 1))
		[ "$t" -lt 600 ] || halt "did not cool below $COOL in 600 s"
	done
	echo $((mhz * 1000)) >"$P8/scaling_max_freq" 2>/dev/null
	echo $((mhz * 1000)) >"$P8/scaling_setspeed" || halt "setspeed $mhz refused"
	touch "$RUN"
	worker 8 &
	worker 9 &
	t=0
	while [ "$t" -lt "$HOLD" ]; do
		sleep 1
		t=$((t + 1))
		sample "load$mhz"
	done
	rm -f "$RUN"
	wait
	echo $SAFE >"$P8/scaling_setspeed"
	say "point $mhz held $HOLD s"
done
echo 2522000 >"$P8/scaling_max_freq"
say "end passed"
