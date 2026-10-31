#!/bin/busybox sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# Wi-Fi module cycles on the running station, fed over SSH:
#   ssh root@station 'CYCLES=3 /bin/busybox sh -s' < wifi-cycles.sh
# Starts the firmware once per boot if needed (region19_prepare, then
# wmt_negotiate), then CYCLES times: insmod mac, add wlan0, bring it up,
# one passive scan of the pinned 5200 MHz channel, rmmod. Prints one line
# per step and keeps each cycle's kernel log in /run/station/. The kernel
# log is never cleared: the firmware-ready line marks a started firmware.
# With STOP=1 (0341), the firmware is then stopped through wlan_stop and a
# further insmod must be refused.
export PATH=/bin LD_LIBRARY_PATH=/lib
CYCLES=${CYCLES:-3}
C=/sys/bus/platform/devices/10001340.consys
since() { dmesg | tail -n +$((mark + 1)); }
phys() { for p in /sys/class/ieee80211/*; do [ -e "$p" ] && printf '%s ' "${p##*/}"; done; }
M=/lib/modules/$(uname -r)/mac.ko

if ! dmesg | grep -q "mac module attaches on load"; then
	for step in region19_prepare wmt_negotiate; do
		if echo 1 > $C/$step; then echo "firmware $step=0"; else echo "firmware $step=failed"; fi
	done
	i=0
	while [ $i -lt 90 ] && ! dmesg | grep -q "mac module attaches on load\|firmware stopped"; do
		sleep 1
		i=$((i + 1))
	done
	dmesg | grep -q "mac module attaches on load" || { echo "firmware not ready"; exit 1; }
fi
echo "firmware ready"

c=1
while [ $c -le "$CYCLES" ]; do
	mark=$(dmesg | wc -l)
	insmod "$M"; echo "cycle $c insmod=$?"
	sleep 1
	since | grep -E "record prepare|regulatory configuration" | sed "s/^/cycle $c /" | cut -c1-160
	phy=$(phys)
	phy=${phy%% *}
	echo "cycle $c phy=$phy"
	iw phy "$phy" interface add wlan0 type managed; echo "cycle $c add=$?"
	ip link set wlan0 up; echo "cycle $c up=$?"
	iw dev wlan0 scan freq 5200 passive > /run/station/scan-$c.txt 2>&1
	echo "cycle $c scan=$? bss=$(grep -c '^BSS ' /run/station/scan-$c.txt)"
	timeout 30 rmmod mac; echo "cycle $c rmmod=$?"
	sleep 1
	echo "cycle $c lsmod=$(lsmod | grep -c '^mac ') phy_after=$(phys)"
	since | grep -E "detached|Oops|BUG|WARNING|stopped|refused|Call trace|scan:" | sed "s/^/cycle $c /" | cut -c1-160
	since > /run/station/wifi-cycle-$c.txt
	c=$((c + 1))
done

if [ "${STOP:-0}" = 1 ]; then
	mark=$(dmesg | wc -l)
	if echo 1 > $C/wlan_stop; then echo "stop=0"; else echo "stop=failed"; fi
	insmod "$M"; echo "after-stop insmod=$?"
	lsmod | grep -q '^mac ' && { timeout 30 rmmod mac; echo "after-stop rmmod=$?"; }
	since | grep -E "WLAN stop|Oops|BUG|WARNING|Call trace|attach|regulatory" | sed "s/^/stop /" | cut -c1-160
	since > /run/station/wifi-stop.txt
fi
