#!/bin/busybox sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# Desk test of one access point, with the original supplicant, no bgscan and a
# pinned address, then back to the normal link:
#   ssh root@station '/bin/busybox sh -s <freq> [ht20]' < wifi-desk-join.sh
# ht20 holds the link to 20 MHz, with /run/station/ht/wpa_supplicant, built with
# HT overrides, in place of the original supplicant. PEER=<address> in the remote
# command pings that host on this LAN instead of the gateway, once on the normal
# link first, so its own ICMP counters show whether the frames reached it.
# Needs a current /run/station/roam-bss from wifi-roam.sh map. Prints frequency,
# signal and counters only; the private logs stay in /mnt/data/station/desk-*.
export PATH=/bin LD_LIBRARY_PATH=/lib
WPA="wpa_cli -p /run/station/wpa -i wlan0"
F=$1
MODE=${2:-}
SUPPLICANT=wpa_supplicant
EXTRA=
if [ "$MODE" = ht20 ]; then
	SUPPLICANT=/run/station/ht/wpa_supplicant
	EXTRA=disable_ht40=1
	[ -x "$SUPPLICANT" ] || { echo "no $SUPPLICANT"; exit 1; }
fi
MARK="wifi-desk-join: start $F $MODE"
field() { $WPA status | sed -n "s/^$1=//p"; }
gateway() { ip route | awk '/^default/ { print $3; exit }'; }
stop_supplicant() {
	killall wpa_supplicant
	while pidof wpa_supplicant > /dev/null; do sleep 1; done
}
wait_completed() {
	i=0
	while [ "$i" -lt 30 ] && [ "$(field wpa_state)" != COMPLETED ]; do
		sleep 1
		i=$((i + 1))
	done
	echo "after_s=$i state=$(field wpa_state) freq=$(field freq)"
	# A firmware restart takes the address and udhcpc does not notice.
	if [ "$(field wpa_state)" = COMPLETED ] && ! ip -4 addr show wlan0 | grep -q inet; then
		echo "address lost; restarting udhcpc"
		killall udhcpc
		udhcpc -i wlan0 -b -t 10 -T 3 -A 10 -s /run/station/dhcp.sh > "$D/udhcpc.txt" 2>&1
		sleep 15
	fi
}

line=$(awk -v f="$F" '$2 == f { print; exit }' /run/station/roam-bss)
[ -n "$line" ] || { echo "no access point on $F in roam-bss"; exit 1; }
echo "target freq=$F signal=$(echo "$line" | cut -d' ' -f3)"

D=/mnt/data/station/desk-$F$MODE-$(cut -d' ' -f1 /proc/uptime)
mkdir -p "$D" || exit 1
C=/run/station/desk.conf
umask 077
awk -v b="${line%% *}" -v f="$F" -v x="$EXTRA" '
	/^[ \t]*(bssid|scan_freq|freq_list|bgscan)=/ { next }
	{ print }
	/network=\{/ { print "\tbssid=" b; print "\tscan_freq=" f; print "\tfreq_list=" f; if (x != "") print "\t" x }' \
	/run/station/wpa.conf > "$C"

T=${PEER:-$(gateway)}
ping -c 3 -W 2 "$T" | grep 'packets transmitted'
echo "$MARK" > /dev/kmsg
cat /dev/kmsg > "$D/kmsg.txt" &
KMSG=$!
sleep 2
stop_supplicant
"$SUPPLICANT" -dd -Dnl80211 -iwlan0 -c "$C" > "$D/wpa.log" 2>&1 &
wait_completed
if [ "$(field wpa_state)" = COMPLETED ]; then
	ping -c 300 -i 0.2 "$T" > "$D/ping.txt" 2>&1
	grep 'packets transmitted' "$D/ping.txt"
	echo "after ping state=$(field wpa_state) freq=$(field freq)"
	$WPA signal_poll | grep -E '^(AVG_RSSI|LINKSPEED|WIDTH)='
fi

stop_supplicant
rm -f "$C"
wpa_supplicant -Dnl80211 -iwlan0 -c /run/station/wpa.conf > /run/station/wpa.log 2>&1 &
wait_completed
sleep 5
kill "$KMSG"
echo "disconnect_reasons=$(sed -n 's/.*CTRL-EVENT-DISCONNECTED.* reason=\([0-9]*\).*/\1/p' "$D/wpa.log" | tr '\n' ' ')"
sed -n "/$MARK/,\$p" "$D/kmsg.txt" > "$D/test.txt"
echo "active_scans=$(grep -cE 'probing=[1-9]' "$D/test.txt") restarts=$(grep -c 'WLAN restart: begin' "$D/test.txt") stopped=$(grep -c 'join stopped' "$D/test.txt")"
grep -E 'join grant|data qos:' "$D/test.txt" | sed 's/.*one-shot WLAN //'
echo "inet=$(ip -4 addr show wlan0 | grep -c inet) state=$(field wpa_state) freq=$(field freq)"
ping -c 3 -W 2 "$(gateway)" | grep 'packets transmitted'
sync
