#!/bin/sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# One direction of the voice path during one eSCO link. Run after bt-test.sh load and
# pair, with CONSYS up, and one mode per link:
#   NAME='headset' DIR=rx sh bt-voice-test.sh    the microphone to private/mic.cvsd
#   NAME='headset' DIR=tx sh bt-voice-test.sh    notes to the headset, 5 s in each bit order
#   NAME='headset' DIR=both sh bt-voice-test.sh  the microphone for 24 s, with 10 s of CVSD
#                                                idle pattern sent from 8 s in
# BT_CALL=1 with DIR=both tells the headset a call is active before the link opens, and
# ended 10 s into the capture. Indicators follow BlueALSA's list: 1 service, 2 call.
# Nothing plays over HCI to hold the link, in case the firmware acts on those packets.
# The capture holds speech: it is private. The rate tells ALSA 8 kHz, not the 64 kHz of the
# coded bits: at 64 kHz the core's interrupt check reads a normal interval as a lost buffer
# and stops capture at once. aplay starts on its first write, as the vendor's HAL does: the
# driver's ring is smaller than the buffer, so waiting for a full one never starts.
# A hang leaves nothing in RAM, so each step goes to the log and to /mnt/data with a sync.
D=/run/bt-t1
P=$D/private
R=/run/bt-root
L=/mnt/data/bt-voice-log.txt
step() { echo "$(date +%T) $1" | tee -a $L > /dev/kmsg; sync; }
status() {
	s=/proc/asound/card$card/pcm0$1/sub0/status
	[ -e "$s" ] && echo "$(date +%T) pcm0$1 $(grep -E 'state|hw_ptr' "$s" | tr -s ' ' | tr '\n' ' ')" >> $L
	sync
}
: > $L
step "start DIR=$DIR"
if [ "$DIR" = tx ]; then
	tail -c +45 $D/voice.wav | head -c 80000 > $P/notes.raw
	$D/bt-voice encode < $P/notes.raw > $P/notes-low.cvsd
	$D/bt-voice encode --msb < $P/notes.raw > $P/notes-high.cvsd
	cat $P/notes-low.cvsd $P/notes-high.cvsd > $R/tmp/tx.cvsd
	step "tx bytes $(wc -c < $R/tmp/tx.cvsd)"
elif [ "$DIR" = both ]; then
	# 0xaa is the pattern the driver itself writes for silence.
	head -c 80000 /dev/zero | tr '\000' '\252' > $R/tmp/tx.cvsd
fi
insmod $D/mtk-btcvsd.ko; echo "insmod driver=$?"
insmod $D/mt6797-btcvsd.ko; echo "insmod card=$?"
sleep 1
card=$(sed -n 's/^ *\([0-9][0-9]*\) \[.*mt6797-btcvsd.*/\1/p' /proc/asound/cards | head -1)
[ -n "$card" ] || { step "no card"; exit 1; }
if [ -n "${BT_CALL:-}" ]; then
	rm -f $R/tmp/at $R/tmp/in-call
	mkfifo $R/tmp/at
	exec 3<> $R/tmp/at
	: > $R/tmp/in-call
	# While this client is open, BlueALSA forwards what it can't answer, so +CLCC is answered here.
	chroot $R /usr/bin/env PATH=/usr/bin:/bin sh -c "exec bluealsa-rfcomm /org/bluealsa/hci0/dev_$(tr : _ < $P/addr) < /tmp/at" 2>&1 | while read -r line; do
		echo "$(date +%T) $line" >> $P/rfcomm.log
		case "$line" in
		*AT+CLCC*)
			[ ! -e $R/tmp/in-call ] || echo '+CLCC: 1,1,0,0,0' >&3
			echo OK >&3
			;;
		esac
	done &
	sleep 1
	echo '+CIEV: 1,1' >&3
	echo '+CIEV: 2,1' >&3
	step "call on"
	sleep 1
fi
NAME="$NAME" SCO_NO_PLAY=1 sh $D/bt-test.sh sco 30 > $P/voice-sco.txt 2>&1 &
sco=$!
sleep 4
step "stream starts"
if [ "$DIR" = tx ]; then
	timeout 24 chroot $R /usr/bin/env PATH=/usr/bin:/bin aplay -q -D "hw:$card,0" -t raw -f S16_LE -c 1 -r 8000 -R 1 --period-size=450 --buffer-size=1800 /tmp/tx.cvsd &
	dir=p
else
	secs=20
	[ "$DIR" = both ] && secs=24
	timeout $secs chroot $R /usr/bin/env PATH=/usr/bin:/bin sh -c "arecord -q -D hw:$card,0 -t raw -f S16_LE -c 1 -r 8000 --period-size=480 --buffer-size=1920 > /tmp/mic.cvsd" &
	dir=c
fi
stream=$!
if [ "$DIR" = both ]; then
	(
		sleep 8
		step "silence starts"
		timeout 12 chroot $R /usr/bin/env PATH=/usr/bin:/bin aplay -q -D "hw:$card,0" -t raw -f S16_LE -c 1 -r 8000 -R 1 --period-size=450 --buffer-size=1800 /tmp/tx.cvsd
		step "silence ended $?"
	) &
	tx=$!
fi
if [ -n "${BT_CALL:-}" ]; then
	(
		sleep 10
		rm -f $R/tmp/in-call
		echo '+CIEV: 2,0' >&3
		step "call off"
	) &
fi
i=0
while [ $i -lt "${secs:-20}" ]; do
	sleep 1
	status $dir
	i=$((i + 1))
	# The link as the controller sees it: read-only, and these lines hold no address.
	if [ "$DIR" = both ] && [ $((i % 6)) = 3 ]; then
		for q in tpl rssi lq; do
			echo "$(date +%T) $(chroot $R /usr/bin/env PATH=/usr/bin:/bin hcitool $q "$(cat $P/addr)" 2>&1)" >> $L
		done
	fi
done
wait $stream; step "stream ended $?"
[ -z "${tx:-}" ] || wait "$tx"
wait $sco
step "link ended"
[ -z "${BT_CALL:-}" ] || killall bluealsa-rfcomm
grep -E 'aplay=|arecord=' $P/voice-sco.txt
[ "$DIR" = tx ] || { cp $R/tmp/mic.cvsd $P/; echo "mic.cvsd bytes: $(wc -c < $P/mic.cvsd)"; }
tail -n 6 $L
rmmod mt6797_btcvsd; echo "rmmod card=$?"
rmmod mtk_btcvsd; echo "rmmod driver=$?"
step finished
dmesg | grep -E 'btcvsd|xrun|Call trace|Oops|WARNING|nobody cared' | grep -vE '([0-9A-Fa-f]{2}:){5}' | tail -12
