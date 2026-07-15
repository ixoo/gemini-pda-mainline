#!/usr/bin/env bash

# Read-only external-display inventory. Do not open /dev/hdmitx or issue any
# bridge/HDMI ioctl; the vendor node is unbound in the captured system.

set -u
export LC_ALL=C

section() { printf '\n[%s]\n' "$1"; }

section i2c
for dev in /sys/bus/i2c/devices/3-0039 /sys/bus/i2c/devices/3-0050; do
	[ -d "$dev" ] || continue
	echo "device=$dev"
	for file in name modalias uevent; do
		[ -r "$dev/$file" ] || continue
		echo "--$file"
		sed -n '1,24p' "$dev/$file"
	done
	if [ -L "$dev/driver" ]; then
		printf 'driver=%s\n' "$(readlink "$dev/driver")"
	else
		echo 'driver=unbound'
	fi
	if [ -r "$dev/of_node/compatible" ]; then
		printf 'compatible='
		tr '\000' ',' < "$dev/of_node/compatible"
		printf '\n'
	fi
done

section platform
find /sys/bus/platform/devices -maxdepth 1 -mindepth 1 -printf '%f\n' 2>/dev/null |
	grep -Ei 'hdmi|mhl|sii|edid' | sort || true

section device_nodes
find /dev -maxdepth 1 -type c -printf '%M %u %g %s %p\n' 2>/dev/null |
	grep -Ei 'hdmi|mhl|edid' || true

section interrupts
grep -Ei 'sii|hdmi|mhl|edid' /proc/interrupts 2>/dev/null || true

section dmesg
dmesg 2>/dev/null | grep -Ei 'sii9022|hdmi|mhl|edid' | tail -n 80 || true
