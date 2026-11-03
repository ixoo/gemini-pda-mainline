#!/bin/sh
# The first Panfrost run, driven by the device custodian. Run from a directory
# holding the modules and gpu-job. It loads the modules in order, runs a finite
# job count, unloads, and records state after each step. Stops on the first
# failure and always tries to unload what it loaded.
#
#   gpu-test.sh probe [parent]   load, identify, unload
#   gpu-test.sh job [parent]     load, identify, up to JOBS jobs, unload
#   gpu-test.sh gles [parent]    load, identify, up to FRAMES shader frames, unload
#   gpu-test.sh load [parent]    load, identify, LOAD_SECONDS of shader load, unload
#
# The driver defaults to DVFS and idle power-off. Giving parent or KHZ selects a fixed
# clock instead: parent is mt6797_parent, 0 = clk26m, 1 = syspll_d3, and KHZ=442500 or
# 520000 runs from the MFGPLL. IDLE_OFF=0 keeps the domains on. GAP_MS waits between
# gles frames. COOL=1, in load mode, makes soc-thermal read 60 C from 20 s to 40 s of
# the run, above the 58 C passive trip, for its governor to cap the rate, and raises the
# run stop to 65 C for the whole run. It needs the zone's emul_temp. The true banks are
# logged, and emulation ends if a bank reaches 58 C, as the zone then reads a false value.
# LOG_RATES=1 logs each rate change. PIN_HZ, with DVFS=1, holds devfreq at one OPP.
# TOGGLE="LOW HIGH", with DVFS=1 in load mode, moves the rate between two OPPs every
# 100 ms under the load, so up and down steps of a chosen size run with the GPU busy.
# BURST, with GAP_MS, makes a load mode run wait GAP_MS after each BURST frames, then
# run LIGHT small frames, 40 ms apart, so the rate falls before the next burst.
# PERFCNT=1 adds panfrost unstable_ioctls=1 (which taints) and a counter window in load.
# Limits, from the vendor (2026-10-31-mt6797-thermal-management): SoC under its 55 C
# cooler exit to start (also enforced in the driver), and stop at 58 C during a run,
# its recovered policy's first CPU cooling trip, since no cooling device exists here.
# Battery stops at 46 C, where the vendor starts cutting charge current.
mode=${1:?probe, job, gles or load}; parent=${2:-}; JOBS=${JOBS:-100}; FRAMES=${FRAMES:-20}
LOAD_SECONDS=${LOAD_SECONDS:-60}; LOAD_SIZE=${LOAD_SIZE:-512}
START_MAX_MC=55000; RUN_MAX_MC=58000; BATTERY_MAX_MC=46000
[ -z "${COOL:-}" ] || RUN_MAX_MC=65000
here=$(cd "$(dirname "$0")" && pwd)
MODULES="clk-mt6797-mfg rt5735-regulator drm_panel_orientation_quirks drm drm_shmem_helper gpu-sched panfrost"

zone=; battery=
for z in /sys/class/thermal/thermal_zone*; do
  [ "$(cat "$z/type")" = soc-thermal ] && zone=$z/temp
  [ "$(cat "$z/type")" = battery-thermal ] && battery=$z/temp
done
[ -n "$zone" ] && [ -n "$battery" ] || { echo "no soc-thermal or battery-thermal zone"; exit 3; }

regs() {
  echo "--- regs: $1"
  for a in 10006180 10006184 10006334 10006338 1000633c 10006340 10006344 10006348 1000634c \
           10001220 10001228 10001094 10001fbc 10001fc0 10001fc4 10001fc8 10001fd8 10001fe4 \
           10000050 10000104 1000c240 1000c244 10007018; do
    printf '%s %s\n' "$a" "$(devmem 0x$a 32)"
  done
}
rail() {
  for r in /sys/class/regulator/regulator.*; do
    [ "$(cat "$r/name" 2>/dev/null)" = vgpu ] &&
      echo "vgpu state=$(cat "$r/state") microvolts=$(cat "$r/microvolts")"
  done
}
banks() {
  f=/sys/kernel/debug/mt6797-thermal-banks
  [ -e "$f" ] && echo "banks $(cut -d' ' -f1 /proc/uptime) $(cut -d' ' -f2 "$f" | tr '\n' ' ')"
}
devfreq() {
  for d in /sys/class/devfreq/*; do
    case "$d" in *gpu*)
      echo "devfreq cur=$(cat "$d/cur_freq") min=$(cat "$d/min_freq") max=$(cat "$d/max_freq") gov=$(cat "$d/governor")"
      cat "$d/trans_stat";;
    esac
  done
}
rpm() {
  banks
  devfreq
  echo "--- rpm: $1 uptime $(cut -d' ' -f1 /proc/uptime)"
  p=/sys/devices/platform/13040000.gpu/power
  for f in control runtime_status runtime_usage runtime_active_kids runtime_active_time runtime_suspended_time; do
    [ -e "$p/$f" ] && echo "$f=$(cat "$p/$f")"
  done
  ps=$(devmem 0x10006180 32); echo "PWR_STATUS=$ps"
  [ -e /sys/kernel/debug/pm_genpd/pm_genpd_summary ] &&
    grep -E 'mfg|13040000|genpd:' /sys/kernel/debug/pm_genpd/pm_genpd_summary
}
state() { echo "soc=$(cat "$zone") mC"; rail; regs "$1"; }

# Only what this run loaded, in reverse: a display driver may be using the DRM core.
loaded=
unload() {
  for m in $loaded; do
    rmmod "$m" || echo "rmmod $m failed"
  done
}

uname -r; cat /proc/sys/kernel/random/boot_id
t=$(cat "$zone"); echo "start soc=$t mC"
[ "$t" -lt "$START_MAX_MC" ] || { echo "too hot to start"; exit 2; }
state before
mark=$(dmesg | wc -l)

rc=0
for m in $MODULES; do
  if [ -d "/sys/module/$(echo "$m" | tr - _)" ]; then
    echo "=== $m already loaded"
    continue
  fi
  args=; [ "$m" = panfrost ] && args="${parent:+mt6797_parent=$parent mt6797_dvfs=0}${KHZ:+ mt6797_khz=$KHZ mt6797_dvfs=0}${IDLE_OFF:+ mt6797_idle_off=$IDLE_OFF}${LOG_RATES:+ mt6797_log_rates=1}${PERFCNT:+ unstable_ioctls=1}"
  echo "=== insmod $m $args"
  # shellcheck disable=SC2086 # args is a few words, none with a space
  insmod "$here/$m.ko" $args || { echo "insmod $m failed"; rc=1; break; }
  loaded="$m $loaded"
  [ "$m" = rt5735-regulator ] && { sleep 1; rail; }
done
dmesg | tail -n +$((mark + 1))
[ $rc = 0 ] && [ -e /dev/dri/renderD128 ] || { echo "no render node"; rc=1; }

if [ $rc = 0 ] && [ -n "${PIN_HZ:-}" ]; then
  for d in /sys/class/devfreq/*; do
    case "$d" in *gpu*)
      # devfreq accepts neither limit past the other, and the current limits are the whole table.
      echo "$PIN_HZ" > "$d/min_freq"; echo "$PIN_HZ" > "$d/max_freq"; sleep 1
      echo "pinned $PIN_HZ cur=$(cat "$d/cur_freq")"
      [ "$(cat "$d/cur_freq")" = "$PIN_HZ" ] || { echo "pin failed"; rc=1; };;
    esac
  done
fi
if [ $rc = 0 ]; then
  rpm just-loaded
  sleep 1
  rpm one-second-later
  state loaded
  if [ "$mode" = job ]; then jobs=$JOBS; else jobs=0; fi
  timeout 60 "$here/gpu-job" --zone "$zone" --jobs "$jobs" --max-mc "$RUN_MAX_MC"; rc=$?
  echo "gpu-job exit $rc"
  if [ "$mode" = gles ] && [ $rc = 0 ]; then
    timeout 120 "$here/mesa/ld-linux-aarch64.so.1" --library-path "$here/mesa" "$here/mesa/gpu-gles" \
      --zone "$zone" --battery-zone "$battery" --frames "$FRAMES" --max-mc "$RUN_MAX_MC" --gap-ms "${GAP_MS:-0}"; rc=$?
    echo "gpu-gles exit $rc"
  fi
  if [ "$mode" = load ] && [ $rc = 0 ]; then
    ( while :; do banks; sleep 5; done ) &
    sampler=$!
    toggler=
    cooler=
    if [ -n "${COOL:-}" ]; then
      for c in /sys/class/thermal/cooling_device*; do
        case "$(cat "$c/type")" in *gpu*) cdev=$c;; esac
      done
      emul=$(dirname "$zone")/emul_temp
      ( read_state() { echo "cooling $1 cur_state=$(cat "$cdev/cur_state") cur_freq=$(cat /sys/class/devfreq/*gpu*/cur_freq) soc=$(cat "$zone")"; banks; }
        sleep 20
        read_state before
        echo 60000 > "$emul"
        n=0
        while [ $n -lt 4 ]; do
          sleep 5; read_state emulating; n=$((n + 1))
          # Back to the true value: the tool stops itself if it is over the run limit.
          cut -d' ' -f2 /sys/kernel/debug/mt6797-thermal-banks | while read -r b; do
            [ "$b" -lt 58000 ] || { echo "true bank at $b mC"; echo 0 > "$emul"; }
          done
        done
        echo 0 > "$emul"
        sleep 5; read_state after ) &
      cooler=$!
    fi
    if [ -n "${TOGGLE:-}" ]; then
      # shellcheck disable=SC2086 # two words, split on purpose
      set -- $TOGGLE
      for d in /sys/class/devfreq/*; do
        case "$d" in *gpu*) df=$d;; esac
      done
      ( echo "$1" > "$df/min_freq"
        while :; do
          echo "$1" > "$df/max_freq"; sleep 0.1
          echo "$2" > "$df/max_freq"; sleep 0.1
        done ) &
      toggler=$!
    fi
    timeout $((LOAD_SECONDS + 30)) "$here/mesa/ld-linux-aarch64.so.1" --library-path "$here/mesa" \
      "$here/mesa/gpu-gles" --zone "$zone" --battery-zone "$battery" --seconds "$LOAD_SECONDS" \
      --size "$LOAD_SIZE" --max-mc "$RUN_MAX_MC" --battery-max-mc "$BATTERY_MAX_MC" \
      --perfcnt "${PERFCNT:-0}" --burst "${BURST:-0}" --gap-ms "${GAP_MS:-0}" --light "${LIGHT:-0}"; rc=$?
    echo "gpu-gles exit $rc"
    kill "$sampler"
    [ -z "$toggler" ] || kill "$toggler"
    [ -z "$cooler" ] || { kill "$cooler"; echo 0 > "$emul"; }
  fi
  rpm after-job
  sleep 1
  rpm one-second-after-job
  state after-job
fi

echo "=== unload"
unload
dmesg | tail -n +$((mark + 1))
# A job that faults and recovers still gives a correct image, so the tool's exit
# cannot see it. Fail on any GPU fault since this run began.
faults=$(dmesg | tail -n +$((mark + 1)) | grep -cE 'panfrost.*(fault|timeout|reset|error)|Oops|Call trace|WARNING')
echo "gpu faults in this run: $faults"
[ "$faults" = 0 ] || [ $rc != 0 ] || rc=5
state unloaded
echo "result rc=$rc"
exit $rc
