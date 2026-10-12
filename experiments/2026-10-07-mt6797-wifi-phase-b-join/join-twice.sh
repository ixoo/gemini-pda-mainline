#!/bin/sh
# SPDX-License-Identifier: MIT
# Bounded TWO-lifetime variant of join-once.sh (proposal 0180). The same active
# wlan0 vif and the one running pinned supplicant are kept for both cycles: a
# cycle ends with the driver's own bounded teardown (deauth + cleanup), the
# driver re-arms once, and the supplicant's natural reconnect drives the second
# cycle. No interface down, no supplicant stop, no wpa_cli and no retry beyond
# two; the driver's two-lifetime cap refuses a third, which bounds the run.
# Each cycle's DHCP/ping/SSH runs in its own per-cycle directory with a fresh
# readiness marker and receipt so cycle 2 cannot reuse cycle 1's lease, listener
# or ready state. Nothing prints the SSID, BSSID or PSK.
#
# Budgets (finite, per cycle unless marked overall):
#   overall supplicant wait   = 200 s   (OVERALL_TICKS=200, 1 s/tick)
#   data-phase/udhcpc         = 20 s    (4 tries x 3 s, busybox udhcpc)
#   Wi-Fi SSH listener        = 90 s    (busybox timeout around Dropbear)
#   ping                      = 12 s    (3 requests x 2 s)
#   per cycle                 = exactly one scan, one join, one data phase,
#                               one lease, one listener, one ping, one terminal
#   cycles admitted           = 2 (CYCLES); the driver refuses a third scan
#                               at hw_scan (first effect), before any peer/key write
set -eu
umask 077
BB=/bin/busybox
stage=start
wifi_sshd_pid=
wifi_sshd_exit=255
stop_wifi_sshd() {
    [ -n "$wifi_sshd_pid" ] || return 0
    set +e
    kill "$wifi_sshd_pid" 2>/dev/null
    wait "$wifi_sshd_pid"
    wifi_sshd_exit=$?
    set -e
    wifi_sshd_pid=
}
supplicant_pid=
# shellcheck disable=SC2317  # on_exit runs only via the EXIT/HUP/INT/TERM trap
on_exit() {
    rc=$?
    stop_wifi_sshd
    [ -n "$supplicant_pid" ] && { kill "$supplicant_pid" 2>/dev/null || true; }
    if [ "$rc" != 0 ]; then
        $BB printf '__STAGE_FAIL__ stage=%s rc=%s\n' "$stage" "$rc" >&2
    fi
}
trap on_exit EXIT
trap 'exit 1' HUP INT TERM
stage=target_input
: "${EXPECTED_BOOT:?authenticated boot is required}"
: "${TARGET_SSID:?private target SSID is required}"
: "${TARGET_BSSID:?private target BSSID is required}"
: "${WPA_PSK_HEX:?two-lifetime cycles require the PSK-bound supplicant path}"
: "${TARGET_SSID_HEX:?private target SSID hex is required}"
[ "$(printf %s "$TARGET_SSID" | $BB wc -c)" -ge 1 ]
[ "$(printf %s "$TARGET_SSID" | $BB wc -c)" -le 32 ]
printf %s "$TARGET_BSSID" | $BB grep -Eq '^[0-9a-f]{2}(:[0-9a-f]{2}){5}$'
printf %s "$WPA_PSK_HEX" | $BB grep -Eq '^[0-9a-f]{64}$'
printf %s "$TARGET_SSID_HEX" | $BB grep -Eq '^([0-9a-f]{2}){1,32}$'
stage=kernel_release
kernel=$($BB uname -r)
[ "$kernel" = 7.1.3-gemini-a53-wifi-phase-b-compile ]
stage=boot_identity
boot_before=$($BB cat /proc/sys/kernel/random/boot_id)
[ "$boot_before" = "$EXPECTED_BOOT" ]
stage=single_phy0
[ -d /sys/class/ieee80211/phy0 ]
[ "$($BB cat /sys/class/ieee80211/phy0/index)" = 0 ]
stage=no_wlan0
[ ! -e /sys/class/net/wlan0 ]
stage=tmp_leaf
[ -e /tmp ] || $BB mkdir /tmp
[ -d /tmp ] && [ ! -L /tmp ]
$BB mkdir /tmp/mt6797-wifi-phase-b-1
stage=userspace_tools
cd /
$BB sha256sum -c > /dev/null <<'SUMS'
a244c8cc1740d8e3e92589dfd1b9527dbbfc97692cc23e8cfb96cd9d10d8d7da  bin/iw
17538b8f9889a470c061f69a8fea8124da89627311cd16546c133a89f09056df  lib/ld-linux-aarch64.so.1
e4ac8ae1d81e4865e3aadedb962879cf9415903b3f2ba81ec75e9962b86ab8b0  lib/libc.so.6
046856f95f4636f1fc7c3a12bf4f3cd5634c2fc5145c3fdf7395d4f349fa69c7  lib/libgcc_s.so.1
b6152b2f0ef8c2e09de975cd938273db8ad4a33f41dc398945e7081bd4ea6dd4  lib/libnl-3.so.200
08f2d205cb25b90a1a0271a58f9cbfd91810d8067b1b4ebbefa6ba85e83320c9  lib/libnl-genl-3.so.200
0487b7109c0a456eabf3aef33d74d38e5aa4e6dddcb586c03bb203803dd27da7  bin/wpa_supplicant
SUMS
iw() { /lib/ld-linux-aarch64.so.1 --library-path /lib /bin/iw "$@"; }
[ "$(iw --version)" = 'iw version 5.19' ]
stage=wlan0_add
iw phy phy0 interface add wlan0 type managed
[ -d /sys/class/net/wlan0 ]
stage=wlan0_up
$BB ip link set wlan0 up
[ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$EXPECTED_BOOT" ]
phy_info=$(iw phy phy0 info)
# The supplicant keeps ownership across both cycles; ap_scan=1 with the one
# network block makes it re-scan and reconnect after the driver's bounded
# teardown, which the re-armed driver admits as the second lifetime.
stage=supplicant_config
$BB printf 'boot_before=%s\nkernel=%s\ninterface_created=1\ninterface_up=1\ncycles=2\n__IW_PASSIVE_BEGIN__\n' "$boot_before" "$kernel"
printf '__PHY_INFO_BEGIN__\n%s\n__PHY_INFO_END__\n' "$phy_info"
conf=/tmp/mt6797-wifi-phase-b-1/wpa.conf
wpa_log=/tmp/mt6797-wifi-phase-b-1/wpa.log
$BB mkdir -p /tmp/wpa
{
    printf 'ctrl_interface=/tmp/wpa\npassive_scan=1\nap_scan=1\n'
    printf 'network={\n\tssid=%s\n\tbssid=%s\n\tscan_freq=5200\n\tfreq_list=5200\n' "$TARGET_SSID_HEX" "$TARGET_BSSID"
    printf '\tproto=RSN\n\tkey_mgmt=WPA-PSK\n\tpairwise=CCMP\n\tgroup=CCMP\n\tieee80211w=0\n\tpsk=%s\n}\n' "$WPA_PSK_HEX"
} > "$conf"
unset WPA_PSK_HEX
stage=supplicant_start
$BB printf '__JOIN_BEGIN__\n'
/bin/wpa_supplicant -Dnl80211 -iwlan0 -c "$conf" -d > "$wpa_log" 2>&1 &
supplicant_pid=$!
dropbear_sha256=10663dd45019bc1391730c36d779e6a5e4433fd86311543a714f1a198629bc54

# One cycle's Phase C3 data checks into a per-cycle directory. $1 is the cycle
# number; every file (lease, router, prefix, hook, dhcp.sh, sshd-pid, the
# wifi-ssh readiness marker) is under that directory so cycle 2 cannot reuse
# cycle 1's state, listener or receipt. Emits cycle-tagged fields.
data_checks() {
    cyc=$1
    cd="/tmp/mt6797-wifi-phase-b-1/c$cyc"
    $BB mkdir -p "$cd"
    tool_udhcpc=0; tool_ping=0; dhcp_exit=255; dhcp_bound=0; dhcp_prefix=0
    hook_status=none; lease_written=0; dropbear_digest_ok=0
    wifi_sshd_started=0; wifi_sshd_ready=0; ping_transmitted=0; ping_received=0
    if $BB --list | $BB grep -qx udhcpc; then tool_udhcpc=1; fi
    if $BB --list | $BB grep -qx ping; then tool_ping=1; fi
    [ "$tool_udhcpc" = 1 ] || return 0
    # shellcheck disable=SC2016
    $BB printf '#!/bin/sh\nBB=/bin/busybox\ndir=%s\nstatus() { $BB printf %%s "$1" > "$dir/hook-status"; }\ncase "$1" in\n  bound|renew)\n    [ "$interface" = wlan0 ] || { status interface; exit 0; }\n    printf %%s "$ip" | $BB grep -Eq "^([0-9]{1,3}\\.){3}[0-9]{1,3}$" || { status address; exit 0; }\n    printf %%s "$mask" | $BB grep -Eq "^[0-9]{1,2}$" && [ "$mask" -ge 1 ] && [ "$mask" -le 32 ] || { status prefix; exit 0; }\n    $BB ip addr add "$ip/$mask" dev wlan0 || { status addr-failed; exit 0; }\n    for r in $router; do\n      if $BB ip route add default via "$r" dev wlan0 2>/dev/null; then $BB printf %%s "$r" > "$dir/router"; break; fi\n    done\n    $BB printf %%s "$mask" > "$dir/prefix"\n    $BB printf %%s "$ip" > "$dir/lease"\n    status bound\n    ;;\nesac\n' "$cd" > "$cd/dhcp.sh"
    $BB chmod 700 "$cd/dhcp.sh"
    set +e
    $BB timeout 20 $BB udhcpc -i wlan0 -f -n -q -t 4 -T 3 -s "$cd/dhcp.sh" > "$cd/udhcpc.log" 2>&1
    dhcp_exit=$?
    set -e
    [ -f "$cd/hook-status" ] && hook_status=$($BB cat "$cd/hook-status")
    if [ "$hook_status" = bound ] && [ -f "$cd/lease" ] && [ -f "$cd/prefix" ]; then
        dhcp_bound=1; lease_written=1
        dhcp_prefix=$($BB cat "$cd/prefix")
        printf %s "$dhcp_prefix" | $BB grep -Eq '^[0-9]{1,2}$' || dhcp_prefix=0
    fi
    if [ "$dhcp_bound" = 1 ] && [ "$($BB sha256sum /bin/dropbear | $BB cut -c1-64)" = "$dropbear_sha256" ]; then
        dropbear_digest_ok=1
    fi
    if [ "$dropbear_digest_ok" = 1 ] && [ -f /etc/dropbear/host_key ] && [ -d /root/.ssh ]; then
        $BB timeout 90 /bin/dropbear -F -s -j -k -l wlan0 -p "$($BB cat "$cd/lease"):22" -D /root/.ssh \
            -r /etc/dropbear/host_key -P "$cd/sshd-pid" -I 30 -M 60 -T 2 2> "$cd/dropbear.log" &
        wifi_sshd_pid=$!
        wifi_sshd_started=1
        t=0
        while [ "$t" -lt 6 ] && [ ! -s "$cd/sshd-pid" ]; do $BB sleep 0.5; t=$((t + 1)); done
        if [ -s "$cd/sshd-pid" ] && [ "$($BB cat "$cd/sshd-pid")" = "$wifi_sshd_pid" ] && kill -0 "$wifi_sshd_pid" 2>/dev/null; then
            $BB cat "$cd/lease" > "$cd/wifi-ssh"
            wifi_sshd_ready=1
        fi
    fi
    if [ "$dhcp_bound" = 1 ] && [ "$tool_ping" = 1 ] && [ -f "$cd/router" ]; then
        set +e
        $BB timeout 12 $BB ping -c 3 -W 2 "$($BB cat "$cd/router")" > "$cd/ping.log" 2>&1
        set -e
        ping_transmitted=$($BB sed -n 's/^\([0-9][0-9]*\) packets transmitted, \([0-9][0-9]*\) packets received.*/\1/p' "$cd/ping.log" | $BB head -n 1)
        ping_received=$($BB sed -n 's/^\([0-9][0-9]*\) packets transmitted, \([0-9][0-9]*\) packets received.*/\2/p' "$cd/ping.log" | $BB head -n 1)
        [ -n "$ping_transmitted" ] || ping_transmitted=0
        [ -n "$ping_received" ] || ping_received=0
    fi
    $BB printf 'cycle=%s dhcp_exit=%s dhcp_bound=%s dhcp_prefix=%s lease_written=%s dropbear_digest_ok=%s wifi_sshd_started=%s wifi_sshd_ready=%s wifi_sshd_exit=%s ping_transmitted=%s ping_received=%s\n' \
        "$cyc" "$dhcp_exit" "$dhcp_bound" "$dhcp_prefix" "$lease_written" "$dropbear_digest_ok" "$wifi_sshd_started" "$wifi_sshd_ready" "$wifi_sshd_exit" "$ping_transmitted" "$ping_received"
}

terminal_re='one-shot WLAN join (cleanup: stage=3 credits=returned slots=retired deauth=[01]|stopped:)'
rearm_re='one-shot WLAN join rearm: lifetime='
# Two cycles over the one supplicant. A cycle is: observe its data phase (run
# the per-cycle data checks once), then its terminal. Between cycles the driver
# must record exactly one re-arm; the supplicant reconnects on its own. The
# overall wait bounds the whole run; a fault stops at once (no third cycle, no
# retry) and the driver cap refuses any third lifetime regardless.
OVERALL_TICKS=200
CYCLES=2
cyc=1
data_seen=0
rearms=0
terminals=0
tick=0
prev_terminal_count=0
while [ "$tick" -lt "$OVERALL_TICKS" ] && [ "$terminals" -lt "$CYCLES" ]; do
    [ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$EXPECTED_BOOT" ]
    current_log=$($BB dmesg)
    if [ "$data_seen" -lt "$cyc" ]; then
        # The cyc-th data phase record marks this cycle's open data phase.
        n=$(printf '%s\n' "$current_log" | $BB grep -c 'one-shot WLAN join data phase: budget_ms=')
        if [ "$n" -ge "$cyc" ]; then
            data_seen=$cyc
            stop_wifi_sshd
            data_checks "$cyc"
        fi
    fi
    rearms=$(printf '%s\n' "$current_log" | $BB grep -c "$rearm_re")
    tcount=$(printf '%s\n' "$current_log" | $BB grep -Ec "$terminal_re")
    if [ "$tcount" -gt "$prev_terminal_count" ]; then
        prev_terminal_count=$tcount
        terminals=$tcount
        stop_wifi_sshd
        if [ "$terminals" -lt "$CYCLES" ]; then
            cyc=$((cyc + 1))
        fi
    fi
    tick=$((tick + 1))
    if [ $((tick % 20)) -eq 0 ]; then
        $BB printf 'keepalive=%s\n' "$tick"
    fi
    $BB sleep 1
done

set +e
kill "$supplicant_pid" 2>/dev/null
wait "$supplicant_pid" 2>/dev/null
supplicant_exit=$?
set -e
supplicant_pid=
$BB rm -f "$conf"
stop_wifi_sshd
$BB rm -rf /tmp/mt6797-wifi-phase-b-1/c1 /tmp/mt6797-wifi-phase-b-1/c2
stage=supplicant_phrases
for phrase in 'nl80211: Received scan results' 'Associated with' 'WPA: RX message 1 of 4-Way Handshake' 'WPA: Sending EAPOL-Key 2/4' 'RX message 3 of 4-Way Handshake' 'WPA: Sending EAPOL-Key 4/4' 'WPA: Installing PTK' 'WPA: Installing GTK' 'WPA: Key negotiation completed' 'CTRL-EVENT-CONNECTED' 'CTRL-EVENT-DISCONNECTED'; do
    key=$(printf %s "$phrase" | $BB tr 'A-Z: /-' 'a-z____')
    $BB printf 'supplicant_%s=%s\n' "$key" "$($BB grep -cF -- "$phrase" "$wpa_log" || true)"
done
$BB printf 'supplicant_exit=%s\nsupplicant_log_bytes=%s\n' "$supplicant_exit" "$($BB wc -c < "$wpa_log" 2>/dev/null || echo 0)"
stage=boot_after
$BB printf '__JOIN_END__\nconnect_exit=%s\ncycles_observed=%s\nrearms_observed=%s\nterminals_observed=%s\n' \
    "$supplicant_exit" "$cyc" "$rearms" "$terminals"
boot_after=$($BB cat /proc/sys/kernel/random/boot_id)
$BB printf '__IW_PASSIVE_END__\nboot_after=%s\n' "$boot_after"
[ "$boot_after" = "$EXPECTED_BOOT" ]
exit 0
