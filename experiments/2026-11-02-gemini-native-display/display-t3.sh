#!/bin/sh
# SPDX-License-Identifier: MIT
# T3: tear the running output down by unloading, then bring it up again with
# read-only DCS identity reads, and hold a test frame. Run with the modules T2 left
# loaded. Leaves the modules loaded.
# usage: display-t3.sh MODULE_DIR KMS_FRAME SECONDS
set -u
dir=$1
tool=$2
secs=$3

cg() { echo "== $1 $(cut -d' ' -f1 /proc/uptime) CG0 $(devmem 0x14000100 32) CG1 $(devmem 0x14000110 32) PLL_CON0 $(devmem 0x10215050 32) tainted $(cat /proc/sys/kernel/tainted)"; }

uname -r
cat /proc/sys/kernel/random/boot_id
cg before
rmmod mediatek-drm || { echo "FAILED rmmod mediatek-drm"; dmesg | tail -40; exit 7; }
rmmod panel-novatek-nt36672e || { echo "FAILED rmmod panel"; dmesg | tail -40; exit 7; }
cg unloaded
sleep 5
insmod "$dir/panel-novatek-nt36672e.ko" read_identity=1 || { echo "FAILED insmod panel"; exit 5; }
insmod "$dir/mediatek-drm.ko" keep_firmware_fb=1 || { echo "FAILED insmod mediatek-drm"; exit 5; }
sleep 2
ls /dev/dri || { echo "NOT BOUND"; dmesg | tail -40; exit 6; }
cg bound
"$tool" "$secs"
rc=$?
echo "kms-frame rc=$rc"
cg after
grep -E 'ovl|rdma|dsi' /proc/interrupts
dmesg | grep -E 'DCS read|dsi get' | tail -30
dmesg | grep -i -E 'timed out|underflow|nobody cared|WARNING|Unable|\*ERROR\*|failed' | tail -20
echo "finished rc=$rc"
exit $rc
