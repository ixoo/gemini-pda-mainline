#!/bin/sh
# SPDX-License-Identifier: MIT
#
# A53 cpufreq device test, one stage per call. Run as root on the station from
# a directory holding cpu-mhz, clk-mt6797-mcusys.ko and cpufreq-dt.ko.
#
#   t0  read-only baseline: TOPCKGEN/MCUCFG words, clocks, hashes, temperature
#   t2  load clk-mt6797-mcusys (FHCTL init, no frequency change)
#   t3  load cpufreq-dt (performance: CPU4-7 1274 -> 1209 MHz)
#   t4  CPU0-3 sweep, 897 -> 221 -> 897 MHz, then two long jumps
#   t5a CPU4-7 1209 <-> 1092 MHz (no post-divider change)
#   t5b CPU4-7 sweep below 1092 MHz (post-divider change through MAINPLL)
#   t6  schedutil on both clusters through idle, load, idle
#   t7  cooling: emulate 62 C on the SoC zone, then release
#   t8  unload and reload both modules
#
# Every stage stops at the first fault and prints STOP with the reason.
set -u

HERE=$(cd "$(dirname "$0")" && pwd)
MHZ="$HERE/cpu-mhz"
CF=/sys/devices/system/cpu/cpufreq
REF=/tmp/a53-cpufreq-hash-ref
TOL=5	# percent allowed between a measured and a requested clock
DEV=1001a000.clock-controller

stop() {
	echo "STOP: $*"
	dmesg | grep -E 'mcusys|cpufreq|cpu-freq|thermal' | tail -n 30
	exit 1
}

regs() {
	r=/sys/kernel/debug/$DEV/registers
	[ -r "$r" ] || stop "no debugfs node $r"
	cat "$r" || stop "register readback failed"
	grep -q 'faulted=0' "$r" || stop "driver faulted"
}

# sync_dcm_ok WORD: each enabled A53 sync DCM divider allows the lowest OPP
# (the vendor keeps divider <= MHz / 70; CPU0-3 221 MHz, CPU4-7 325 MHz)
sync_dcm_ok() {
	sync_dcm_cluster "$1" 0 8 221
	sync_dcm_cluster "$1" 1 16 325
}

# sync_dcm_cluster WORD CLUSTER EN_BIT LOWEST_OPP_MHZ
sync_dcm_cluster() {
	en=$(( ($1 >> $3) & 1 ))
	sel=$(( ($1 >> ($3 + 1)) & 31 ))
	echo "sync_dcm cluster$2 en $en div $sel floor_mhz $((en * sel * 70))"
	[ $((en * sel * 70)) -le "$4" ] ||
		stop "cluster$2 sync DCM divider $sel above the $4 MHz OPP"
}

soc_temp() {
	for z in /sys/class/thermal/thermal_zone*; do
		[ "$(cat "$z/type")" = soc-thermal ] && { cat "$z/temp"; return; }
	done
	echo 0
}

check_temp() {
	t=$(soc_temp)
	echo "soc_temp_mC $t"
	[ "$t" -lt 80000 ] || stop "SoC at $t mC"
}

check_log() {
	# cpufreq-dt logs this for each A72 it leaves out; it is not a fault.
	if dmesg | grep -E 'mcusys|cpufreq|cpu-freq' |
	   grep -vE 'cpufreq_dt: failed to find data for cpu[89]$' |
	   grep -qiE 'did not hold|not granted|not released|stopped at PCW|behind the driver|refusing|failed|error|Oops|BUG|WARNING'; then
		stop "fault in the kernel log"
	fi
}

# measure CPU KHZ: measured clock within TOL percent of KHZ. CPU0 takes most
# interrupts and can read several percent low, so CPU0-3 are measured on CPU1
# and CPU3.
measure() {
	m=$("$MHZ" "$1" 5 | awk '{print $4}')
	echo "cpu$1 want_khz $2 measured_mhz $m"
	awk -v m="$m" -v k="$2" -v t="$TOL" \
		'BEGIN { d = m * 1000 - k; if (d < 0) d = -d; exit !(d * 100 <= k * t) }' ||
		stop "cpu$1 at $m MHz, wanted $2 kHz"
}

hash_ok() {
	h=$("$MHZ" "$1" hash | awk '{print $2}')
	echo "cpu$1 hash $h"
	[ "$h" = "$(cat "$REF")" ] || stop "cpu$1 hash $h differs from $(cat "$REF")"
}

policy() {
	echo "$CF/policy$1"
}

set_khz() {
	p=$(policy "$1")
	echo "$2" > "$p/scaling_setspeed" || stop "setspeed $2 refused"
	cur=$(cat "$p/scaling_cur_freq")
	echo "policy$1 set $2 cur $cur"
	[ "$cur" = "$2" ] || stop "policy$1 reports $cur after $2"
	check_log
}

# step POLICY CPU_A CPU_B KHZ...
step() {
	pol=$1; a=$2; b=$3
	shift 3
	for k in "$@"; do
		set_khz "$pol" "$k"
		regs > /tmp/a53-cpufreq-regs
		grep -E "^pll|^muxsel" /tmp/a53-cpufreq-regs
		measure "$a" "$k"
		measure "$b" "$k"
		hash_ok "$a"
		check_temp
	done
}

# Screen blanking takes CPU1-7 offline; every stage needs CPU0-7 (the A72s,
# CPU8-9, may be online too).
online=$(cat /sys/devices/system/cpu/online)
case $online in
0-7|0-9) ;;
*) stop "CPUs online $online, not 0-7 or 0-9 (disable console blanking)" ;;
esac

case "${1:-}" in
t0)
	uname -r
	cat /proc/sys/kernel/random/boot_id
	for a in 0x10000104 0x10220744 0x1022074c; do
		echo "$a $(devmem $a 32)"
	done
	sync_dcm_ok "$(devmem 0x10220744 32)"
	[ -r /sys/kernel/debug/clk/mainpll/clk_rate ] &&
		echo "mainpll_hz $(cat /sys/kernel/debug/clk/mainpll/clk_rate)"
	ls "$CF" 2>&1
	for c in 0 3 4 7; do "$MHZ" $c 5; done
	"$MHZ" 0 hash | awk '{print $2}' > "$REF"
	echo "hash_ref $(cat "$REF")"
	hash_ok 4
	check_temp
	;;
t2)
	insmod "$HERE/clk-mt6797-mcusys.ko" || stop "clk-mt6797-mcusys refused"
	dmesg | grep mcusys | tail -n 5
	[ -e /sys/bus/platform/drivers/clk-mt6797-mcusys/$DEV ] ||
		stop "clk-mt6797-mcusys did not bind $DEV"
	regs
	check_log
	;;
t3)
	insmod "$HERE/cpufreq-dt.ko" || stop "cpufreq-dt refused"
	sleep 1
	for p in 0 4; do
		d=$(policy $p)
		[ -d "$d" ] || stop "no policy$p"
		for f in related_cpus scaling_governor scaling_available_frequencies \
			 cpuinfo_transition_latency scaling_cur_freq; do
			echo "policy$p $f $(cat "$d/$f")"
		done
	done
	[ "$(xargs < "$(policy 0)/related_cpus")" = "0 1 2 3" ] ||
		stop "policy0 is not CPU0-3"
	[ "$(xargs < "$(policy 4)/related_cpus")" = "4 5 6 7" ] ||
		stop "policy4 is not CPU4-7"
	regs
	measure 3 897000
	measure 4 1209000
	hash_ok 0
	hash_ok 4
	check_log
	for c in /sys/class/thermal/cooling_device*; do
		echo "$(basename "$c") $(cat "$c/type") max $(cat "$c/max_state")"
	done
	;;
t4)
	echo userspace > "$(policy 0)/scaling_governor"
	step 0 1 3 806000 715000 624000 481000 338000 221000 \
		338000 481000 624000 715000 806000 897000 221000 897000
	;;
t5a)
	echo userspace > "$(policy 4)/scaling_governor"
	step 4 4 7 1092000 1209000 1092000 1209000
	;;
t5b)
	echo userspace > "$(policy 4)/scaling_governor"
	step 4 4 7 1092000 962000 832000 650000 468000 325000 \
		468000 650000 832000 962000 1092000 1209000 325000 1209000
	;;
t6)
	for p in 0 4; do
		echo schedutil > "$(policy $p)/scaling_governor"
		echo "policy$p trans_before $(cat "$(policy $p)/stats/total_trans")"
	done
	sleep 10
	for p in 0 4; do echo "policy$p idle_cur $(cat "$(policy $p)/scaling_cur_freq")"; done
	pids=""
	for c in 0 1 2 3 4 5 6 7; do
		(end=$(($(date +%s) + 15)); while [ "$(date +%s)" -lt "$end" ]; do
			"$MHZ" $c hash; done > /tmp/a53-load-$c) &
		pids="$pids $!"
	done
	sleep 5
	for p in 0 4; do echo "policy$p load_cur $(cat "$(policy $p)/scaling_cur_freq")"; done
	# shellcheck disable=SC2086 # one word per PID
	wait $pids
	sleep 10
	for p in 0 4; do
		echo "policy$p idle_cur $(cat "$(policy $p)/scaling_cur_freq") trans_after $(cat "$(policy $p)/stats/total_trans")"
		cat "$(policy $p)/stats/time_in_state"
	done
	for c in 0 1 2 3 4 5 6 7; do
		n=$(awk '{print $2}' /tmp/a53-load-$c | sort -u)
		echo "cpu$c load_hashes $(wc -l < /tmp/a53-load-$c) distinct $n"
		[ "$n" = "$(cat "$REF")" ] || stop "cpu$c load hash $n"
	done
	regs
	check_log
	check_temp
	;;
t7)
	z=""
	for d in /sys/class/thermal/thermal_zone*; do
		[ "$(cat "$d/type")" = soc-thermal ] && z=$d
	done
	[ -n "$z" ] || stop "no soc-thermal zone"
	for c in "$z"/cdev*; do
		case "$(basename "$c")" in *_*) continue;; esac
		echo "$(basename "$c") $(cat "$c/type") trip $(cat "${c}_trip_point")"
	done
	for p in 0 4; do echo performance > "$(policy $p)/scaling_governor"; done
	echo 62000 > "$z/emul_temp" || stop "emul_temp refused"
	for i in 1 2 3 4 5 6 7 8 9 10; do
		sleep 1
		echo "t+$i max0 $(cat "$(policy 0)/scaling_max_freq") max4 $(cat "$(policy 4)/scaling_max_freq") cur0 $(cat "$(policy 0)/scaling_cur_freq") cur4 $(cat "$(policy 4)/scaling_cur_freq")"
	done
	echo 0 > "$z/emul_temp"
	for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
		sleep 1
		echo "t+$i max0 $(cat "$(policy 0)/scaling_max_freq") max4 $(cat "$(policy 4)/scaling_max_freq")"
	done
	[ "$(cat "$(policy 0)/scaling_max_freq")" = 897000 ] &&
	[ "$(cat "$(policy 4)/scaling_max_freq")" = 1209000 ] ||
		stop "cooling did not release"
	regs
	check_log
	;;
t8)
	for p in 0 4; do echo performance > "$(policy $p)/scaling_governor"; done
	rmmod cpufreq-dt || stop "rmmod cpufreq-dt"
	rmmod clk-mt6797-mcusys || stop "rmmod clk-mt6797-mcusys"
	ls "$CF"
	insmod "$HERE/clk-mt6797-mcusys.ko" || stop "reload clk-mt6797-mcusys"
	insmod "$HERE/cpufreq-dt.ko" || stop "reload cpufreq-dt"
	sleep 1
	dmesg | grep mcusys | tail -n 3
	for p in 0 4; do
		echo schedutil > "$(policy $p)/scaling_governor"
		echo "policy$p $(cat "$(policy $p)/scaling_governor") $(cat "$(policy $p)/scaling_cur_freq")"
	done
	regs
	check_log
	;;
*)
	echo "usage: $0 t0|t2|t3|t4|t5a|t5b|t6|t7|t8" >&2
	exit 2
	;;
esac
echo "PASS ${1}"
