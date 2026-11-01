#!/bin/sh
# SPDX-License-Identifier: MIT
# Jack test: log the Headphone Jack control and the ACCDET interrupt count while
# the owner unplugs and replugs, then play with the headphones out to see whether
# playback alone raises the interrupt. With RELOAD=1, instead reload the audio
# modules with the headphones in and read the state.
# Run as root with the headphones in. Prompts go to stderr and the console.
# Usage: [RELOAD=1] jack-test.sh [BUNDLE]   (default BUNDLE: /tmp/audio)
# Exit: 0 finished, 1 stopped, 2 module load failed, 3 no card.
set -u

B=${1:-/tmp/audio}
RELOAD=${RELOAD:-0}
RELEASE=7.1.3-gemini-a53-station
OUT=/tmp/jack-test-$(date +%Y%m%d-%H%M%S)
PATH=$B/bin:$PATH
export ALSA_CONFIG_DIR="$B/alsa" ALSA_CONFIG_PATH="$B/alsa/alsa.conf"
CARD=
mkdir -p "$OUT" || exit 1
exec 3>&2 >"$OUT/run.log" 2>&1

finish() {
	rc=$?
	if [ -n "$CARD" ]; then
		amixer -c "$CARD" -q cset 'name=Headphone Switch' off
		amixer -c "$CARD" -q cset 'name=ADDA_DL_CH1 DL1_CH1' off
		amixer -c "$CARD" -q cset 'name=ADDA_DL_CH2 DL1_CH2' off
		amixer -c "$CARD" -q cset 'name=HPL Mux' Open
		amixer -c "$CARD" -q cset 'name=HPR Mux' Open
	fi
	echo "exit=$rc out=$OUT"
	echo "exit=$rc log=$OUT/run.log" >&3
}
trap finish EXIT

say() { printf '\n== %s ==\n' "$1"; }
now() { cut -d' ' -f1 /proc/uptime; }
tell() {
	echo "[$(now)] $1"
	echo ">>> $1" >&3
	echo ">>> $1" >/dev/tty1 2>/dev/null
}
logs() { dmesg | grep -iE 'mt6351|jack|accdet|asoc' | tail -40; }
fail() {
	echo "STOP: $1"
	logs
	exit "${2:-1}"
}
mix() {
	amixer -c "$CARD" -q cset "name=$1" "$2" || fail "control '$1' refused '$2'"
	echo "set $1=$2"
}
findcard() {
	CARD=$(sed -n 's/^ *\([0-9][0-9]*\) \[mt6797.*/\1/p' /proc/asound/cards 2>/dev/null | head -1)
}
state() {
	amixer -c "$CARD" cget 'iface=CARD,name=Headphone Jack' | sed -n 's/.*: values=//p'
}
count() {
	sed -n 's/^ *[0-9]*: *\([0-9 ]*\).*mt6351-accdet.*/\1/p' /proc/interrupts |
		awk '{ for (i = 1; i <= NF; i++) n += $i; print n + 0 }'
}
# Log every change of the state or the interrupt count for $1 seconds.
watch_jack() {
	s=$(state)
	c=$(count)
	echo "[$(now)] start: state=$s irq=$c"
	i=0
	while [ "$i" -lt "$1" ]; do
		sleep 1
		i=$((i + 1))
		ns=$(state)
		nc=$(count)
		if [ "$ns" != "$s" ] || [ "$nc" != "$c" ]; then
			echo "[$(now)] state=$ns irq=$nc"
			s=$ns
			c=$nc
		fi
	done
	echo "[$(now)] end: state=$s irq=$c"
}
load() {
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
	findcard
	[ -n "$CARD" ] || fail "no card index" 3
}

say identity
uname -a
[ "$(uname -r)" = "$RELEASE" ] || fail "release is not $RELEASE"
[ -e "$B/modules/load-order" ] || fail "bundle lacks modules/load-order"

if [ "$RELOAD" = 1 ]; then
	say reload
	tell "headphones must stay in: reloading the audio modules"
	CARD=
	for m in mt6797_mt6351 snd_soc_mt6797_afe snd_soc_aw8738 snd_soc_mt6351; do
		rmmod "$m" || fail "rmmod $m"
	done
	load
	sleep 2
	echo "[$(now)] 2 s after load, headphones in: state=$(state) irq=$(count)"
	say dmesg
	logs
	exit 0
fi

say modules
load
[ -n "$(state)" ] || fail "no Headphone Jack control"

say cycles
tell "headphones in. In 5 s: unplug, wait 5 s, plug in, wait 5 s; three times, within 60 s"
sleep 5
tell "start now"
watch_jack 60
tell "stop now, leave the headphones in"

say playback-with-headphones-out
tell "please UNPLUG the headphones within 10 s and leave them out"
watch_jack 10
tell "playing with the headphones out; nothing to hear"
mix 'Speaker Switch' off
mix 'Headphone Volume' 0,0
mix 'DAC In Mux' 'Normal Path'
mix 'HPL Mux' 'Audio Playback'
mix 'HPR Mux' 'Audio Playback'
mix 'ADDA_DL_CH1 DL1_CH1' on
mix 'ADDA_DL_CH2 DL1_CH2' on
mix 'Headphone Switch' on
echo "[$(now)] before: state=$(state) irq=$(count)"
aplay -D "plughw:$CARD,0" "$B/tone.wav"
echo "aplay rc=$?"
echo "[$(now)] after: state=$(state) irq=$(count)"
mix 'Headphone Switch' off
watch_jack 5

say plug-after-playback
tell "please PLUG the headphones in within 10 s"
watch_jack 10
tell "finished, leave the headphones in"

say dmesg
logs
