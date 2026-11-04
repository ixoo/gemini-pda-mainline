#!/bin/sh
# SPDX-License-Identifier: MIT
# T0: which addresses answer on I2C1, with no sensor module loaded. One register
# read per address, each once. A pointer byte and a read, no register write. Stops
# at the first failure that isn't a plain no-ACK, since that would be a bus fault.
# Run on the station: sh sensors-t0.sh
set -u

I2C1=/sys/bus/platform/devices/11008000.i2c
echo "uname $(uname -r) boot $(cat /proc/sys/kernel/random/boot_id)"
if grep -qE '^(bmi160|stk3310)' /proc/modules; then
	echo "STOP a sensor module is loaded"
	exit 1
fi
bus=
for d in "$I2C1"/i2c-*; do
	[ -e "$d" ] && bus=${d##*/i2c-}
done
if [ -z "$bus" ]; then
	echo "STOP no I2C1 adapter"
	exit 1
fi
echo "i2c1 bus=$bus"
for d in /sys/bus/platform/devices/11007000.i2c/i2c-*; do
	echo "i2c0 ${d##*/}"
done
for d in /sys/bus/i2c/devices/"$bus"-*; do
	[ -e "$d" ] && echo "client ${d##*/} $(cat "$d/name")"
done

grep -qs debugfs /proc/mounts || mount -t debugfs none /sys/kernel/debug
for pins in /sys/kernel/debug/pinctrl/*/pinmux-pins; do
	grep -E '^pin (55|56|63|65|88) ' "$pins"
done
grep -E 'gpio-(55|56|63|65|88) |^ *(55|56|63|65|88):' /sys/kernel/debug/gpio

mark=$(dmesg | wc -l)
for pair in 0x69:0x00 0x48:0x3e 0x48:0x3f 0x68:0x00 0x30:0x20 \
	0x77:0xd0 0x5f:0x0f 0x6a:0x0f 0x6b:0x0f; do
	addr=${pair%:*}
	reg=${pair#*:}
	out=$(i2cget -y "$bus" "$addr" "$reg" b 2>&1)
	rc=$?
	echo "$addr reg $reg rc=$rc $out"
	if [ "$rc" -ne 0 ]; then
		case "$out" in
		*"No such device or address"*) ;;
		*)
			echo "STOP not a plain no-ACK"
			break
			;;
		esac
	fi
done
echo "--- new dmesg"
dmesg | sed "1,${mark}d"
grep -E '11008000|i2c' /proc/interrupts
