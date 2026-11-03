#!/bin/sh
# SPDX-License-Identifier: MIT
# T2: the first modeset. Load the display modules with the firmware framebuffer
# kept, put a test frame on the panel for SECONDS, read the pipeline while it runs,
# then let the tool exit, which disables the output. The modules stay loaded.
# usage: display-t2.sh MODULE_DIR KMS_FRAME SECONDS
set -u
dir=$1
tool=$2
secs=$3

dump() { # name base first last
	a=$(($3))
	while [ "$a" -le $(($4)) ]; do
		printf '%s+0x%03x %s\n' "$1" "$a" "$(devmem $(($2 + a)) 32)"
		a=$((a + 4))
	done
}
state() {
	echo "== $1"
	cat /proc/sys/kernel/tainted
	dump mmsys 0x14000000 0x034 0x0a4
	dump mmsys 0x14000000 0x100 0x110
	dump mmsys 0x14000000 0x150 0x150
	dump mutex 0x1401f000 0x000 0x034
	dump mipitx 0x10215000 0x000 0x068
	[ "$2" = gates-open ] || return 0
	dump dsi0 0x1401c000 0x000 0x068
	dump dsi0 0x1401c000 0x104 0x130
	dump dsi0 0x1401c000 0x160 0x19c
	dump ovl0 0x1400b000 0x000 0x050
	dump ovl0 0x1400b000 0xf40 0xf40
	dump ovl0_2l 0x1400d000 0x000 0x030
	dump ovl1_2l 0x1400e000 0x000 0x030
	dump rdma0 0x1400f000 0x000 0x040
	dump rdma0 0x1400f000 0x0f0 0x100
}
lo() {
	f=$dir/$1.ko
	shift
	echo "insmod $f $*"
	insmod "$f" "$@" || { echo "FAILED insmod $f"; dmesg | tail -40; exit 5; }
}

uname -r
cat /proc/sys/kernel/random/boot_id
state before gates-open
lo phy-mtk-mipi-dsi-drv
lo clk-mt6797-mm
lo mtk-mmsys
lo mtk-mutex
lo drm_panel_orientation_quirks
lo drm
lo panel-novatek-nt36672e
lo drm_kms_helper
lo drm_dma_helper
lo cec
lo drm_display_helper
lo mediatek-drm keep_firmware_fb=1
sleep 2
ls /dev/dri || { echo "NOT BOUND"; dmesg | tail -40; exit 6; }
dmesg | grep -i -E 'mediatek-drm|mipi|dsi|panel|\[drm' | tail -20
grep -E 'ovl|rdma|dsi' /proc/interrupts

"$tool" "$secs" &
pid=$!
sleep 10
state running gates-open
grep -E 'ovl|rdma|dsi' /proc/interrupts
wait "$pid"
rc=$?
echo "kms-frame rc=$rc"
# The output is off now, so the display gates may be closed: read MMSYS and PHY only.
state after gates-closed
grep -E 'ovl|rdma|dsi' /proc/interrupts
dmesg | grep -i -E 'mediatek-drm|mipi|dsi|panel|\[drm|flip|timed out|underflow|nobody cared|WARNING|Unable' | tail -40
echo "finished rc=$rc"
exit $rc
