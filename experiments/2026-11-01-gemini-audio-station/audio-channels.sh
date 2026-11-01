#!/bin/sh
# SPDX-License-Identifier: MIT
# Second station audio test, on a boot where audio-test.sh already loaded the
# modules: each speaker alone with a gap, GPIO243/244 during playback, then the
# microphones with the speakers playing and with the owner speaking.
# Run as root with the owner present. Prompts go to the terminal.
# Usage: audio-channels.sh [BUNDLE]   (default BUNDLE: /tmp/audio)
# Exit: 0 finished, 1 stopped.
set -u

B=${1:-/tmp/audio}
RELEASE=7.1.3-gemini-a53-station
OUT=/tmp/audio-channels-$(date +%Y%m%d-%H%M%S)
PATH=$B/bin:$PATH
export ALSA_CONFIG_DIR="$B/alsa" ALSA_CONFIG_PATH="$B/alsa/alsa.conf"
CARD=
UNMOUNT=
mkdir -p "$OUT" || exit 1
exec 3>&2 >"$OUT/run.log" 2>&1

finish() {
	rc=$?
	if [ -n "$CARD" ]; then
		for c in Speaker Headphone 'Main Mic' 'Back Mic' 'Headset Mic'; do
			amixer -c "$CARD" -q cset "name=$c Switch" off
		done
		amixer -c "$CARD" -q cset 'name=PGA Volume' 0,0
		amixer -c "$CARD" -q cset 'name=ADDA_DL_CH1 DL1_CH1' off
		amixer -c "$CARD" -q cset 'name=ADDA_DL_CH2 DL1_CH2' off
		amixer -c "$CARD" -q cset 'name=HPL Mux' Open
		amixer -c "$CARD" -q cset 'name=HPR Mux' Open
	fi
	[ -z "$UNMOUNT" ] || umount /sys/kernel/debug
	echo "exit=$rc out=$OUT"
	echo "exit=$rc log=$OUT/run.log" >&3
}
trap finish EXIT

say() { printf '\n== %s ==\n' "$1"; }
tell() { echo "$1"; echo ">>> $1" >&3; }
fail() {
	echo "STOP: $1"
	dmesg | grep -iE 'mt6351|aw873|asoc|afe|audio|snd' | tail -40
	exit 1
}
mix() {
	amixer -c "$CARD" -q cset "name=$1" "$2" || fail "control '$1' refused '$2'"
	echo "set $1=$2"
}
pins() {
	grep -E 'gpio-24[34]' /sys/kernel/debug/gpio
	for f in /sys/kernel/debug/pinctrl/*/pinmux-pins; do
		grep -E '^pin 24[34] ' "$f"
	done
}
# One speaker: play, read the pins while it plays, wait for the end.
speaker() {
	tell "$1 in 4 s, for 8 s"
	sleep 4
	tell "$1 now"
	aplay -D "plughw:$CARD,$PDEV" "$B/$2" &
	p=$!
	sleep 2
	pins
	wait $p
	echo "aplay rc=$?"
	tell "$1 done"
}

say identity
uname -a
[ "$(uname -r)" = "$RELEASE" ] || fail "release is not $RELEASE"
for f in bin/amixer bin/aplay bin/arecord alsa/alsa.conf tone.wav tone-left.wav tone-right.wav; do
	[ -e "$B/$f" ] || fail "bundle lacks $f"
done
CARD=$(sed -n 's/^ *\([0-9][0-9]*\) \[mt6797.*/\1/p' /proc/asound/cards | head -1)
[ -n "$CARD" ] || fail "no card: run audio-test.sh first"
PDEV=$(aplay -l | sed -n "s/^card $CARD:.*device \([0-9]*\): Playback_1.*/\1/p")
CDEV=$(arecord -l | sed -n "s/^card $CARD:.*device \([0-9]*\): Capture_1.*/\1/p")
[ -n "$PDEV" ] && [ -n "$CDEV" ] || fail "PCM devices not found"
if [ ! -e /sys/kernel/debug/gpio ]; then
	mount -t debugfs debugfs /sys/kernel/debug && UNMOUNT=1
fi

say safe-defaults
mix 'Headphone Switch' off
mix 'Headset Mic Switch' off
mix 'Headphone Volume' 0,0
mix 'Lineout Volume' 0,0
mix 'Handset Volume' 0
mix 'PGA Volume' 0,0

say speakers
pins
mix 'DAC In Mux' 'Normal Path'
mix 'HPL Mux' 'Audio Playback'
mix 'HPR Mux' 'Audio Playback'
mix 'ADDA_DL_CH1 DL1_CH1' on
mix 'ADDA_DL_CH2 DL1_CH2' on
mix 'Speaker Switch' on
speaker 'LEFT channel' tone-left.wav
sleep 4
speaker 'RIGHT channel' tone-right.wav
pins

say microphones
mix 'AIF Out Mux' 'Normal Path'
mix 'UL1_CH1 ADDA_UL_CH1' on
mix 'UL1_CH2 ADDA_UL_CH2' on
mix 'ADC L Mux' 'Left Preamplifier'
mix 'ADC R Mux' 'Right Preamplifier'
mix 'PGA L Mux' AIN0
mix 'PGA R Mux' AIN2
mix 'Main Mic Switch' on
mix 'Back Mic Switch' on
# The stock path uses 18 dB; run 3 used the minimum.
mix 'PGA Volume' 3,3

tell "quiet capture, 3 s: please stay silent"
arecord -D "plughw:$CARD,$CDEV" -f S16_LE -r 48000 -c 2 -d 3 "$OUT/quiet.wav"
echo "arecord rc=$?"

tell "capture with the speakers playing, 2 s"
aplay -D "plughw:$CARD,$PDEV" "$B/tone.wav" &
p=$!
arecord -D "plughw:$CARD,$CDEV" -f S16_LE -r 48000 -c 2 -d 2 "$OUT/tone.wav"
echo "arecord rc=$?"
wait $p
echo "aplay rc=$?"
mix 'Speaker Switch' off

tell "speak now, for 5 s"
arecord -D "plughw:$CARD,$CDEV" -f S16_LE -r 48000 -c 2 -d 5 "$OUT/speech.wav"
echo "arecord rc=$?"
tell "finished"

say dmesg
dmesg | grep -iE 'mt6351|aw873|asoc|afe|audio|snd' | tail -40
