#!/bin/sh
# SPDX-License-Identifier: MIT
# T4: the console moves to the native path. Load with no firmware framebuffer kept,
# blank and unblank three times, let a DRM master take the panel and give it back,
# then unload and reload. Stops at the first failure and leaves things in place.
# usage: display-t4.sh MODULE_DIR KMS_FRAME
set -u
dir=$1
tool=$2

state() { echo "== $1 $(cut -d' ' -f1 /proc/uptime) CG0 $(devmem 0x14000100 32) CG1 $(devmem 0x14000110 32) PLL_CON0 $(devmem 0x10215050 32) tainted $(cat /proc/sys/kernel/tainted)"; }
say() { echo "$1" > /dev/tty0; echo "console: $1"; }
fail() { echo "FAILED: $1"; state failed; dmesg | tail -40; exit "$2"; }
lo() {
	f=$dir/$1.ko
	if grep -q "^$(echo "$1" | tr - _) " /proc/modules; then
		echo "already loaded: $1"
		return 0
	fi
	shift
	echo "insmod $f $*"
	insmod "$f" "$@" || fail "insmod $f" 5
}
load() {
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
	lo drm_client_lib
	lo mediatek-drm
}
fbinfo() {
	cat /proc/fb
	cat /sys/class/graphics/fb0/name /sys/class/graphics/fb0/virtual_size 2>&1
	grep -H . /sys/class/vtconsole/*/name /sys/class/vtconsole/*/bind 2>/dev/null
}

uname -r
cat /proc/sys/kernel/random/boot_id
state before
fbinfo
say "display-t4 A: on simplefb, about to load"
sleep 3
load
sleep 3
state loaded
fbinfo
ls /dev/dri || fail "no DRM device" 6
say "display-t4 B: this line is on the native path"
sleep 20

for i in 1 2 3; do
	echo 4 > /sys/class/graphics/fb0/blank || fail "blank" 8
	state "blanked $i"
	sleep 5
	echo 0 > /sys/class/graphics/fb0/blank || fail "unblank" 8
	state "unblanked $i"
	say "display-t4 C$i: back after blank $i"
	sleep 5
done
dmesg | grep -E 'power mode read|sleep failed|\[drm' | tail -12

"$tool" 10
rc=$?
echo "kms-frame rc=$rc"
[ "$rc" = 0 ] || fail "kms-frame" 9
sleep 1
state 'after kms-frame'
say "display-t4 D: console back after the bars"
sleep 8

rmmod mediatek-drm || fail "rmmod mediatek-drm" 7
state unloaded
fbinfo
sleep 5
load
sleep 3
state reloaded
fbinfo
say "display-t4 E: console back after reload"
sleep 5
dmesg | grep -i -E 'timed out|underflow|nobody cared|WARNING|Unable|\*ERROR\*|sleep failed' | tail -20
echo "tainted $(cat /proc/sys/kernel/tainted)"
echo "finished rc=0"
