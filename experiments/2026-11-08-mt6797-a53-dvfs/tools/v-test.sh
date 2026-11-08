#!/bin/sh
# SPDX-License-Identifier: MIT
#
# A53 DVFS device test (experiments/2026-11-08-mt6797-a53-dvfs, V1-V9), one stage per call.
# Run as root on the station RAM root; cpu-mhz in /tmp/cf; modules from the image.
# Written by the device custodian; expectations after D1 added here.
set -u
STAGE=${1:-}
MHZ=/tmp/cf/cpu-mhz; M=/lib/modules/$(uname -r)
CF=/sys/devices/system/cpu/cpufreq; REF=/tmp/v-hash-ref; TOL=5
DEV=1001a000.clock-controller
stop() { echo "STOP: $*"; dmesg | grep -iE 'da921|da9213|vsram|mcusys|cpufreq|cci|devfreq|thermal|coupl' | tail -n 30; exit 1; }
regs() { r=/sys/kernel/debug/$DEV/registers; [ -r "$r" ] || stop "no $r"; cat "$r"; grep -q 'faulted=0' "$r" || stop "driver faulted"; }
soc_temp() { for z in /sys/class/thermal/thermal_zone*; do [ "$(cat $z/type)" = soc-thermal ] && { cat $z/temp; return; }; done; echo 0; }
check_temp() { t=$(soc_temp); echo "soc_temp_mC $t"; [ "$t" -lt 80000 ] || stop "SoC at $t"; }
check_log() {
  if dmesg | grep -iE 'da921|da9213|vsram|mcusys|cpufreq|cpu-freq|cci|devfreq|coupl' |
     grep -vE 'cpufreq_dt: failed to find data for cpu[89]$|cpu[89] has no OPPs' |
     grep -qiE 'fault|failed|error|behind the driver|did not hold|not granted|refusing|Oops|BUG|WARNING'; then stop "fault in the kernel log"; fi
}
rg() { for r in /sys/class/regulator/regulator.*; do [ "$(cat $r/name 2>/dev/null)" = "$1" ] && { cat $r/microvolts; return; }; done; echo none; }
# Table voltages (mV) of the station-dvfs points, by kHz (CPU) or MHz (CCI).
mv_ll() { case $1 in 1547000|1495000|1443000) echo 1200;; 1391000) echo 1180;; 1339000) echo 1160;;
  1274000) echo 1140;; 1222000) echo 1120;; 1118000) echo 1070;; 1014000) echo 1040;; 897000) echo 1000;;
  806000) echo 970;; 715000) echo 940;; 624000) echo 900;; 481000) echo 870;; 338000) echo 860;;
  221000) echo 840;; *) echo 0;; esac; }
mv_l() { case $1 in 2002000|1950000) echo 1200;; 1885000) echo 1190;; 1820000) echo 1170;; 1755000) echo 1160;;
  1703000) echo 1130;; 1625000) echo 1110;; 1495000) echo 1070;; 1352000) echo 1040;; 1209000) echo 1000;;
  1092000) echo 970;; 962000) echo 940;; 832000) echo 900;; 650000|468000) echo 860;; 325000) echo 840;;
  *) echo 0;; esac; }
mv_cci() { case $1 in 988|975|936) echo 1200;; 910) echo 1190;; 884) echo 1170;; 845) echo 1150;;
  819) echo 1140;; 754) echo 1100;; 676) echo 1060;; 611) echo 1020;; 533) echo 970;; 481) echo 940;;
  416) echo 910;; 325) echo 890;; 234) echo 860;; *) echo 0;; esac; }
CCI=/sys/class/devfreq/cci
max() { [ "$1" -ge "$2" ] && echo "$1" || echo "$2"; }
# vsram_code CODE: the VSRAM_L selector's millivolts
vsram_mv() { case $1 in 0) echo 1050;; 1) echo 600;; 2) echo 700;; *) echo $(( 900 + ($1 - 3) * 25 ));; esac; }
volts() { # real hardware: DA9214 0xd7 and INFRACFG VSRAM words
  sel=$(( $(i2cget -fy 6 0x68 0xd7) & 0x7f )); vp=$(( 300 + sel * 10 ))
  w1=$(devmem 0x10001f9c 32); w2=$(devmem 0x10001fa0 32); code=$(( w1 & 0xf )); vs=$(vsram_mv $code)
  echo "hw vproc1_mV $vp (sel 0x$(printf %x $sel)) vsram_mV $vs (f9c $w1 fa0 $w2) sysfs vproc1 $(rg vproc1) vsram_l $(rg vsram_l)"
  [ "$w1" = "$w2" ] || stop "VSRAM words differ"
  [ $(( w1 )) -eq $(( code * 0x01010101 )) ] || stop "VSRAM word $w1 is not one selector"
  [ "$vs" -ge "$vp" ] || stop "VSRAM_L $vs below VPROC1 $vp"
  [ "$vs" -ge 1100 ] || stop "VSRAM_L $vs below its 1100 mV floor"
  [ "$(rg vproc1)" = "none" ] || [ "$(rg vproc1)" = "$((vp*1000))" ] || stop "vproc1 sysfs $(rg vproc1) != hw $vp mV"
}
# expect: with the policies steady, VPROC1 is the highest table voltage of its
# consumers and VSRAM_L is VPROC1 + 10 mV rounded up to 25 mV, within 1100-1200 mV.
expect() {
  e=$(max "$(mv_ll "$(cat $CF/policy0/scaling_cur_freq)")" "$(mv_l "$(cat $CF/policy4/scaling_cur_freq)")")
  [ -d $CCI ] && e=$(max "$e" "$(mv_cci $(( $(cat $CCI/cur_freq) / 1000000 )))")
  s=$(( e + 10 )); s=$(( 900 + (s - 900 + 24) / 25 * 25 )); [ $s -lt 1100 ] && s=1100; [ $s -gt 1200 ] && s=1200
  echo "expect vproc1_mV $e vsram_mV $s"
  [ "$vp" = "$e" ] || stop "VPROC1 $vp mV, expected $e"
  [ "$vs" = "$s" ] || stop "VSRAM_L $vs mV, expected $s"
}
measure() { m=$($MHZ $1 5 | awk '{print $4}'); echo "cpu$1 want_khz $2 measured_mhz $m"
  awk -v m=$m -v k=$2 -v t=$TOL 'BEGIN{d=m*1000-k; if(d<0)d=-d; exit !(d*100<=k*t)}' || stop "cpu$1 at $m MHz, wanted $2 kHz"; }
hash_ok() { h=$($MHZ $1 hash | awk '{print $2}'); echo "cpu$1 hash $h"; [ "$h" = "$(cat $REF)" ] || { stop "cpu$1 hash $h"; }; }
set_khz() { p=$CF/policy$1; echo $2 > $p/scaling_setspeed || stop "setspeed $2 refused"; cur=$(cat $p/scaling_cur_freq); echo "policy$1 set $2 cur $cur"; [ "$cur" = "$2" ] || stop "policy$1 reports $cur after $2"; check_log; }
step() { pol=$1; a=$2; b=$3; shift 3; for k in "$@"; do set_khz $pol $k; grep -E '^pll|^muxsel' /sys/kernel/debug/$DEV/registers; volts; expect; measure $a $k; measure $b $k; hash_ok $a; check_temp; done; }
case $(cat /sys/devices/system/cpu/online) in 0-7|0-9) ;; *) stop "CPUs online $(cat /sys/devices/system/cpu/online)";; esac
case "$STAGE" in
v1) uname -r; cat /proc/sys/kernel/random/boot_id; for c in 0 3 4 7; do $MHZ $c 5; done
    $MHZ 0 hash | awk '{print $2}' > $REF; echo "hash_ref $(cat $REF)"; hash_ok 4; volts; check_temp
    [ -d $CF/policy0 ] && stop "cpufreq already has policies" ;;
v2) insmod $M/da9213-legacy-regulator.ko || stop "da9213 refused"; insmod $M/mt6797-vsram-regulator.ko || stop "vsram refused"; sleep 1
    dmesg | grep -iE 'da921|da9213|vsram|coupl' | tail -8
    for r in /sys/class/regulator/regulator.*; do n=$(cat $r/name); case $n in vproc*|vsram*) echo "$n $(cat $r/microvolts 2>/dev/null) $(cat $r/constraint_flags 2>/dev/null)";; esac; done
    volts; check_log ;;
v3) insmod $M/clk-mt6797-mcusys.ko || stop "mcusys refused"; sleep 1; dmesg | grep mcusys | tail -5; regs; volts; check_log ;;
v4) insmod $M/cpufreq-dt.ko || stop "cpufreq-dt refused"; sleep 1
    for p in 0 4; do d=$CF/policy$p; [ -d $d ] || stop "no policy$p"; for f in related_cpus scaling_governor scaling_available_frequencies scaling_cur_freq; do echo "policy$p $f $(cat $d/$f)"; done; done
    [ "$(xargs < $CF/policy0/related_cpus)" = "0 1 2 3" ] || stop policy0; [ "$(xargs < $CF/policy4/related_cpus)" = "4 5 6 7" ] || stop policy4
    # Both policies set their OPP at load (0675): CPU0-3 stay at 897 MHz, CPU4-7 leave
    # the unlisted 1274 MHz for 1352 MHz; VPROC1 1040 mV (0xd7 = 0x4a), VSRAM_L 1100 mV.
    [ "$(cat $CF/policy0/scaling_cur_freq)" = 897000 ] || stop "policy0 not at 897000"
    [ "$(cat $CF/policy4/scaling_cur_freq)" = 1352000 ] || stop "policy4 not at 1352000"
    regs; volts; expect; measure 3 897000; measure 4 1352000; hash_ok 0; hash_ok 4; check_log
    for c in /sys/class/thermal/cooling_device*; do echo "$(basename $c) $(cat $c/type) max $(cat $c/max_state)"; done ;;
v5) echo userspace > $CF/policy0/scaling_governor
    step 0 1 3 1014000 1118000 1222000 1274000 1339000 1391000 1443000 1495000 1547000 \
      1495000 1443000 1391000 1339000 1274000 1222000 1118000 1014000 897000 806000 715000 624000 481000 338000 221000 \
      338000 481000 624000 715000 806000 897000 221000 1547000 221000 897000 ;;
v6) echo userspace > $CF/policy4/scaling_governor
    step 4 4 7 1352000 1495000 1625000 1703000 1755000 1820000 1885000 1950000 2002000 \
      1950000 1885000 1820000 1755000 1703000 1625000 1495000 1352000 1209000 1092000 962000 832000 650000 468000 325000 \
      468000 650000 832000 962000 1092000 1209000 325000 2002000 325000 1209000 ;;
v7) insmod $M/mtk-cci-devfreq.ko || stop "cci refused"; sleep 2; D=$CCI
    dmesg | grep -iE 'cci|devfreq' | tail -5
    [ -d $D ] || stop "no CCI devfreq (probe deferred?)"
    dmesg | grep -i 'mtk-ccifreq\|cci' | grep -qi 'defer' && stop "CCI probe deferred"
    echo "cci $D gov $(cat $D/governor) cur $(cat $D/cur_freq)"; volts
    for pair in "221000 325000" "897000 325000" "221000 1209000" "1547000 2002000" "897000 1209000"; do
      ll=${pair% *}; l=${pair#* }
      echo $ll > $CF/policy0/scaling_setspeed; echo $l > $CF/policy4/scaling_setspeed; sleep 1
      cur=$(cat $D/cur_freq); rate=$(sed -n 's/^pll2 .* rate=\([0-9]*\) .*/\1/p' /sys/kernel/debug/$DEV/registers)
      echo "ll $ll l $l cci $cur pll2_rate $rate"; volts; expect
      [ "$(mv_cci $(( cur / 1000000 )))" != 0 ] || stop "CCI at $cur, not a table point"
      awk -v r="$rate" -v c="$cur" 'BEGIN{d=r-c; if(d<0)d=-d; exit !(d*200<=c)}' || stop "CCI PLL $rate Hz, devfreq $cur Hz"
      case $pair in "221000 325000") [ "$cur" = 234000000 ] || stop "CCI $cur at the lowest points";;
        "1547000 2002000") [ "$cur" = 988000000 ] || stop "CCI $cur at the highest points";; esac
    done
    for p in 0 4; do echo schedutil > $CF/policy$p/scaling_governor; echo "policy$p trans_before $(cat $CF/policy$p/stats/total_trans)"; done
    sleep 10; for p in 0 4; do echo "policy$p idle_cur $(cat $CF/policy$p/scaling_cur_freq)"; done; echo "cci idle $(cat $D/cur_freq)"
    pids=""; for c in 0 1 2 3 4 5 6 7; do (end=$(($(date +%s)+15)); while [ "$(date +%s)" -lt "$end" ]; do $MHZ $c hash; done > /tmp/v-load-$c) & pids="$pids $!"; done
    sleep 5; for p in 0 4; do echo "policy$p load_cur $(cat $CF/policy$p/scaling_cur_freq)"; done; echo "cci load $(cat $D/cur_freq)"; volts
    wait $pids; sleep 10; for p in 0 4; do echo "policy$p idle_cur $(cat $CF/policy$p/scaling_cur_freq) trans_after $(cat $CF/policy$p/stats/total_trans)"; done; echo "cci idle $(cat $D/cur_freq)"
    for c in 0 1 2 3 4 5 6 7; do n=$(awk '{print $2}' /tmp/v-load-$c | sort -u); echo "cpu$c load_hashes $(wc -l < /tmp/v-load-$c) distinct $n"; [ "$n" = "$(cat $REF)" ] || stop "cpu$c load hash"; done
    regs; volts; check_log; check_temp ;;
v8) z=""; for d in /sys/class/thermal/thermal_zone*; do [ "$(cat $d/type)" = soc-thermal ] && z=$d; done
    for p in 0 4; do echo performance > $CF/policy$p/scaling_governor; done
    echo 62000 > $z/emul_temp || stop "emul_temp refused"
    for i in 1 2 3 4 5 6 7 8 9 10; do sleep 1; echo "t+$i max0 $(cat $CF/policy0/scaling_max_freq) max4 $(cat $CF/policy4/scaling_max_freq)"; done
    echo 0 > $z/emul_temp
    for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do sleep 1; echo "t+$i max0 $(cat $CF/policy0/scaling_max_freq) max4 $(cat $CF/policy4/scaling_max_freq)"; done
    [ "$(cat $CF/policy0/scaling_max_freq)" = 1547000 ] && [ "$(cat $CF/policy4/scaling_max_freq)" = 2002000 ] || stop "cooling did not release"
    for p in 0 4; do echo schedutil > $CF/policy$p/scaling_governor; done; volts; regs; check_log ;;
v9) for p in 0 4; do echo schedutil > $CF/policy$p/scaling_governor; done
    pids=""; for c in 0 1 2 3 4 5 6 7; do (end=$(($(date +%s)+600)); while [ "$(date +%s)" -lt "$end" ]; do $MHZ $c hash; done > /tmp/v9-load-$c) & pids="$pids $!"; done
    i=0; while [ $i -lt 60 ]; do sleep 10; i=$((i+1)); t=$(soc_temp)
      echo "t+$((i*10)) soc $t f0 $(cat $CF/policy0/scaling_cur_freq) f4 $(cat $CF/policy4/scaling_cur_freq) max0 $(cat $CF/policy0/scaling_max_freq) max4 $(cat $CF/policy4/scaling_max_freq) $(volts | cut -d' ' -f1-6)"
      [ "$t" -lt 80000 ] || { kill $pids; stop "SoC at $t"; }; done
    wait $pids
    for c in 0 1 2 3 4 5 6 7; do n=$(awk '{print $2}' /tmp/v9-load-$c | sort -u); echo "cpu$c load_hashes $(wc -l < /tmp/v9-load-$c) distinct $n"; [ "$n" = "$(cat $REF)" ] || stop "cpu$c load hash"; done
    for p in 0 4; do cat $CF/policy$p/stats/time_in_state | tr '\n' ' '; echo; done; regs; volts; check_log; check_temp ;;
*) echo "usage: $0 v1..v9"; exit 2 ;;
esac
echo "PASS $STAGE"
