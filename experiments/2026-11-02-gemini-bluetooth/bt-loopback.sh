#!/bin/sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# The voice path's own loopback during one eSCO link: the driver copies the coded
# microphone packets straight to the headset. No coder, no capture file. Run after
# bt-test.sh load and pair, with CONSYS up: usage NAME='headset' sh bt-loopback.sh.
D=/run/bt-t1
R=/run/bt-root
in_root() { chroot $R /usr/bin/env PATH=/usr/bin:/bin:/usr/sbin:/sbin "$@"; }
rd() { busybox devmem "$1" 32; }
irqs() { awk '/BTCVSD/ { n = 0; for (i = 2; i <= NF && $i ~ /^[0-9]+$/; i++) n += $i; print n }' /proc/interrupts; }
regs() { echo "$1 r=$(rd 0x18000fd0) w=$(rd 0x18000fd4) ctl=$(rd 0x18000fd8) irqs=$(irqs)"; }
regs before
insmod $D/snd-soc-btcvsd.ko; echo "insmod driver=$?"
insmod $D/mt6797-btcvsd.ko; echo "insmod card=$?"
sleep 1
grep -i btcvsd /proc/asound/cards || { echo "no card"; exit 1; }
card=$(sed -n 's/^ *\([0-9][0-9]*\) \[.*mt6797-btcvsd.*/\1/p' /proc/asound/cards | head -1)
regs loaded
NAME="$NAME" sh $D/bt-test.sh sco 30 > $D/private/loopback-sco.txt 2>&1 &
sco=$!
sleep 5
regs link
in_root amixer -q -c "$card" cset 'name=BTCVSD Loopback Switch' on; echo "loopback on=$?"
i=0
while [ $i -lt 20 ]; do
	sleep 1
	regs "loop-$i"
	i=$((i + 1))
done
wait $sco
grep -E 'aplay=|arecord=' $D/private/loopback-sco.txt
sleep 1
regs ended
in_root amixer -q -c "$card" cset 'name=BTCVSD Loopback Switch' off; echo "loopback off=$?"
regs off
rmmod mt6797_btcvsd; echo "rmmod card=$?"
rmmod snd_soc_btcvsd; echo "rmmod driver=$?"
regs unloaded
