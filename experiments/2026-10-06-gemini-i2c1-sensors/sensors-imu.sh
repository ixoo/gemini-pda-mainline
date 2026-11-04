#!/bin/sh
# SPDX-License-Identifier: MIT
# Sample the BMI160 through IIO direct reads, loading nothing. Writes a CSV that
# decode-imu.py reads: a header of scales and the matrix, then raw samples.
# Run on the station: sh sensors-imu.sh OUTPUT SECONDS
set -eu

out=$1
seconds=$2
dev=
for d in /sys/bus/iio/devices/iio:device*; do
	[ "$(cat "$d/name")" = bmi160 ] && dev=$d
done
[ -n "$dev" ] || { echo "no bmi160 IIO device"; exit 1; }

{
	echo "# boot $(cat /proc/sys/kernel/random/boot_id)"
	echo "# accel_scale $(cat "$dev/in_accel_scale")"
	echo "# anglvel_scale $(cat "$dev/in_anglvel_scale")"
	echo "# accel_rate $(cat "$dev/in_accel_sampling_frequency")"
	echo "# anglvel_rate $(cat "$dev/in_anglvel_sampling_frequency")"
	echo "# accel_matrix $(cat "$dev/in_accel_mount_matrix")"
	echo "# anglvel_matrix $(cat "$dev/in_anglvel_mount_matrix")"
	echo "t,ax,ay,az,gx,gy,gz"
} > "$out"

start=$(cut -d' ' -f1 /proc/uptime)
while :; do
	now=$(cut -d' ' -f1 /proc/uptime)
	[ "$(echo "$now $start $seconds" | awk '{print ($1 - $2 < $3)}')" = 1 ] || break
	echo "$now,$(cat "$dev/in_accel_x_raw"),$(cat "$dev/in_accel_y_raw"),$(cat "$dev/in_accel_z_raw"),$(cat "$dev/in_anglvel_x_raw"),$(cat "$dev/in_anglvel_y_raw"),$(cat "$dev/in_anglvel_z_raw")" >> "$out"
	sleep 0.05
done
wc -l "$out"
