#!/bin/sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# One direction of the voice path during one eSCO link. Run after bt-test.sh load and
# pair, with CONSYS up, and only one direction per link:
#   NAME='headset' DIR=rx sh bt-voice-test.sh    the microphone to private/mic.cvsd
#   NAME='headset' DIR=tx sh bt-voice-test.sh    notes to the headset, two bit orders
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
fi
insmod $D/mtk-btcvsd.ko; echo "insmod driver=$?"
insmod $D/mt6797-btcvsd.ko; echo "insmod card=$?"
sleep 1
card=$(sed -n 's/^ *\([0-9][0-9]*\) \[.*mt6797-btcvsd.*/\1/p' /proc/asound/cards | head -1)
[ -n "$card" ] || { step "no card"; exit 1; }
NAME="$NAME" sh $D/bt-test.sh sco 30 > $P/voice-sco.txt 2>&1 &
sco=$!
sleep 4
step "stream starts"
if [ "$DIR" = tx ]; then
	timeout 24 chroot $R /usr/bin/env PATH=/usr/bin:/bin aplay -q -D "hw:$card,0" -t raw -f S16_LE -c 1 -r 8000 -R 1 --period-size=450 --buffer-size=1800 /tmp/tx.cvsd &
	dir=p
else
	timeout 20 chroot $R /usr/bin/env PATH=/usr/bin:/bin sh -c "arecord -q -D hw:$card,0 -t raw -f S16_LE -c 1 -r 8000 --period-size=480 --buffer-size=1920 > /tmp/mic.cvsd" &
	dir=c
fi
stream=$!
i=0
while [ $i -lt 20 ]; do
	sleep 1
	status $dir
	i=$((i + 1))
done
wait $stream; step "stream ended $?"
for pid in $(pidof "$(test "$DIR" = tx && echo aplay || echo arecord)"); do
	[ "$(readlink "/proc/$pid/root")" = "$R" ] && kill "$pid"
done
wait $sco
step "link ended"
grep -E 'aplay=|arecord=' $P/voice-sco.txt
[ "$DIR" = tx ] || { cp $R/tmp/mic.cvsd $P/; echo "mic.cvsd bytes: $(wc -c < $P/mic.cvsd)"; }
tail -n 6 $L
rmmod mt6797_btcvsd; echo "rmmod card=$?"
rmmod mtk_btcvsd; echo "rmmod driver=$?"
step finished
dmesg | grep -E 'btcvsd|xrun|Call trace|Oops|WARNING|nobody cared' | grep -vE '([0-9A-Fa-f]{2}:){5}' | tail -12
