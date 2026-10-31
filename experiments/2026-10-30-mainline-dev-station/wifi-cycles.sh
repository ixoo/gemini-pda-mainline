#!/bin/busybox sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# Wi-Fi module cycles on the running station, fed over SSH:
#   ssh root@station 'CYCLES=3 RESTARTS=2 /bin/busybox sh -s' < wifi-cycles.sh
# Loads the core and CONSYS modules (0346-0348) and starts the firmware once
# if needed (region19_prepare, then wmt_negotiate), then CYCLES times: insmod
# mac, add wlan0, bring it up, one passive scan of the pinned 5200 MHz
# channel, rmmod. Then RESTARTS times: unload mac, CONSYS (which stops the
# firmware and powers CONN off) and the core, load them again, start the
# firmware (a second common init and calibration, R2) and run one cycle.
# Prints one line per step and keeps each step's kernel log in /run/station/.
# The kernel log is never cleared; each step reads only the lines after its
# own mark. With STOP=1 (0341), the firmware is then stopped through
# wlan_stop and a further insmod must be refused.
export PATH=/bin LD_LIBRARY_PATH=/lib
CYCLES=${CYCLES:-3}
RESTARTS=${RESTARTS:-0}
C=/sys/bus/platform/devices/10001340.consys
D=/lib/modules/$(uname -r)
M=$D/mac.ko
STARTED=/run/station/firmware-started
since() { dmesg | tail -n +$((mark + 1)); }
phys() { for p in /sys/class/ieee80211/*; do [ -e "$p" ] && printf '%s ' "${p##*/}"; done; }
mkdir -p /run/station

load_owner() {
	lsmod | grep -q '^mt6797_wlan_core ' || { insmod "$D/mt6797-wlan-core.ko"; echo "$1 load core=$?"; }
	lsmod | grep -q '^mt6797_consys ' || { insmod "$D/mt6797-consys.ko"; echo "$1 load consys=$?"; }
}

start_firmware() {
	mark=$(dmesg | wc -l)
	for step in region19_prepare wmt_negotiate; do
		if echo 1 > $C/$step; then echo "$1 firmware $step=0"; else echo "$1 firmware $step=failed"; fi
	done
	i=0
	while [ $i -lt 90 ] && ! since | grep -q "mac module attaches on load\|firmware stopped\|stopped ("; do
		sleep 1
		i=$((i + 1))
	done
	since > "/run/station/firmware-$1.txt"
	since | grep -E "kept from an earlier|common init: result|EMI final policy|stopped \(" | sed "s/^/$1 /" | cut -c1-160
	since | grep -q "mac module attaches on load" || { echo "$1 firmware not ready"; exit 1; }
	echo "$1 firmware ready after ${i}s"
	: > $STARTED
}

cycle() {
	mark=$(dmesg | wc -l)
	insmod "$M"; echo "cycle $1 insmod=$?"
	sleep 1
	since | grep -E "record prepare|regulatory configuration" | sed "s/^/cycle $1 /" | cut -c1-160
	phy=$(phys)
	phy=${phy%% *}
	echo "cycle $1 phy=$phy"
	iw phy "$phy" interface add wlan0 type managed; echo "cycle $1 add=$?"
	ip link set wlan0 up; echo "cycle $1 up=$?"
	iw dev wlan0 scan freq 5200 passive > "/run/station/scan-$1.txt" 2>&1
	echo "cycle $1 scan=$? bss=$(grep -c '^BSS ' "/run/station/scan-$1.txt")"
	timeout 30 rmmod mac; echo "cycle $1 rmmod=$?"
	sleep 1
	echo "cycle $1 lsmod=$(lsmod | grep -c '^mac ') phy_after=$(phys)"
	since | grep -E "detached|Oops|BUG|WARNING|stopped|refused|Call trace|scan:" | sed "s/^/cycle $1 /" | cut -c1-160
	since > "/run/station/wifi-cycle-$1.txt"
}

load_owner boot
[ -e $STARTED ] || start_firmware boot
echo "firmware ready"

c=1
while [ $c -le "$CYCLES" ]; do
	cycle $c
	c=$((c + 1))
done

r=1
while [ $r -le "$RESTARTS" ]; do
	mark=$(dmesg | wc -l)
	lsmod | grep -q '^mac ' && { timeout 30 rmmod mac; echo "restart $r rmmod mac=$?"; }
	timeout 30 rmmod mt6797-consys; echo "restart $r rmmod consys=$?"
	rmmod mt6797-wlan-core; echo "restart $r rmmod core=$?"
	rm -f $STARTED
	since | grep -E "WLAN stop|CONN power-off|CONSYS unloaded|Oops|BUG|WARNING|Call trace" | sed "s/^/restart $r /" | cut -c1-160
	since > "/run/station/unload-$r.txt"
	load_owner "restart $r"
	start_firmware "restart-$r"
	cycle "r$r"
	r=$((r + 1))
done

if [ "${STOP:-0}" = 1 ]; then
	mark=$(dmesg | wc -l)
	if echo 1 > $C/wlan_stop; then echo "stop=0"; else echo "stop=failed"; fi
	insmod "$M"; echo "after-stop insmod=$?"
	lsmod | grep -q '^mac ' && { timeout 30 rmmod mac; echo "after-stop rmmod=$?"; }
	since | grep -E "WLAN stop|Oops|BUG|WARNING|Call trace|attach|regulatory" | sed "s/^/stop /" | cut -c1-160
	since > /run/station/wifi-stop.txt
fi
