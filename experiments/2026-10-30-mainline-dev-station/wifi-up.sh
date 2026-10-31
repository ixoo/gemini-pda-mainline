#!/bin/busybox sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# A persistent Wi-Fi station on the running station, fed over SSH:
#   ssh root@station 'sh -s' < wifi-up.sh
# Needs /run/station/wifi-cycles.sh (this directory's) and
# /run/station/wifi.env (mode 0600, RAM only, never in the image or the
# repository) with TARGET_SSID_HEX, TARGET_BSSID and WPA_PSK_HEX.
# Starts the firmware if needed (wifi-cycles.sh with CYCLES=0), loads mac,
# brings wlan0 up and leaves wpa_supplicant (auto-reconnect on) and udhcpc
# (lease renewal) running. Prints the connection state without the network's
# name, address or keys. With DOWN=1 it stops both and unloads mac instead.
export PATH=/bin LD_LIBRARY_PATH=/lib
R=/run/station
M=/lib/modules/$(uname -r)/mac.ko
CTRL=$R/wpa
wpa() { wpa_cli -p $CTRL -i wlan0 "$@"; }

if [ "${DOWN:-0}" = 1 ]; then
	killall udhcpc wpa_supplicant 2>/dev/null
	sleep 1
	lsmod | grep -q '^mac ' && { timeout 30 rmmod mac; echo "down rmmod=$?"; }
	exit 0
fi

[ -f $R/wifi.env ] || { echo "no $R/wifi.env"; exit 1; }
CYCLES=0 sh $R/wifi-cycles.sh || exit 1
lsmod | grep -q '^mac ' || { insmod "$M"; echo "insmod=$?"; sleep 1; }
[ -d /sys/class/net/wlan0 ] || {
	for p in /sys/class/ieee80211/*; do phy=${p##*/}; done
	iw phy "$phy" interface add wlan0 type managed; echo "add $phy=$?"
}
ip link set wlan0 up; echo "up=$?"

umask 077
mkdir -p $CTRL
(
	# shellcheck source=/dev/null
	. $R/wifi.env
	printf 'ctrl_interface=%s\npassive_scan=1\nap_scan=1\n' $CTRL
	printf 'network={\n\tssid=%s\n\tbssid=%s\n\tscan_freq=5200\n\tfreq_list=5200\n' "$TARGET_SSID_HEX" "$TARGET_BSSID"
	printf '\tproto=RSN\n\tkey_mgmt=WPA-PSK\n\tpairwise=CCMP\n\tgroup=CCMP\n\tieee80211w=0\n\tpsk=%s\n}\n' "$WPA_PSK_HEX"
) > $R/wpa.conf
cat > $R/dhcp.sh <<'EOF'
#!/bin/busybox sh
case "$1" in
deconfig)
	ip addr flush dev wlan0
	;;
bound|renew)
	ip addr flush dev wlan0
	ip addr add "$ip/$mask" dev wlan0
	for r in $router; do ip route replace default via "$r" dev wlan0 && break; done
	: > /run/station/wifi-lease
	;;
esac
EOF
chmod 700 $R/dhcp.sh

pidof wpa_supplicant > /dev/null || {
	wpa_supplicant -Dnl80211 -iwlan0 -c $R/wpa.conf > $R/wpa.log 2>&1 &
}
pidof udhcpc > /dev/null || {
	rm -f $R/wifi-lease
	udhcpc -i wlan0 -b -t 10 -T 3 -A 10 -s $R/dhcp.sh > $R/udhcpc.log 2>&1
}
i=0
while [ $i -lt 60 ] && [ ! -e $R/wifi-lease ]; do sleep 1; i=$((i + 1)); done
echo "state=$(wpa status | grep '^wpa_state=' | cut -d= -f2) $(wpa status | grep -E '^(freq|key_mgmt|pairwise_cipher)=' | tr '\n' ' ')"
[ -e $R/wifi-lease ] || { echo "no lease after ${i}s"; exit 1; }
echo "lease after ${i}s"
gw=$(ip route | awk '/^default .*wlan0/ {print $3}')
ping -c 3 -W 2 "$gw" > $R/ping.txt 2>&1
echo "gateway ping: $(grep -o '[0-9]* packets received' $R/ping.txt)"
