#!/bin/sh
# SPDX-License-Identifier: MIT
# One admitted passive scan. The host supplies the already authenticated boot.
set -eu
umask 077
BB=/bin/busybox
: "${EXPECTED_BOOT:?authenticated boot is required}"
kernel=$($BB uname -r)
boot_before=$($BB cat /proc/sys/kernel/random/boot_id)
[ "$kernel" = 7.1.3-gemini-a53-wifi-passive-scan-broadcast ]
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
$BB mkdir /tmp/mt6797-passive-scan-broadcast-1
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
if printf '%s\n' "$channel40" | $BB grep -q '(disabled)'; then
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
# The inert colocated-6GHz hint is accepted, while actual 6GHz stays refused.
# cfg80211 filters the driver's fixed 2.4GHz/UNII-1 list by current permissions.
$BB timeout 12 /lib/ld-linux-aarch64.so.1 --library-path /lib /bin/iw dev wlan0 scan passive
scan_exit=$?
set -e
boot_after=$($BB cat /proc/sys/kernel/random/boot_id)
$BB printf '__IW_PASSIVE_END__\nscan_exit=%s\nboot_after=%s\n' "$scan_exit" "$boot_after"
[ "$boot_after" = "$EXPECTED_BOOT" ]
