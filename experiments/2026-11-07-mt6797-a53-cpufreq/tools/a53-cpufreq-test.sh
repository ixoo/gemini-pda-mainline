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

stop() {
	echo "STOP: $*"
	dmesg | grep -E 'mcusys|cpufreq|cpu-freq|thermal' | tail -n 30
	exit 1
}

regs() {
	r=""
	for d in /sys/kernel/debug/*.clock-controller; do
		[ -d "$d" ] && r=$d
	done
	[ -n "$r" ] || { echo "regs: no debugfs node"; return; }
	cat "$r/registers" || stop "register readback failed"
	grep -q 'faulted=0' "$r/registers" || stop "driver faulted"
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
	if dmesg | grep -E 'mcusys|cpufreq|cpu-freq' |
	   grep -qiE 'did not hold|not granted|not released|stopped at PCW|behind the driver|refusing|Oops|BUG|WARNING'; then
		stop "fault in the kernel log"
	fi
}

# measure CPU KHZ: measured clock within TOL percent of KHZ
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
		regs | grep -E "^pll|^muxsel"
		measure "$a" "$k"
		measure "$b" "$k"
		hash_ok "$a"
		check_temp
	done
}

case "${1:-}" in
t0)
	uname -r
	cat /proc/sys/kernel/random/boot_id
	for a in 0x10000104 0x10220744 0x1022074c; do
		echo "$a $(devmem $a 32)"
	done
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
	regs
	measure 0 897000
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
	step 0 0 3 806000 715000 624000 481000 338000 221000 \
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
