#!/bin/sh
# SPDX-License-Identifier: MIT
# Device test of the Gemini UCM profile without installing it: copies the system
# ucm2 tree and this profile to a temporary directory and points alsaucm at it.
# Plays TONE (a quiet 48 kHz S16 stereo WAV) on the speakers, then the headphones,
# and records 2 s from the microphones. Prompts go to stderr. Run as root.
# Usage: ucm-test.sh PROFILE_DIR TONE
set -u
[ "$#" -eq 2 ] || { echo "usage: $0 PROFILE_DIR TONE" >&2; exit 2; }
P=$1
TONE=$2
OUT=/tmp/ucm-test-$(date +%Y%m%d-%H%M%S)
mkdir -p "$OUT/ucm2" || exit 1
cp -R /usr/share/alsa/ucm2/. "$OUT/ucm2/" && cp -R "$P/." "$OUT/ucm2/" || exit 1
export ALSA_CONFIG_UCM2="$OUT/ucm2"
exec 3>&2 >"$OUT/run.log" 2>&1
CARD=hw:mt6797mt6351
tell() { echo ">>> $1"; echo ">>> $1" >&3; }
ctl() { amixer -D "$CARD" cget "name=$1" | sed -n 's/.*: values=//p'; }
state() {
	for c in 'Speaker Switch' 'Headphone Switch' 'Main Mic Switch' 'Back Mic Switch' \
		'Headphone Volume' 'PGA Volume'; do
		echo "$c=$(ctl "$c")"
	done
	echo "jack=$(amixer -D "$CARD" cget 'iface=CARD,name=Headphone Jack' | sed -n 's/.*: values=//p')"
}
# Each alsaucm run is a new manager: setting the verb runs its sequence, which turns every
# output and microphone off, before the named device is enabled.
ucm() { alsaucm -c "$CARD" "$@"; }
use() { ucm set _verb HiFi set _enadev "$1"; }

cat /proc/asound/cards
ucm list _verbs || { tell "no profile found; stop"; exit 1; }
ucm list _devices/HiFi
ucm set _verb HiFi get PlaybackPCM/Speaker get CapturePCM/Mic get JackControl/Headphones

tell "speaker: a quiet tone"
use Speaker
state
aplay -D "$CARD,0" "$TONE"; echo "aplay rc=$?"
tell "headphones: a quiet tone"
use Headphones
state
aplay -D "$CARD,0" "$TONE"; echo "aplay rc=$?"
tell "microphones: 2 s, speak now"
use Mic
state
arecord -D "$CARD,3" -f S16_LE -r 48000 -c 2 -d 2 "$OUT/mic.wav"; echo "arecord rc=$?"
ucm set _verb HiFi
state
echo "out=$OUT" >&3
