#!/bin/sh
# SPDX-License-Identifier: MIT
# First station audio test: load the audio modules, then a headphone tone, one
# capture from AIN0 and AIN2 and, only with TEST_SPEAKER=1, the same tone on the
# speakers. Run as root on the booted station with headphones attached.
# Usage: [TEST_SPEAKER=1] audio-test.sh [BUNDLE]   (default BUNDLE: /tmp/audio)
# Exit: 0 finished, 1 stopped, 2 module load failed, 3 no card.
set -u

B=${1:-/tmp/audio}
TEST_SPEAKER=${TEST_SPEAKER:-0}
RELEASE=7.1.3-gemini-a53-station
OUT=/tmp/audio-test-$(date +%Y%m%d-%H%M%S)
PATH=$B/bin:$PATH
export ALSA_CONFIG_DIR="$B/alsa" ALSA_CONFIG_PATH="$B/alsa/alsa.conf"
CARD=
mkdir -p "$OUT" || exit 1
exec >"$OUT/run.log" 2>&1

finish() {
	rc=$?
	if [ -n "$CARD" ]; then
		for c in Speaker Headphone 'Main Mic' 'Back Mic' 'Headset Mic'; do
			amixer -c "$CARD" -q sset "$c Switch" off
		done
		amixer -c "$CARD" -q sset 'ADDA_DL_CH1 DL1_CH1' off
		amixer -c "$CARD" -q sset 'ADDA_DL_CH2 DL1_CH2' off
		amixer -c "$CARD" -q sset 'HPL Mux' Open
		amixer -c "$CARD" -q sset 'HPR Mux' Open
	fi
	echo "exit=$rc out=$OUT"
	cat "$OUT/run.log" >&2
}
trap finish EXIT

say() { printf '\n== %s ==\n' "$1"; }
fail() {
	echo "STOP: $1"
	say dmesg
	dmesg | grep -iE 'mt6797|mt6351|aw873|asoc|afe|audio|snd' | tail -60
	exit "${2:-1}"
}
mix() {
	amixer -c "$CARD" -q sset "$1" "$2" || fail "control '$1' refused '$2'"
	echo "set $1=$2"
}
power() {
	for a in 0x10006180 0x10006184 0x10006314; do
		echo "$a $(busybox devmem "$a" 32)"
	done
}

say identity
uname -a
[ "$(uname -r)" = "$RELEASE" ] || fail "release is not $RELEASE"
for f in bin/amixer bin/aplay bin/arecord alsa/alsa.conf tone.wav modules/load-order; do
	[ -e "$B/$f" ] || fail "bundle lacks $f"
done

say power-before
power

say modules
while read -r m; do
	n=$(basename "$m" .ko | tr - _)
	grep -q "^$n " /proc/modules && continue
	insmod "$B/modules/$m" || fail "insmod $m" 2
done <"$B/modules/load-order"
n=0
while ! grep -q mt6797 /proc/asound/cards 2>/dev/null; do
	n=$((n + 1))
	[ "$n" -le 10 ] || fail "no card after 10 s" 3
	sleep 1
done
cat /proc/asound/cards
CARD=$(sed -n 's/^ *\([0-9][0-9]*\) \[mt6797.*/\1/p' /proc/asound/cards | head -1)
[ -n "$CARD" ] || fail "no card index" 3
PDEV=$(aplay -l | sed -n "s/^card $CARD:.*device \([0-9]*\): Playback_1.*/\1/p")
CDEV=$(arecord -l | sed -n "s/^card $CARD:.*device \([0-9]*\): Capture_1.*/\1/p")
echo "playback=$PDEV capture=$CDEV"
[ -n "$PDEV" ] && [ -n "$CDEV" ] || fail "PCM devices not found" 3
amixer -c "$CARD" scontrols

say safe-defaults
mix 'Speaker Switch' off
mix 'Headset Mic Switch' off
mix 'Headphone Volume' 0
mix 'Lineout Volume' 0
mix 'Handset Volume' 0
mix 'PGA Volume' 0
amixer -c "$CARD" sget 'Headphone Volume'

say headphone
mix 'DAC In Mux' 'Normal Path'
mix 'HPL Mux' 'Audio Playback'
mix 'HPR Mux' 'Audio Playback'
mix 'ADDA_DL_CH1 DL1_CH1' on
mix 'ADDA_DL_CH2 DL1_CH2' on
mix 'Headphone Switch' on
aplay -D "plughw:$CARD,$PDEV" "$B/tone.wav" &
p=$!
sleep 1
cat "/proc/asound/card$CARD/pcm${PDEV}p/sub0/status"
cat "/proc/asound/card$CARD/pcm${PDEV}p/sub0/hw_params"
power
wait $p
echo "aplay rc=$?"
mix 'Headphone Switch' off

say capture
mix 'AIF Out Mux' 'Normal Path'
mix 'UL1_CH1 ADDA_UL_CH1' on
mix 'UL1_CH2 ADDA_UL_CH2' on
mix 'ADC L Mux' 'Left Preamplifier'
mix 'ADC R Mux' 'Right Preamplifier'
mix 'PGA L Mux' AIN0
mix 'PGA R Mux' AIN2
mix 'Main Mic Switch' on
mix 'Back Mic Switch' on
arecord -D "plughw:$CARD,$CDEV" -f S16_LE -r 48000 -c 2 -d 2 "$OUT/capture.wav"
echo "arecord rc=$?"
mix 'Main Mic Switch' off
mix 'Back Mic Switch' off

if [ "$TEST_SPEAKER" = 1 ]; then
	say speaker
	mix 'Speaker Switch' on
	aplay -D "plughw:$CARD,$PDEV" "$B/tone.wav" &
	p=$!
	sleep 1
	grep -E 'gpio-24[34]' /sys/kernel/debug/gpio
	wait $p
	echo "aplay rc=$?"
	mix 'Speaker Switch' off
else
	say speaker-skipped
fi

say gpio
grep -E 'gpio-24[34]' /sys/kernel/debug/gpio
for f in /sys/kernel/debug/pinctrl/*/pinmux-pins; do
	grep -E '^pin 24[34] ' "$f"
done

say dmesg
dmesg | grep -iE 'mt6797|mt6351|aw873|asoc|afe|audio|snd' | tail -80
