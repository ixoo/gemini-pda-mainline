#!/bin/sh
# SPDX-License-Identifier: MIT
# Read-only: print the MT6351 audio, clock and ACCDET registers through the
# built-in PMIC wrapper's regmap, so it works with the audio modules removed.
# One line per register; each read touches only that register.
# Usage: pmic-audio-read.sh >FILE
set -u
R=/sys/kernel/debug/regmap/1000d000.pwrap/registers
grep -q ' /sys/kernel/debug ' /proc/mounts || mount -t debugfs none /sys/kernel/debug
if [ ! -r "$R" ]; then
	echo "no $R; present:" >&2
	ls /sys/kernel/debug/regmap >&2
	exit 1
fi
# A line is "rrrr: vvvv\n", 11 bytes, and register R is line R/2.
line() { dd if="$R" bs=11 skip=$(($1 / 2)) count=1 2>/dev/null; }
case $(line $((0x023a))) in
023a:*) ;;
*) echo "unexpected line format; nothing else read" >&2; exit 1 ;;
esac
range() {
	a=$(($1))
	while [ "$a" -le $(($2)) ]; do
		line "$a"
		a=$((a + 2))
	done
}
echo "uptime $(cut -d' ' -f1 /proc/uptime)"
range 0x023a 0x024c # clock power-down
range 0x029a 0x029a # CLKSQ
range 0x0800 0x080a # ZCD and HP gain
range 0x0a00 0x0a02 # VA18
range 0x0a16 0x0a18 # VUSB33
range 0x0cf2 0x0d1e # analog decoder and encoder
range 0x0f46 0x0f64 # ACCDET
range 0x2000 0x209e # audio digital
