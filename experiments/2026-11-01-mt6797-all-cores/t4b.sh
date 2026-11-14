#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
#
# T4b on the station: t4b.sh up | down | hotplug MHZ. Runs on the device after
# the A72 module, the rail providers, the cluster clocks, cpufreq-dt and the CCI
# have loaded in that order, with policy8 on the userspace governor.
#   up, down     set every A72 point in turn and check it
#   hotplug MHZ  set MHZ, take CPU9 and CPU8 down and up, and check the return
# At each step it reads VPROC2 and VSRAM_B, measures CPU8 with cpu-mhz, hashes
# on CPU8 and CPU9 against CPU0, and stops at the first rule broken.
# CPU_MHZ is the cpu-mhz tool (default /tmp/cpu-mhz); CPU, REGS, SOC,
# REGULATORS and DMESG override paths for a dry run. Exit: 0 passed, 1 a stop.
# The log is /tmp/t4b.log.
set -u

CPU=${CPU:-/sys/devices/system/cpu}
P8=$CPU/cpufreq/policy8
REGS=${REGS:-/sys/kernel/debug/1001a000.clock-controller/registers}
SOC=${SOC:-/sys/class/thermal/thermal_zone0/temp}
REGULATORS=${REGULATORS:-/sys/class/regulator}
DMESG=${DMESG:-dmesg}
TOOL=${CPU_MHZ:-/tmp/cpu-mhz}
LOG=/tmp/t4b.log
SOC_LIMIT=75000
FAULTS='WARNING|Oops|BUG:|Internal error|rcu_.*stall|self-detected|Sending NMI|panfrost.*(timeout|fault)|failed to update|BUCKB|SRAM LDO|B PLL reads|not restored|not prepared|coupl'

# MHz and the table's VPROC2 in mV, from 0706 and 0775.
TABLE='338 880
676 880
845 880
1001 900
1131 930
1378 980
1495 1000
1677 1040
1885 1080
2093 1110
2158 1130
2223 1140
2262 1150
2327 1170
2392 1200
2522 1200'

say() { echo "$(cut -d' ' -f1 /proc/uptime) $*" | tee -a "$LOG"; }
stop() { say "STOP $*"; exit 1; }

rail() {
	for r in "$REGULATORS"/regulator.*; do
		[ "$(cat "$r/name" 2>/dev/null)" = "$1" ] && { cat "$r/microvolts"; return; }
	done
	echo 0
}

faults() { $DMESG | grep -cE "$FAULTS"; }
field() { tr ' ' '\n' <"$REGS" | sed -n "s/^$1=//p"; }

# cpu-mhz prints "hash H ms T" and "cpu C mhz M"; keep H and M.
hash_on() { "$TOOL" "$1" hash | awk '$1 == "hash" { print $2 }'; }
mhz_on() { "$TOOL" "$1" | awk '$3 == "mhz" { print $4 }'; }

hashes() {
	for c in 8 9; do
		h=$(hash_on "$c")
		[ -n "$h" ] || stop "hash on cpu$c failed"
		[ "$h" = "$REF" ] || stop "hash on cpu$c: $h, wanted $REF"
	done
}

# The state at one point: rate, rails, the clock driver, CPU8's clock, hashes.
check() {
	mhz=$1
	mv=$2
	khz=$((mhz * 1000))
	cur=$(cat "$P8/scaling_cur_freq")
	vproc=$(rail vproc-big)
	vsram=$(rail vsram_b)
	brate=$(field b_rate)
	faulted=$(field faulted)
	meas=$(mhz_on 8)
	[ -n "$meas" ] || stop "cpu-mhz 8 failed"
	soc=$(cat "$SOC")
	say "mhz=$mhz cur=$cur vproc=$vproc vsram=$vsram b_rate=$brate meas=$meas soc=$soc online=$(cat "$CPU/online")"
	[ "$cur" = "$khz" ] || stop "policy8 at $cur, wanted $khz"
	[ "$vproc" = $((mv * 1000)) ] || stop "vproc-big $vproc, wanted $((mv * 1000))"
	if [ "$vproc" -ge 1200000 ]; then
		[ "$vsram" = 1200000 ] || stop "vsram_b $vsram at the 1.2 V top"
	else
		[ "$vsram" -ge $((vproc + 10000)) ] || stop "vsram_b $vsram below vproc + 10 mV"
	fi
	{ [ "$vsram" -ge 1000000 ] && [ "$vsram" -le 1200000 ]; } || stop "vsram_b $vsram out of 1.0-1.2 V"
	[ "$brate" = $((khz * 1000)) ] || stop "b_rate $brate, wanted $((khz * 1000))"
	[ "$faulted" = 0 ] || stop "clock driver faulted"
	{ [ $((meas * 100)) -ge $((mhz * 95)) ] && [ $((meas * 100)) -le $((mhz * 105)) ]; } ||
		stop "cpu8 measured $meas MHz for $mhz"
	[ "$soc" -lt $SOC_LIMIT ] || stop "soc $soc"
	hashes
	[ "$(faults)" = "$BASE" ] || stop "new fault lines in dmesg"
}

set_point() {
	echo $(($1 * 1000)) >"$P8/scaling_setspeed" || stop "setspeed $1 refused"
	sleep 1
	check "$1" "$2"
}

[ $# -ge 1 ] || stop "usage: t4b.sh up | down | hotplug MHZ"
[ -x "$TOOL" ] || stop "no cpu-mhz at $TOOL"
[ -r "$REGS" ] || stop "no clock driver registers"
[ "$(cat "$CPU/online")" = 0-9 ] || stop "online $(cat "$CPU/online"), wanted 0-9"
[ "$(cat "$P8/related_cpus")" = "8 9" ] || stop "policy8 covers $(cat "$P8/related_cpus")"
[ "$(cat "$P8/scaling_governor")" = userspace ] || stop "policy8 is not on userspace"
REF=$(hash_on 0)
[ -n "$REF" ] || stop "reference hash failed"
BASE=$(faults)
say "start $* ref=$REF faults=$BASE"

case $1 in
up)
	echo "$TABLE" | while read -r mhz mv; do set_point "$mhz" "$mv"; done || exit 1
	;;
down)
	echo "$TABLE" | sort -rn | while read -r mhz mv; do set_point "$mhz" "$mv"; done || exit 1
	;;
hotplug)
	[ $# -eq 2 ] || stop "usage: t4b.sh hotplug MHZ"
	mv=$(echo "$TABLE" | awk -v m="$2" '$1 == m { print $2 }')
	[ -n "$mv" ] || stop "$2 MHz is not a table point"
	set_point "$2" "$mv"
	before=$(rail vproc-big)
	echo 0 >"$CPU/cpu9/online" || stop "cpu9 did not go down"
	echo 0 >"$CPU/cpu8/online" || stop "cpu8 did not go down"
	[ "$(cat "$CPU/online")" = 0-7 ] || stop "online $(cat "$CPU/online"), wanted 0-7"
	[ "$(rail vproc-big)" = "$before" ] || stop "vproc-big moved while the A72s were down"
	echo 1 >"$CPU/cpu8/online" || stop "cpu8 did not come back"
	echo 1 >"$CPU/cpu9/online" || stop "cpu9 did not come back"
	sleep 1
	$DMESG | grep -E 'cluster prepared again|A72 clock restored' | tail -2 | tee -a "$LOG"
	check "$2" "$mv"
	;;
*)
	stop "usage: t4b.sh up | down | hotplug MHZ"
	;;
esac
say "end $* passed"
