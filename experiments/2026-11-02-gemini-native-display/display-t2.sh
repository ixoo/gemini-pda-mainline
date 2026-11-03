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
	echo "== $1 $(cut -d' ' -f1 /proc/uptime)"
	cat /proc/sys/kernel/tainted
	dump mmsys 0x14000000 0x034 0x0a4
	dump mmsys 0x14000000 0x100 0x110
	dump mmsys 0x14000000 0x150 0x150
	dump mutex 0x1401f000 0x000 0x034
	dump mipitx 0x10215000 0x000 0x068
	# Read a block only behind its open gate: the output may be off by now.
	cg0=$(devmem 0x14000100 32)
	cg1=$(devmem 0x14000110 32)
	[ $((cg1 & 3)) -eq 0 ] && dump dsi0 0x1401c000 0x000 0x068
	[ $((cg1 & 3)) -eq 0 ] && dump dsi0 0x1401c000 0x104 0x130
	[ $((cg1 & 3)) -eq 0 ] && dump dsi0 0x1401c000 0x160 0x19c
	[ $((cg0 >> 15 & 1)) -eq 0 ] && dump ovl0 0x1400b000 0x000 0x050
	[ $((cg0 >> 15 & 1)) -eq 0 ] && dump ovl0 0x1400b000 0xf40 0xf40
	[ $((cg0 >> 17 & 1)) -eq 0 ] && dump ovl0_2l 0x1400d000 0x000 0x030
	[ $((cg0 >> 18 & 1)) -eq 0 ] && dump ovl1_2l 0x1400e000 0x000 0x030
	[ $((cg0 >> 19 & 1)) -eq 0 ] && dump rdma0 0x1400f000 0x000 0x040
	[ $((cg0 >> 19 & 1)) -eq 0 ] && dump rdma0 0x1400f000 0x0f0 0x100
	return 0
}
lo() {
	f=$dir/$1.ko
	if grep -q "^$(echo "$1" | tr - _) " /proc/modules; then
		echo "already loaded: $1"
		return 0
	fi
	shift
	echo "insmod $f $*"
	insmod "$f" "$@" || { echo "FAILED insmod $f"; dmesg | tail -40; exit 5; }
}

uname -r
cat /proc/sys/kernel/random/boot_id
state before
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
kill -0 "$pid" 2>/dev/null && echo "tool still running" || echo "tool already exited"
state running
grep -E 'ovl|rdma|dsi' /proc/interrupts
wait "$pid"
rc=$?
echo "kms-frame rc=$rc"
state after
grep -E 'ovl|rdma|dsi' /proc/interrupts
dmesg | grep -i -E 'mediatek-drm|mipi|dsi|panel|\[drm|flip|timed out|underflow|nobody cared|WARNING|Unable' | tail -40
echo "finished rc=$rc"
exit $rc
