#!/bin/sh
# SPDX-License-Identifier: MIT
# T1: load the display modules and bind, with no modeset, then unload. The
# console must keep running throughout. Stops at the first failed load, or if no
# DRM device appears, and leaves what loaded in place for inspection. Exits
# non-zero on any failure, including a failed unload.
# usage: display-t1.sh MODULE_DIR
set -u
dir=$1

state() {
	echo "== $1"
	for r in 0x14000100 0x14000110 0x1400b000 0x1400bf40 0x1401c000 0x1401c014 0x1401c00c 0x10215050 0x10215058 0x1401f02c; do
		echo "$r $(devmem $r 32)"
	done
	echo "tainted $(cat /proc/sys/kernel/tainted)"
}
say() { echo "$1" > /dev/tty0; echo "console: $1"; }
lo() {
	f=$dir/$1.ko
	shift
	echo "insmod $f $*"
	insmod "$f" "$@" || { echo "FAILED insmod $f"; state failed; dmesg | tail -40; exit 5; }
}

uname -r
cat /proc/sys/kernel/random/boot_id
state before
say "display-t1 A: before load"
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
sleep 5
state bound
ls /sys/class/drm /dev/dri 2>&1
if ! ls /dev/dri/card* >/dev/null 2>&1; then
	echo "NOT BOUND: no DRM device, leaving the modules loaded"
	dmesg | tail -40
	exit 6
fi
grep -E 'ovl|rdma|dsi' /proc/interrupts
dmesg | grep -i -E 'mediatek-drm|mtk-|mipi|dsi|panel|nobody cared|drm' | tail -40
say "display-t1 B: bound, no modeset"
sleep 20
grep -E 'ovl|rdma|dsi' /proc/interrupts
state 'bound +25 s'
rc=0
for m in mediatek-drm drm_display_helper cec drm_dma_helper drm_kms_helper \
	panel-novatek-nt36672e drm drm_panel_orientation_quirks mtk-mutex mtk-mmsys \
	clk-mt6797-mm phy-mtk-mipi-dsi-drv; do
	echo "rmmod $m"
	rmmod "$m" || { echo "FAILED rmmod $m"; rc=7; break; }
done
state unloaded
say "display-t1 C: unloaded"
grep -c . /proc/modules
dmesg | tail -15
echo "finished rc=$rc"
exit $rc
