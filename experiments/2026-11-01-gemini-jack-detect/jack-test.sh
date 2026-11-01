#!/bin/sh
# SPDX-License-Identifier: MIT
# First jack test: load the audio modules with headphones already in, then log
# every change of the Headphone Jack control for 60 s while the owner unplugs
# and replugs. Run as root on a fresh boot. Prompts go to the terminal.
# Usage: jack-test.sh [BUNDLE]   (default BUNDLE: /tmp/audio)
# Exit: 0 finished, 1 stopped, 2 module load failed, 3 no card.
set -u

B=${1:-/tmp/audio}
RELEASE=7.1.3-gemini-a53-station
OUT=/tmp/jack-test-$(date +%Y%m%d-%H%M%S)
PATH=$B/bin:$PATH
export ALSA_CONFIG_DIR="$B/alsa" ALSA_CONFIG_PATH="$B/alsa/alsa.conf"
mkdir -p "$OUT" || exit 1
exec 3>&2 >"$OUT/run.log" 2>&1

finish() {
	rc=$?
	echo "exit=$rc out=$OUT"
	echo "exit=$rc log=$OUT/run.log" >&3
}
trap finish EXIT

say() { printf '\n== %s ==\n' "$1"; }
tell() { echo "$1"; echo ">>> $1" >&3; }
logs() { dmesg | grep -iE 'mt6351|jack|accdet|asoc' | tail -40; }
fail() {
	echo "STOP: $1"
	logs
	exit "${2:-1}"
}
state() {
	amixer -c "$CARD" cget 'name=Headphone Jack' | sed -n 's/.*: values=//p'
}
count() { grep mt6351-accdet /proc/interrupts || echo 'no mt6351-accdet line'; }

say identity
uname -a
[ "$(uname -r)" = "$RELEASE" ] || fail "release is not $RELEASE"
[ -e "$B/modules/load-order" ] || fail "bundle lacks modules/load-order"

say modules
tell "headphones must already be plugged in: loading now"
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
CARD=$(sed -n 's/^ *\([0-9][0-9]*\) \[mt6797.*/\1/p' /proc/asound/cards | head -1)
[ -n "$CARD" ] || fail "no card index" 3
sleep 2
count
last=$(state)
echo "state 2 s after load, plugged in: $last"
[ -n "$last" ] || fail "no Headphone Jack control"

say changes
tell "for 60 s: unplug, wait 5 s, plug in, wait 5 s; do that three times"
n=0
while [ "$n" -lt 120 ]; do
	now=$(state)
	if [ "$now" != "$last" ]; then
		echo "t=$((n / 2)) s: $last -> $now"
		last=$now
	fi
	n=$((n + 1))
	usleep 500000
done
tell "finished, leave the headphones plugged in"
echo "final state: $last"
count

say dmesg
logs
