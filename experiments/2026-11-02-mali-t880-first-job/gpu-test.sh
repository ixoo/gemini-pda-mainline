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
# parent is the panfrost mt6797_parent value, 0 = clk26m (default), 1 = syspll_d3.
# PERFCNT=1 adds panfrost unstable_ioctls=1 (which taints) and a counter window in load.
# Limits, from the vendor's adaptive cooler (2026-10-31-mt6797-thermal-management):
# SoC under its 55 C exit to start (also enforced in the driver), and its 75 C
# target during a run, since no cooling device exists here. Battery stops at 46 C,
# where the vendor starts cutting charge current.
mode=${1:?probe, job, gles or load}; parent=${2:-0}; JOBS=${JOBS:-100}; FRAMES=${FRAMES:-20}
LOAD_SECONDS=${LOAD_SECONDS:-60}; LOAD_SIZE=${LOAD_SIZE:-512}
START_MAX_MC=55000; RUN_MAX_MC=75000; BATTERY_MAX_MC=46000
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
rpm() {
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

unload() {
  for m in panfrost gpu-sched drm_shmem_helper drm drm_panel_orientation_quirks rt5735-regulator clk-mt6797-mfg; do
    [ -d "/sys/module/$(echo "$m" | tr - _)" ] && { rmmod "$m" || echo "rmmod $m failed"; }
  done
}

uname -r; cat /proc/sys/kernel/random/boot_id
t=$(cat "$zone"); echo "start soc=$t mC"
[ "$t" -lt "$START_MAX_MC" ] || { echo "too hot to start"; exit 2; }
state before
mark=$(dmesg | wc -l)

rc=0
for m in $MODULES; do
  args=; [ "$m" = panfrost ] && args="mt6797_parent=$parent${PERFCNT:+ unstable_ioctls=1}"
  echo "=== insmod $m $args"
  # shellcheck disable=SC2086 # args is a few words, none with a space
  insmod "$here/$m.ko" $args || { echo "insmod $m failed"; rc=1; break; }
  [ "$m" = rt5735-regulator ] && { sleep 1; rail; }
done
dmesg | tail -n +$((mark + 1))
[ $rc = 0 ] && [ -e /dev/dri/renderD128 ] || { echo "no render node"; rc=1; }

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
      --zone "$zone" --battery-zone "$battery" --frames "$FRAMES" --max-mc "$RUN_MAX_MC"; rc=$?
    echo "gpu-gles exit $rc"
  fi
  if [ "$mode" = load ] && [ $rc = 0 ]; then
    timeout $((LOAD_SECONDS + 30)) "$here/mesa/ld-linux-aarch64.so.1" --library-path "$here/mesa" \
      "$here/mesa/gpu-gles" --zone "$zone" --battery-zone "$battery" --seconds "$LOAD_SECONDS" \
      --size "$LOAD_SIZE" --max-mc "$RUN_MAX_MC" --battery-max-mc "$BATTERY_MAX_MC" \
      --perfcnt "${PERFCNT:-0}"; rc=$?
    echo "gpu-gles exit $rc"
  fi
  rpm after-job
  sleep 1
  rpm one-second-after-job
  state after-job
fi

echo "=== unload"
unload
dmesg | tail -n +$((mark + 1))
state unloaded
echo "result rc=$rc"
exit $rc
