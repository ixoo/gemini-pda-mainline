#!/bin/sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# Bluetooth device test. Usage: NAME='headset name' sh bt-test.sh STEP
# Steps: load, pair, play, soak SECONDS, unload. Files in /run/bt-t1/.
# BT_PARAMS=gemian_radio=1 at load only if the owner allows it.
# Names and addresses stay in /run/bt-t1/private; printed lines hold neither.
D=/run/bt-t1
P=$D/private
R=/run/bt-root
in_root() { chroot $R /usr/bin/env PATH=/usr/bin:/bin:/usr/sbin:/sbin "$@"; }
ctl() { in_root bluetoothctl "$@" 2>&1 | tee -a $P/bluetoothctl.log | grep -vE '([0-9A-Fa-f]{2}:){5}' | grep -vF "${NAME:-@@}" | tail -3; }
addr() { cat $P/addr; }
stats() { echo "$(date +%T) hci0 $(in_root hciconfig hci0 | grep -E 'RX bytes|TX bytes' | tr -s ' \t' ' ' | tr '\n' ' ')"; }
case "$1" in
load)
	mkdir -p $P
	insmod $D/bluetooth.ko; echo "insmod bluetooth=$?"
	insmod $D/btmt6797.ko ${BT_PARAMS:-}; echo "insmod btmt6797=$?"
	sleep 4
	sh $D/bt-start.sh $D/bt-root.tar.gz
	cp $D/tone.wav $R/tmp/tone.wav
	in_root btmon -w /run/t2.btsnoop > /dev/null 2>&1 < /dev/null &
	;;
pair)
	# One inquiry session of at most 30 s, stopped by the same client that started
	# it: another client's scan off does not stop it. Its agent stays for pairing.
	ctl power on
	rm -f $P/scan-stop
	( echo 'agent NoInputNoOutput'; echo default-agent; echo 'scan bredr'
	  i=0; while [ $i -lt 30 ] && [ ! -e $P/scan-stop ]; do sleep 1; i=$((i + 1)); done
	  echo 'scan off'; sleep 60; echo quit ) \
		| in_root bluetoothctl > $P/scan.log 2>&1 &
	i=0; a=
	while [ $i -lt 30 ] && [ -z "$a" ]; do
		sleep 1; i=$((i + 1))
		a=$(in_root bluetoothctl devices | grep -F "$NAME" | head -1 | cut -d' ' -f2)
	done
	touch $P/scan-stop
	echo "devices seen: $(in_root bluetoothctl devices | wc -l); target after ${i}s: $([ -n "$a" ] && echo found || echo absent)"
	[ -n "$a" ] || exit 1
	echo "$a" > $P/addr
	in_root bluetoothctl --timeout 25 pair "$a" >> $P/bluetoothctl.log 2>&1; echo "pair=$?"
	in_root bluetoothctl --timeout 5 trust "$a" >> $P/bluetoothctl.log 2>&1; echo "trust=$?"
	in_root bluetoothctl --timeout 15 connect "$a" >> $P/bluetoothctl.log 2>&1; echo "connect=$?"
	sleep 2
	in_root bluealsa-cli list-pcms | sed -E 's/dev_[0-9A-F_]+/dev_X/'
	;;
play)
	stats
	timeout 45 chroot $R /usr/bin/env PATH=/usr/bin:/bin aplay -q -D "bluealsa:DEV=$(addr),PROFILE=a2dp" /tmp/tone.wav; echo "aplay=$?"
	stats
	;;
soak)
	# Plays for $2 seconds at most, counting bytes; stops on the first failure.
	end=$(( $(date +%s) + $2 ))
	while [ "$(date +%s)" -lt "$end" ]; do
		timeout 45 chroot $R /usr/bin/env PATH=/usr/bin:/bin aplay -q -D "bluealsa:DEV=$(addr),PROFILE=a2dp" /tmp/tone.wav || { echo "aplay failed"; break; }
		stats
	done
	;;
unload)
	in_root bluetoothctl --timeout 5 disconnect "$(addr)" >> $P/bluetoothctl.log 2>&1
	ctl power off
	killall bluealsa bluetoothd btmon dbus-daemon 2>/dev/null
	sleep 1
	cp $R/run/*.log $R/run/t2.btsnoop $P/ 2>/dev/null
	rmmod btmt6797; echo "rmmod btmt6797=$?"
	rmmod bluetooth; echo "rmmod bluetooth=$?"
	umount $R/proc $R/sys $R/dev
	;;
esac
dmesg | grep -E 'WMT BT function|STP link|mt6797-consys: (firmware|STP)|hci0|Call trace|Oops|WARNING|nobody cared' \
	| grep -vE '([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}' | tail -8
