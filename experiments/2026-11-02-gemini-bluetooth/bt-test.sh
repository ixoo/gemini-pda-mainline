#!/bin/sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# Bluetooth device test. Usage: NAME='headset name' sh bt-test.sh STEP
# Steps: load, pair, play, soak SECONDS, sco SECONDS, unload. Files in /run/bt-t1/.
# BT_HFP=1 at load adds rfcomm.ko and the Hands-Free gateway, for sco.
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
	[ -z "${BT_HFP:-}" ] || { insmod $D/rfcomm.ko; echo "insmod rfcomm=$?"; }
	# shellcheck disable=SC2086 # BT_PARAMS may hold several words, or none.
	insmod $D/btmt6797.ko ${BT_PARAMS:-}; echo "insmod btmt6797=$?"
	sleep 4
	sh $D/bt-start.sh $D/bt-root.tar.gz
	cp $D/tone.wav $D/voice.wav $D/music.wav $R/tmp/ 2>/dev/null
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
ab)
	# One 30 s clip per codec named in $2, numbered, with the rate of each. Order is the
	# caller's to choose and keep from the listener: the printed lines don't name codecs.
	pcm=$(in_root bluealsa-cli list-pcms | grep 'a2dpsrc/sink' | head -1)
	n=0
	for c in $2; do
		n=$((n + 1))
		in_root bluealsa-cli codec "$pcm" "$c" >> $P/ab.log 2>&1; echo "clip $n switch=$?"
		sleep 2
		in_root bluealsa-cli codec "$pcm" | grep -i selected | sed "s/^/clip $n /" >> $P/ab.log
		before=$(in_root hciconfig hci0 | sed -n 's/.*TX bytes:\([0-9]*\).*/\1/p')
		s=$(date +%s)
		timeout 45 chroot $R /usr/bin/env PATH=/usr/bin:/bin aplay -q -D "bluealsa:DEV=$(addr),PROFILE=a2dp" /tmp/music.wav; a=$?
		e=$(date +%s)
		after=$(in_root hciconfig hci0 | sed -n 's/.*TX bytes:\([0-9]*\).*/\1/p')
		echo "clip $n aplay=$a seconds=$((e - s)) kbps=$(( (after - before) * 8 / (e - s) / 1000 ))"
		sleep 3
	done
	;;
stream)
	# $2 seconds of music from one aplay, fed in a loop, so nothing restarts. With a codec
	# in $3, it switches to that before any audio.
	pcm=$(in_root bluealsa-cli list-pcms | grep 'a2dpsrc/sink' | head -1)
	[ -z "${3:-}" ] || { in_root bluealsa-cli codec "$pcm" "$3" >> $P/ab.log 2>&1; echo "switch=$?"; sleep 2; }
	in_root bluealsa-cli codec "$pcm" | grep -i selected
	before=$(in_root hciconfig hci0 | sed -n 's/.*TX bytes:\([0-9]*\).*/\1/p')
	# With BT_RF_LOG, power, signal and link quality once a second. It stops with the stream.
	rf=
	if [ -n "${BT_RF_LOG:-}" ]; then
		dev=$(addr)
		in_root hcitool tpl -t 1 "$dev" > $P/rf.log 2>&1
		while :; do
			echo "$(date +%T) $(in_root hcitool tpl "$dev") $(in_root hcitool rssi "$dev") $(in_root hcitool lq "$dev")"
			sleep 1
		done >> $P/rf.log 2>&1 &
		rf=$!
	fi
	s=$(date +%s); echo "stream starts $(date +%T)"
	i=0
	# BT_APLAY_ARGS holds several words.
	# shellcheck disable=SC2086
	while [ $i -lt $(($2 / 30)) ]; do
		tail -c +45 $R/tmp/music.wav
		i=$((i + 1))
	done | timeout $(($2 + 30)) chroot $R /usr/bin/env PATH=/usr/bin:/bin aplay -q ${BT_APLAY_ARGS:-} -D "bluealsa:DEV=$(addr),PROFILE=a2dp" -t raw -f cd -
	a=$?
	e=$(date +%s)
	[ -z "$rf" ] || { kill "$rf"; wait "$rf" 2>/dev/null; }
	after=$(in_root hciconfig hci0 | sed -n 's/.*TX bytes:\([0-9]*\).*/\1/p')
	echo "stream ends $(date +%T) aplay=$a seconds=$((e - s)) kbps=$(( (after - before) * 8 / (e - s) / 1000 ))"
	;;
soak)
	# Plays for $2 seconds at most, counting bytes; stops on the first failure.
	end=$(( $(date +%s) + $2 ))
	while [ "$(date +%s)" -lt "$end" ]; do
		timeout 45 chroot $R /usr/bin/env PATH=/usr/bin:/bin aplay -q -D "bluealsa:DEV=$(addr),PROFILE=a2dp" /tmp/tone.wav || { echo "aplay failed"; break; }
		stats
	done
	;;
sco)
	# One voice connection: the tone out, the microphone in, for at most $2 s. The
	# capture may hold speech, so it stays private and is deleted once measured.
	stats
	timeout $(($2 + 15)) chroot $R /usr/bin/env PATH=/usr/bin:/bin arecord -q -D "bluealsa:DEV=$(addr),PROFILE=sco" -f S16_LE -r "${BT_SCO_RATE:-8000}" -c 1 -d "$2" /tmp/mic.wav &
	mic=$!
	if [ -n "${SCO_NO_PLAY:-}" ]; then
		sleep "$2"
	else
		timeout $(($2 + 15)) chroot $R /usr/bin/env PATH=/usr/bin:/bin aplay -q -D "bluealsa:DEV=$(addr),PROFILE=sco" -d "$2" /tmp/voice.wav; echo "aplay=$?"
	fi
	wait $mic; echo "arecord=$?"
	stats
	cp $R/tmp/mic.wav $P/ 2>/dev/null
	echo "mic bytes: $(wc -c < $P/mic.wav 2>/dev/null)"
	;;
unload)
	in_root bluetoothctl --timeout 5 disconnect "$(addr)" >> $P/bluetoothctl.log 2>&1
	ctl power off
	killall bluealsa bluetoothd btmon dbus-daemon 2>/dev/null
	sleep 1
	cp $R/run/*.log $R/run/t2.btsnoop $P/ 2>/dev/null
	rmmod rfcomm 2>/dev/null
	rmmod btmt6797; echo "rmmod btmt6797=$?"
	rmmod bluetooth; echo "rmmod bluetooth=$?"
	umount $R/proc $R/sys $R/dev
	;;
esac
dmesg | grep -E 'WMT BT function|STP link|mt6797-consys: (firmware|STP)|hci0|Call trace|Oops|WARNING|nobody cared' \
	| grep -vE '([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}' | tail -8
