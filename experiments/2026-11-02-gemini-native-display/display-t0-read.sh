#!/bin/sh
# SPDX-License-Identifier: MIT
# T0: read-only snapshot of the display state the loader left, on the station.
# Reads registers with busybox devmem and writes nothing. It reads a block only
# if the MM domain is on and that block's MMSYS gate is open, because a read of
# a gated block can hang the bus.
set -u

rd() { devmem "$1" 32; }
dump() { # name base first last
	a=$(($3))
	while [ "$a" -le $(($4)) ]; do
		printf '%s+0x%03x %s\n' "$1" "$a" "$(rd $(($2 + a)))"
		a=$((a + 4))
	done
}

echo "boot_id $(cat /proc/sys/kernel/random/boot_id)"
uname -r
sta=$(rd 0x10006180)
sta2=$(rd 0x10006184)
echo "spm PWR_STATUS $sta PWR_STATUS_2ND $sta2"
# DIS is status bit 3 in the vendor and mainline MT6797 domain data.
if [ $((sta & 8)) -eq 0 ] || [ $((sta2 & 8)) -eq 0 ]; then
	echo "STOP: MM domain reads off"
	exit 3
fi
echo "topckgen CLK_CFG_0 $(rd 0x10000040)"

mm=0x14000000
cg0=$(rd $((mm + 0x100)))
cg1=$(rd $((mm + 0x110)))
echo "mmsys CG0 $cg0 CG1 $cg1"
if [ "$cg0" = 0x00000000 ] && [ "$cg1" = 0x00000000 ]; then
	# Two all-zero gate words is also what a rejected read returns. Tell them
	# apart with a register the capture shows nonzero before going further.
	rst=$(rd $((mm + 0x140)))
	echo "mmsys SW0_RST_B $rst"
	if [ "$rst" = 0x00000000 ]; then
		echo "STOP: reads return zero, possibly rejected by DEVAPC"
		exit 4
	fi
fi

dump mmsys $mm 0x000 0x0a4
dump mmsys $mm 0x100 0x154
dump mmsys $mm 0x880 0x8ac

block() { # name base gatebit first last [first last]
	n=$1 b=$2 g=$3
	shift 3
	if [ $((cg0 >> g & 1)) -ne 0 ]; then
		echo "$n gated, not read"
		return
	fi
	while [ "$#" -ge 2 ]; do
		dump "$n" "$b" "$1" "$2"
		shift 2
	done
}
block smi_common 0x14022000 0 0x000 0x0fc 0x100 0x2fc
block larb0 0x14020000 1 0x000 0x0fc 0x380 0x3fc 0xf00 0xffc
block larb5 0x14021000 2 0x000 0x0fc 0x380 0x3fc 0xf00 0xffc
block ovl0 0x1400b000 15 0x000 0x0d0 0x1d4 0x2a4 0xf40 0xf40
block ovl0_2l 0x1400d000 17 0x000 0x0d0 0x1d4 0x2a4 0xf40 0xf40
block ovl1_2l 0x1400e000 18 0x000 0x0d0 0x1d4 0x2a4 0xf40 0xf40
block rdma0 0x1400f000 19 0x000 0x0b4 0xf00 0xf00
block color0 0x14013000 23 0x400 0x424 0xc00 0xc58
block ccorr 0x14014000 24 0x000 0x034
block aal 0x14015000 25 0x000 0x034
block gamma 0x14016000 26 0x000 0x034
block od 0x14017000 27 0x000 0x034 0x500 0x510
block dither 0x14018000 28 0x000 0x034 0x100 0x170
block ufoe 0x14019000 29 0x000 0x000 0x020 0x020 0x050 0x054 0x100 0x104

# The mutex has no gate of its own; it sits under the MM root simplefb holds.
dump mutex 0x1401f000 0x000 0x034

# DSI0: the engine gate is CG1 bit 0, the interface gate CG1 bit 1.
if [ $((cg1 & 3)) -eq 0 ]; then
	dump dsi0 0x1401c000 0x000 0x19c
	dump dsi0 0x1401c000 0x200 0x20c
else
	echo "dsi0 gated, not read"
fi

# MIPI TX is outside MMSYS; the retained vendor dump reads this same window.
dump mipitx 0x10215000 0x000 0x090

# Pads: mode, direction, output and input for DISP_PWM, DSI_TE, LCM_RST and the
# two bias enables.
g=0x10005000
for p in 60 178 179 180 251; do
	m=$(rd $((g + 0x300 + 0x10 * (p / 8))))
	d=$(rd $((g + 0x000 + 0x10 * (p / 32))))
	o=$(rd $((g + 0x100 + 0x10 * (p / 32))))
	i=$(rd $((g + 0x200 + 0x10 * (p / 32))))
	echo "gpio$p mode $(((m >> (4 * (p % 8))) & 15)) dir $(((d >> (p % 32)) & 1)) out $(((o >> (p % 32)) & 1)) in $(((i >> (p % 32)) & 1))"
done

grep -E 'CmaTotal|CmaFree' /proc/meminfo
dmesg | grep -i -E 'simple-framebuffer|simplefb|cma:|fb0' | head -20
ls /sys/class/backlight/ 2>/dev/null
grep -H . /sys/class/backlight/*/brightness 2>/dev/null
grep -E ' (fb|drm)$' /proc/devices
ls /dev/fb* /dev/dri 2>/dev/null
cat /sys/class/graphics/fb0/virtual_size /sys/class/graphics/fb0/stride 2>/dev/null
grep -E 'mmsys|ovl|rdma|dsi|mutex' /proc/interrupts
