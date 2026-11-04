#!/bin/sh
# SPDX-License-Identifier: MIT
# Sample the STK3x1x through IIO direct reads, loading nothing. Prints uptime, the
# light and proximity raw values and the interrupt count, twice a second.
# Run on the station: sh sensors-als.sh SECONDS
set -eu

seconds=$1
dev=
for d in /sys/bus/iio/devices/iio:device*; do
	[ "$(cat "$d/name")" = stk3310 ] && dev=$d
done
[ -n "$dev" ] || { echo "no stk3310 IIO device"; exit 1; }
echo "# light_scale $(cat "$dev/in_illuminance_scale") proximity_scale $(cat "$dev/in_proximity_scale")"
echo "# t light proximity irq"
n=$((seconds * 2))
while [ "$n" -gt 0 ]; do
	irq=$(awk '/stk3310_event/ { s = 0; for (i = 2; i <= NF && $i ~ /^[0-9]+$/; i++) s += $i; print s }' /proc/interrupts)
	echo "$(cut -d' ' -f1 /proc/uptime) $(cat "$dev/in_illuminance_raw") $(cat "$dev/in_proximity_raw") ${irq:-none}"
	n=$((n - 1))
	sleep 0.5
done
