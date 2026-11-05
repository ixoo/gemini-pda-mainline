#!/bin/sh
# Light each AW9120 output alone, in output order, for the owner to name.
# Usage: led-walk.sh ON_SECONDS
# One output at 3.5 mA at a time. Everything is off again at the end.
set -u

on=${1:-3}
leds=/sys/class/leds

set_rgb() { # LED INTENSITIES BRIGHTNESS
	echo "$2" > "$leds/$1/multi_intensity" || exit 1
	echo "$3" > "$leds/$1/brightness" || exit 1
}

step=0
walk_rgb() { # LED INTENSITIES
	step=$((step + 1))
	echo "output $step: $1 $2"
	set_rgb "$1" "$2" 255
	sleep "$on"
	echo 0 > "$leds/$1/brightness" || exit 1
	sleep 1
}

walk_single() { # LED
	step=$((step + 1))
	echo "output $step: $1"
	echo 255 > "$leds/$1/brightness" || exit 1
	sleep "$on"
	echo 0 > "$leds/$1/brightness" || exit 1
	sleep 1
}

# Daemon block numbers against output numbers: block 2 is outputs 13-15.
for led in rgb:indicator-1 rgb:indicator-3 rgb:indicator-4 rgb:indicator-5 \
	   rgb:indicator-2 rgb:indicator-6; do
	walk_rgb "$led" "255 0 0"
	walk_rgb "$led" "0 255 0"
	walk_rgb "$led" "0 0 255"
done
walk_single red:indicator-7
walk_single blue:indicator-7

for led in rgb:indicator-1 rgb:indicator-2 rgb:indicator-3 rgb:indicator-4 \
	   rgb:indicator-5 rgb:indicator-6; do
	set_rgb "$led" "255 255 255" 0
done
echo walk complete
