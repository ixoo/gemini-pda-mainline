#!/bin/busybox sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# Roaming tests on the running, connected station, fed over SSH:
#   ssh root@station '/bin/busybox sh -s <mode> [count]' < wifi-roam.sh
# map:      one scan while connected; frequency and signal of each access point of
#           this network. Their addresses stay in /run/station/roam-bss.
# scans N:  N passive scans while connected, with a ping running.
# roams N:  N roams, alternating between the first two addresses in roam-bss, which
#           the operator may edit, with a ping running.
# Prints no network name, peer address or key.
export PATH=/bin LD_LIBRARY_PATH=/lib
WPA="wpa_cli -p /run/station/wpa -i wlan0"
L=/run/station/roam-bss
P=/run/station/roam-ping
gateway() { ip route | awk '/^default/ { print $3; exit }'; }
field() { $WPA status | sed -n "s/^$1=//p"; }
uptime_s() { cut -d' ' -f1 /proc/uptime; }

# The longest run of missing replies, in pings 200 ms apart.
ping_start() { ping -i 0.2 "$(gateway)" > "$P" 2>&1 & PING=$!; }
ping_stop() {
	kill "$PING"
	sleep 1
	pidof ping > /dev/null && echo "ping still running"
	sed -n 's/.*icmp_seq=\([0-9]*\).*/\1/p' "$P" | awk '
		{ if (NR > 1 && $1 - last - 1 > gap) gap = $1 - last - 1; last = $1 }
		END { print "ping replies=" NR " longest_gap_pings=" gap + 0 }'
}

map() {
	name=$(field ssid)
	iw dev wlan0 scan passive > /run/station/roam-scan 2>&1
	echo "scan rc=$? state=$(field wpa_state)"
	NAME="$name" awk '
		/^BSS / { b = substr($2, 1, 17); f = ""; s = "" }
		/^\tfreq:/ { f = int($2) }
		/^\tsignal:/ { s = $2 }
		/^\tSSID: / { n = $0; sub(/^\tSSID: /, "", n)
			if (n == ENVIRON["NAME"]) print b, f, s }' /run/station/roam-scan > "$L"
	rm -f /run/station/roam-scan
	awk '{ print "bss " NR " freq=" $2 " signal=" $3 }' "$L"
	echo "current freq=$(field freq)"
}

scans() {
	ping_start
	n=1
	while [ "$n" -le "$1" ]; do
		t0=$(uptime_s)
		iw dev wlan0 scan passive > /run/station/roam-scan 2>&1
		rc=$?
		echo "scan $n rc=$rc bss=$(grep -c '^BSS ' /run/station/roam-scan) start=$t0 end=$(uptime_s) state=$(field wpa_state)"
		rm -f /run/station/roam-scan
		n=$((n + 1))
		sleep 2
	done
	ping_stop
}

roams() {
	a=$(sed -n 1p "$L" | cut -d' ' -f1)
	b=$(sed -n 2p "$L" | cut -d' ' -f1)
	[ -n "$a" ] && [ -n "$b" ] || { echo "need two addresses"; exit 1; }
	ping_start
	n=1
	while [ "$n" -le "$1" ]; do
		if [ "$(field bssid)" = "$a" ]; then to=$b; else to=$a; fi
		t0=$(uptime_s)
		$WPA roam "$to" > /dev/null
		sleep 1
		i=0
		while [ $i -lt 20 ] && { [ "$(field wpa_state)" != COMPLETED ] || [ "$(field bssid)" != "$to" ]; }; do
			sleep 1
			i=$((i + 1))
		done
		if [ "$(field bssid)" = "$to" ]; then at=target; else at=other; fi
		echo "roam $n at=$at state=$(field wpa_state) freq=$(field freq) start=$t0 end=$(uptime_s)"
		n=$((n + 1))
		sleep 10
	done
	ping_stop
	dmesg | grep -cE "WLAN restart: begin" | sed 's/^/restarts=/'
	dmesg | grep -cE "join without a scan" | sed 's/^/scanless=/'
}

case "$1" in
map) map ;;
scans) scans "${2:-70}" ;;
roams) roams "${2:-10}" ;;
*) echo "usage: map|scans N|roams N"; exit 2 ;;
esac
