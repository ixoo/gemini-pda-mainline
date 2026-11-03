#!/bin/sh
# SPDX-License-Identifier: MIT
# T5: GPU frames on the panel. With the display modules loaded and a test frame
# already shown once, load Panfrost, render into display buffers and flip them for
# SECONDS, then unload the GPU modules. The display modules stay loaded.
# Limits are the GPU record's: SoC under 55 C to start, stop at 58 C, battery 46 C.
# usage: display-t5.sh GPU_MODULE_DIR MESA_DIR SECONDS
set -u
dir=$1
mesa=$2
secs=$3
zone=; battery=
for z in /sys/class/thermal/thermal_zone*; do
	[ "$(cat "$z/type")" = soc-thermal ] && zone=$z/temp
	[ "$(cat "$z/type")" = battery-thermal ] && battery=$z/temp
done
[ -n "$zone" ] && [ -n "$battery" ] || { echo "no thermal zones"; exit 3; }

uname -r
cat /proc/sys/kernel/random/boot_id
echo "soc $(cat "$zone") battery $(cat "$battery") tainted $(cat /proc/sys/kernel/tainted)"
[ "$(cat "$zone")" -lt 55000 ] || { echo "too hot to start"; exit 2; }
ls /dev/dri/card* >/dev/null 2>&1 || { echo "display not bound"; exit 6; }

for m in clk-mt6797-mfg rt5735-regulator drm_shmem_helper gpu-sched panfrost; do
	echo "insmod $m"
	insmod "$dir/$m.ko" || { echo "FAILED insmod $m"; dmesg | tail -30; exit 5; }
	[ "$m" = rt5735-regulator ] && sleep 1
done
ls /dev/dri
dmesg | grep -i panfrost | tail -8

"$mesa/ld-linux-aarch64.so.1" --library-path "$mesa" "$mesa/gpu-scanout" "$secs" "$zone" 58000 &
pid=$!
rc=
while kill -0 "$pid" 2>/dev/null; do
	sleep 5
	b=$(cat "$battery")
	echo "$(cut -d' ' -f1 /proc/uptime) soc $(cat "$zone") battery $b"
	if [ "$b" -ge 46000 ]; then
		echo "battery stop"
		kill "$pid"
		rc=2
	fi
done
wait "$pid"
t=$?
[ -n "$rc" ] || rc=$t
echo "gpu-scanout rc=$t"
grep -E 'ovl|rdma|dsi|panfrost|gpu|job|mmu' /proc/interrupts
dmesg | grep -i -E 'panfrost|timed out|underflow|nobody cared|WARNING|Unable|\*ERROR\*|fault' | tail -30
for m in panfrost gpu-sched drm_shmem_helper rt5735-regulator clk-mt6797-mfg; do
	rmmod "$m" || { echo "FAILED rmmod $m"; rc=7; }
done
echo "tainted $(cat /proc/sys/kernel/tainted) soc $(cat "$zone")"
echo "finished rc=$rc"
exit "$rc"
