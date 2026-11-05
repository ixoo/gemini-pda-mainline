#!/bin/sh
# SPDX-License-Identifier: MIT
# Read-only: print the microSD host's state on the station. MMC host and
# block names, the card-detect GPIO, the MSDC1 pad registers, the VMCH and
# VMC regulators and their MT6351 registers. No CID, CSD or serial number.
# Usage: sd-state.sh LABEL >FILE
set -u
label=${1:-state}
grep -q ' /sys/kernel/debug ' /proc/mounts || mount -t debugfs none /sys/kernel/debug
echo "== $label uptime $(cut -d' ' -f1 /proc/uptime)"

echo "-- hosts"
for h in /sys/class/mmc_host/mmc*; do
	[ -e "$h" ] || continue
	echo "$(basename "$h") $(basename "$(readlink -f "$h/device")")"
	for c in "$h"/mmc*:*; do
		[ -e "$c/type" ] && echo "  card $(basename "$c") type=$(cat "$c/type")"
	done
done
echo "-- block"
grep -E 'mmcblk' /proc/partitions | awk '{print $4, $3}'

echo "-- mmc1 ios"
cat /sys/kernel/debug/mmc1/ios 2>/dev/null || echo "no mmc1 ios"

echo "-- gpio 67"
grep -i -E 'gpio-67 |cd' /sys/kernel/debug/gpio 2>/dev/null | head -4
for p in /sys/kernel/debug/pinctrl/*/pins; do
	grep -E '^pin (67|129|130|131|132|133|134) ' "$p" 2>/dev/null
done

echo "-- interrupts"
grep -i -E 'mmc|msdc|cd' /proc/interrupts

echo "-- regulators"
for r in /sys/class/regulator/regulator.*; do
	n=$(cat "$r/name" 2>/dev/null)
	case $n in
	vmch|vmc)
		echo "$n state=$(cat "$r/state" 2>/dev/null) uV=$(cat "$r/microvolts" 2>/dev/null) users=$(cat "$r/num_users" 2>/dev/null)"
		;;
	esac
done

echo "-- pmic"
R=/sys/kernel/debug/regmap/1000d000.pwrap/registers
# A line is "rrrr: vvvv\n", 11 bytes, and register R is line R/2.
line() { dd if="$R" bs=11 skip=$(($1 / 2)) count=1 2>/dev/null; }
if [ -r "$R" ] && line 0x0a2e | grep -q '^0a2e:'; then
	for a in 0x0a2e 0x0aaa 0x0ace 0x0ae2; do line "$a"; done
else
	echo "no pmic regmap or unexpected format; not read"
fi

echo "-- pads"
if command -v devmem >/dev/null 2>&1; then
	# IOCFG_B IES, RDSEL, TDSEL, PUPD, R0, R1, drive and bias; IOCFG_R SMT.
	for a in 0x10002420 0x100024a0 0x100024c0 0x10002500 0x10002510 \
		0x10002520 0x100025b0 0x10002830; do
		echo "$a $(devmem "$a" 32)"
	done
else
	echo "no devmem; pads not read"
fi
