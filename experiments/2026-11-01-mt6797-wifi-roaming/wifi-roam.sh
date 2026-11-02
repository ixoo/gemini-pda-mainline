#!/bin/busybox sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# Roaming tests on the running, connected station, fed over SSH:
#   ssh root@station '/bin/busybox sh -s <mode> [count]' < wifi-roam.sh
# map:      one scan while connected; frequency and signal of each access point of
#           this network. Their addresses stay in /run/station/roam-bss.
# scans N:  N passive scans while connected, with a ping running.
# roams N:  N roams, alternating between the first two addresses in roam-bss, which
#           the operator may edit, each after a scan of those two channels, with a
#           ping running. The network block must not pin a BSSID.
# walk [seconds]: copy this script to the station and start it detached, since USB
#           goes away during it:
#             setsid /bin/busybox sh /run/station/wifi-roam.sh walk </dev/null >/dev/null 2>&1 &
#           Needs /run/station/walk.conf (the network, unpinned, with bgscan and the
#           channels), /run/station/walk-url and /run/station/bg/wpa_supplicant. Logs
#           to /mnt/data/station/, ends at a limit, and restores the normal supplicant.
# Prints no network name, peer address or key; walk's supplicant log has the name.
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
	sed -n 's/.*seq=\([0-9]*\).*/\1/p' "$P" | awk '
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
	fa=$(sed -n 1p "$L" | cut -d' ' -f2)
	fb=$(sed -n 2p "$L" | cut -d' ' -f2)
	ping_start
	n=1
	while [ "$n" -le "$1" ]; do
		if [ "$(field bssid)" = "$a" ]; then to=$b; else to=$a; fi
		# cfg80211 ages a BSS entry out, so a roam needs a recent scan.
		iw dev wlan0 scan freq "$fa" "$fb" passive > /dev/null 2>&1
		echo "scan rc=$?"
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

# Since this boot's log so far, which /dev/kmsg replays first.
walk_count() { n=$(grep -cE "$1" "$D/kmsg.txt"); echo $((n - $2)); }

walk() {
	limit=$1
	D=/mnt/data/station/walk-$(uptime_s)
	mkdir -p "$D" || exit 1
	STOP=$D/stop
	dmesg > "$D/before.txt"
	joins0=$(grep -cE 'connected data phase' "$D/before.txt")
	scans0=$(grep -cE 'probing=[1-9]' "$D/before.txt")
	restarts0=$(grep -cE 'WLAN restart: begin' "$D/before.txt")
	stopped0=$(grep -cE 'join stopped' "$D/before.txt")
	cat /dev/kmsg > "$D/kmsg.txt" &
	KMSG=$!
	sleep 2
	killall wpa_supplicant
	while pidof wpa_supplicant > /dev/null; do sleep 1; done
	/run/station/bg/wpa_supplicant -dd -Dnl80211 -iwlan0 -c /run/station/walk.conf > "$D/wpa.log" 2>&1 &
	(
		while [ ! -e "$STOP" ]; do
			ping -i 0.2 "$(gateway)" >> "$D/ping.txt" 2>&1
			sleep 1
		done
	) &
	(
		while [ ! -e "$STOP" ]; do
			t0=$(uptime_s)
			wget -q -O /dev/null -T 20 "$(cat /run/station/walk-url)" 2> /dev/null
			rc=$?
			echo "fetch start=$t0 end=$(uptime_s) rc=$rc" >> "$D/fetch.txt"
			sleep 1
		done
	) &
	start=$(cut -d. -f1 /proc/uptime)
	why=
	while [ -z "$why" ]; do
		sleep 5
		now=$(cut -d. -f1 /proc/uptime)
		# The first data phase is the supplicant's own join.
		roams=$(($(walk_count 'connected data phase' "$joins0") - 1))
		scans=$(walk_count 'probing=[1-9]' "$scans0")
		restarts=$(walk_count 'WLAN restart: begin' "$restarts0")
		stopped=$(walk_count 'join stopped' "$stopped0")
		# A firmware restart takes the address and udhcpc does not notice, with
		# nobody to restart it during a walk.
		inet=$(ip -4 addr show wlan0 | grep -c inet)
		if [ "$inet" = 0 ] && [ "$(field wpa_state)" = COMPLETED ]; then
			killall udhcpc
			udhcpc -i wlan0 -b -t 10 -T 3 -A 10 -s /run/station/dhcp.sh > "$D/udhcpc.txt" 2>&1
		fi
		[ $((now - start)) -ge "$limit" ] && why="time"
		[ "$roams" -ge 20 ] && why=roams
		[ "$scans" -ge 60 ] && why=scans
		[ "$restarts" -ge 2 ] && why=restarts
		[ "$stopped" -ge 2 ] && why=stopped
		rate=$(iw dev wlan0 station dump | sed -n 's/.*tx bitrate:[[:space:]]*//p')
		avg=$(iw dev wlan0 station dump | sed -n 's/.*signal avg:[[:space:]]*//p')
		echo "t=$((now - start)) roams=$roams scans=$scans restarts=$restarts stopped=$stopped inet=$inet state=$(field wpa_state) freq=$(field freq) avg=$avg rate=$rate" >> "$D/progress.txt"
		sync
	done
	: > "$STOP"
	killall wget ping
	sleep 2
	killall wget ping 2> /dev/null
	killall wpa_supplicant
	while pidof wpa_supplicant > /dev/null; do sleep 1; done
	# A firmware restart takes wlan0 away for a while.
	i=0
	while [ "$i" -lt 30 ] && ! ip link show wlan0 > /dev/null 2>&1; do
		sleep 1
		i=$((i + 1))
	done
	wpa_supplicant -Dnl80211 -iwlan0 -c /run/station/wpa.conf > /run/station/wpa.log 2>&1 &
	sleep 10
	kill "$KMSG"
	{
		echo "end=$why roams=$roams scans=$scans restarts=$restarts stopped=$stopped"
		echo "wget=$(pidof wget) ping=$(pidof ping) state=$(field wpa_state)"
	} > "$D/end.txt"
	sync
}

case "$1" in
walk) walk "${2:-1200}" ;;
map) map ;;
scans) scans "${2:-70}" ;;
roams) roams "${2:-10}" ;;
*) echo "usage: map|scans N|roams N|walk [seconds]"; exit 2 ;;
esac
