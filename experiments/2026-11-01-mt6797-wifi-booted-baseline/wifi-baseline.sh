#!/bin/busybox sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# Wi-Fi baseline on the running station, fed over SSH:
#   ssh root@station 'HOST=<laptop> /bin/busybox sh -s tput' < wifi-baseline.sh
#   ssh root@station '/bin/busybox sh -s reconnects' < wifi-baseline.sh
# The hold outlives its SSH session, so copy this file to /run/station and run:
#   nohup /bin/busybox sh /run/station/wifi-baseline.sh hold > /run/station/hold.log 2>&1 &
# Prints no network name, peer address or key.
export PATH=/bin LD_LIBRARY_PATH=/lib
WPA="wpa_cli -p /run/station/wpa -i wlan0"
S=/sys/class/net/wlan0/statistics
gateway() { ip route | awk '/^default/ { print $3; exit }'; }
state() { $WPA status | sed -n 's/^wpa_state=//p'; }
uptime_s() { cut -d' ' -f1 /proc/uptime; }

# busybox timeout leaves a transfer running, so kill it and check.
stopped() {
	killall -q "$1"
	sleep 1
	pidof "$1" > /dev/null && { echo "$1 still running"; exit 1; }
	return 0
}

tput() {
	r=1
	while [ $r -le 3 ]; do
		a=$(cat $S/rx_bytes)
		wget -q -O /dev/null "http://$HOST:8931/z.bin" &
		sleep 10
		b=$(cat $S/rx_bytes)
		stopped wget
		echo "rx run=$r Mbit=$(((b - a) * 8 / 10000000))"
		r=$((r + 1))
	done
	r=1
	while [ $r -le 3 ]; do
		a=$(cat $S/tx_bytes)
		dd if=/dev/zero bs=65536 count=100000 2> /dev/null | nc "$HOST" 8932 &
		sleep 10
		b=$(cat $S/tx_bytes)
		stopped nc
		echo "tx run=$r Mbit=$(((b - a) * 8 / 10000000))"
		sleep 2
		r=$((r + 1))
	done
	iw dev wlan0 link | grep -E "freq|signal|tx bitrate"
}

reconnects() {
	gw=$(gateway)
	n=1
	while [ $n -le "${COUNT:-26}" ]; do
		$WPA disconnect > /dev/null
		sleep 2
		t0=$(uptime_s)
		$WPA reconnect > /dev/null
		i=0
		while [ $i -lt 20 ] && [ "$(state)" != COMPLETED ]; do
			sleep 1
			i=$((i + 1))
		done
		t1=$(uptime_s)
		ok=$(ping -c 2 -W 2 "$gw" | grep -c "bytes from")
		echo "reconnect $n state=$(state) start=$t0 end=$t1 ping=$ok/2"
		n=$((n + 1))
	done
}

hold() {
	gw=$(gateway)
	end=$(($(cut -d. -f1 /proc/uptime) + ${SECONDS_HOLD:-9000}))
	while [ "$(cut -d. -f1 /proc/uptime)" -lt "$end" ]; do
		ok=$(ping -c 1 -W 2 "$gw" | grep -c "bytes from")
		echo "$(uptime_s) state=$(state) ping=$ok rx=$(cat $S/rx_bytes) tx=$(cat $S/tx_bytes) $(iw dev wlan0 link | grep -E "signal" | tr -d '\t')"
		sleep 60
	done
}

case "$1" in
tput) tput ;;
reconnects) reconnects ;;
hold) hold ;;
*) echo "usage: tput|reconnects|hold"; exit 2 ;;
esac
