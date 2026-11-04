#!/bin/sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# Coded audio through the voice path during one eSCO link: 10 s of notes with the
# first bit in the low position, 10 s with it in the high position, and the microphone
# captured throughout. Run after bt-test.sh load and pair, with CONSYS up:
#   NAME='headset' sh bt-voice-test.sh
# The capture holds speech: it is private, and stays under private/.
D=/run/bt-t1
P=$D/private
R=/run/bt-root
at_root() { chroot $R /usr/bin/env PATH=/usr/bin:/bin "$@"; }
in_root() { chroot $R /usr/bin/env PATH=/usr/bin:/bin:/usr/sbin:/sbin "$@"; }
tail -c +45 $D/voice.wav | head -c 80000 > $P/notes.raw
$D/bt-voice encode < $P/notes.raw > $P/notes-low.cvsd
$D/bt-voice encode --msb < $P/notes.raw > $P/notes-high.cvsd
cat $P/notes-low.cvsd $P/notes-high.cvsd > $R/tmp/tx.cvsd
insmod $D/mtk-btcvsd.ko; echo "insmod driver=$?"
insmod $D/mt6797-btcvsd.ko; echo "insmod card=$?"
sleep 1
card=$(sed -n 's/^ *\([0-9][0-9]*\) \[.*mt6797-btcvsd.*/\1/p' /proc/asound/cards | head -1)
[ -n "$card" ] || { echo "no card"; exit 1; }
NAME="$NAME" sh $D/bt-test.sh sco 30 > $P/voice-sco.txt 2>&1 &
sco=$!
sleep 4
in_root sh -c "arecord -q -D hw:$card,0 -t raw -f S16_LE -c 1 -r 64000 --period-size=480 --buffer-size=1920 > /tmp/mic.cvsd" &
timeout 24 chroot $R /usr/bin/env PATH=/usr/bin:/bin aplay -q -D "hw:$card,0" -t raw -f S16_LE -c 1 -r 64000 --period-size=450 --buffer-size=1800 /tmp/tx.cvsd; echo "aplay=$?"
for pid in $(pidof arecord); do
	[ "$(readlink "/proc/$pid/root")" = "$R" ] && kill "$pid"
done
wait $sco
grep -E 'aplay=|arecord=' $P/voice-sco.txt
cp $R/tmp/mic.cvsd $P/ 2>/dev/null
echo "mic.cvsd bytes: $(wc -c < $P/mic.cvsd)"
rmmod mt6797_btcvsd; echo "rmmod card=$?"
rmmod mtk_btcvsd; echo "rmmod driver=$?"
dmesg | grep -E 'btcvsd|xrun|Call trace|Oops|WARNING|nobody cared' | grep -vE '([0-9A-Fa-f]{2}:){5}' | tail -12
