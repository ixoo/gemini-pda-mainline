#!/bin/sh
# SPDX-License-Identifier: MIT
# One passive scan followed by one bounded legacy join to the private AP target.
set -eu
umask 077
BB=/bin/busybox
: "${EXPECTED_BOOT:?authenticated boot is required}"
: "${TARGET_SSID:?private target SSID is required}"
: "${TARGET_BSSID:?private target BSSID is required}"
[ "$(printf %s "$TARGET_SSID" | $BB wc -c)" -ge 1 ]
[ "$(printf %s "$TARGET_SSID" | $BB wc -c)" -le 32 ]
printf %s "$TARGET_BSSID" | $BB grep -Eq '^[0-9a-f]{2}(:[0-9a-f]{2}){5}$'
kernel=$($BB uname -r)
boot_before=$($BB cat /proc/sys/kernel/random/boot_id)
[ "$kernel" = 7.1.3-gemini-a53-wifi-phase-b-compile ]
[ "$boot_before" = "$EXPECTED_BOOT" ]
[ -d /sys/class/ieee80211/phy0 ]
[ "$($BB cat /sys/class/ieee80211/phy0/index)" = 0 ]
[ "$($BB readlink -f /sys/class/ieee80211/phy0/device)" = "$($BB readlink -f /sys/bus/platform/devices/10001340.consys)" ]
count=0
for phy in /sys/class/ieee80211/phy*; do
    [ -d "$phy" ] || continue
    count=$((count + 1))
done
[ "$count" = 1 ]
[ ! -e /sys/class/net/wlan0 ]
# This small RAM root may omit /tmp. Preserve the one-use leaf refusal.
if [ ! -e /tmp ]; then
    $BB mkdir /tmp
fi
[ -d /tmp ] && [ ! -L /tmp ]
$BB mkdir /tmp/mt6797-wifi-phase-b-1
# The authenticated shell limits regular files to 128 KiB. Keep this
# prerequisite snapshot in memory; the parent exports the complete log later.
pre_scan_log=$($BB dmesg)
[ "$(printf '%s\n' "$pre_scan_log" | $BB grep -c 'one-shot WLAN TC4 reconciliation: snapshot=2 status=0 ')" = 1 ]
[ "$(printf '%s\n' "$pre_scan_log" | $BB grep -c 'one-shot WLAN regulatory configuration: status=0')" = 1 ]
[ "$(printf '%s\n' "$pre_scan_log" | $BB grep -c 'one-shot WLAN private record prepare: status=0')" = 1 ]
if printf '%s\n' "$pre_scan_log" | $BB grep -q 'one-shot WLAN firmware stopped ('; then
    exit 1
fi
cd /
$BB sha256sum -c > /dev/null <<'SUMS'
a244c8cc1740d8e3e92589dfd1b9527dbbfc97692cc23e8cfb96cd9d10d8d7da  bin/iw
17538b8f9889a470c061f69a8fea8124da89627311cd16546c133a89f09056df  lib/ld-linux-aarch64.so.1
e4ac8ae1d81e4865e3aadedb962879cf9415903b3f2ba81ec75e9962b86ab8b0  lib/libc.so.6
046856f95f4636f1fc7c3a12bf4f3cd5634c2fc5145c3fdf7395d4f349fa69c7  lib/libgcc_s.so.1
b6152b2f0ef8c2e09de975cd938273db8ad4a33f41dc398945e7081bd4ea6dd4  lib/libnl-3.so.200
08f2d205cb25b90a1a0271a58f9cbfd91810d8067b1b4ebbefa6ba85e83320c9  lib/libnl-genl-3.so.200
SUMS
iw() {
    /lib/ld-linux-aarch64.so.1 --library-path /lib /bin/iw "$@"
}
[ "$(iw --version)" = 'iw version 5.19' ]
# Query host cfg80211 state only; require the known-good band to be permitted.
phy_info=$(iw phy phy0 info)
channel40=$(printf '%s\n' "$phy_info" | $BB grep '\* 5200 MHz \[40\]')
[ "$(printf '%s\n' "$phy_info" | $BB grep -c '\* 5200 MHz \[40\]')" = 1 ]
if printf '%s\n' "$channel40" | $BB grep -Eq 'disabled|no IR|radar detection'; then
    exit 1
fi
iw phy phy0 interface add wlan0 type managed
[ -d /sys/class/net/wlan0 ]
[ "$($BB readlink -f /sys/class/net/wlan0/phy80211)" = "$($BB readlink -f /sys/class/ieee80211/phy0)" ]
[ "$($BB cat /sys/class/net/wlan0/address)" = "$($BB cat /sys/class/ieee80211/phy0/macaddress)" ]
$BB ip link set wlan0 up
[ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$EXPECTED_BOOT" ]
$BB printf 'boot_before=%s\nkernel=%s\ninterface_created=1\ninterface_up=1\n__IW_PASSIVE_BEGIN__\n' "$boot_before" "$kernel"
printf '__PHY_INFO_BEGIN__\n%s\n__PHY_INFO_END__\n' "$phy_info"
set +e
# One known-good permitted channel; fixed 500 ms dwell is encoded by this candidate.
$BB timeout 12 /lib/ld-linux-aarch64.so.1 --library-path /lib /bin/iw dev wlan0 scan freq 5200 passive > /tmp/mt6797-wifi-phase-b-1/scan.txt
scan_exit=$?
set -e
$BB cat /tmp/mt6797-wifi-phase-b-1/scan.txt
[ "$scan_exit" = 0 ]
# Only a matching BSS block on the fixed permitted channel admits connect.
# shellcheck disable=SC2016 # awk field references are intentional
$BB awk -v target="$TARGET_BSSID" '
    /^BSS / { found = ($2 == target "(on") }
    found && $1 == "freq:" && $2 == 5200 { accepted = 1 }
    END { exit !accepted }
' /tmp/mt6797-wifi-phase-b-1/scan.txt
[ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$EXPECTED_BOOT" ]
join_log=$($BB dmesg)
[ "$(printf '%s\n' "$join_log" | $BB grep -c 'one-shot passive WLAN scan: status=0 complete=1 ')" = 1 ]
if printf '%s\n' "$join_log" | $BB grep -Eq 'one-shot WLAN (join stopped:|firmware stopped \()'; then
    exit 1
fi
# Event subscription has no radio command. Stop it after this single attempt.
$BB timeout 13 /lib/ld-linux-aarch64.so.1 --library-path /lib /bin/iw event -t > /tmp/mt6797-wifi-phase-b-1/events.txt 2>&1 &
event_pid=$!
trap 'kill "$event_pid" 2>/dev/null || true' EXIT HUP INT TERM
$BB printf '__JOIN_BEGIN__\n'
set +e
$BB timeout 3 /lib/ld-linux-aarch64.so.1 --library-path /lib /bin/iw dev wlan0 connect "$TARGET_SSID" 5200 "$TARGET_BSSID"
connect_exit=$?
set -e
# No disconnect/ifdown/retry: the driver owns finite teardown or fails stop.
tick=0
terminal=0
while [ "$tick" -lt 12 ]; do
    [ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$EXPECTED_BOOT" ]
    current_log=$($BB dmesg)
    if printf '%s\n' "$current_log" | $BB grep -Eq 'one-shot WLAN join (cleanup:|stopped:)'; then
        terminal=1
        break
    fi
    tick=$((tick + 1))
    $BB sleep 1
done
kill "$event_pid" 2>/dev/null || true
wait "$event_pid" 2>/dev/null || true
trap - EXIT HUP INT TERM
$BB cat /tmp/mt6797-wifi-phase-b-1/events.txt
$BB printf '__JOIN_END__\nconnect_exit=%s\njoin_terminal=%s\n' "$connect_exit" "$terminal"
boot_after=$($BB cat /proc/sys/kernel/random/boot_id)
$BB printf '__IW_PASSIVE_END__\nscan_exit=%s\nboot_after=%s\n' "$scan_exit" "$boot_after"
[ "$boot_after" = "$EXPECTED_BOOT" ]
