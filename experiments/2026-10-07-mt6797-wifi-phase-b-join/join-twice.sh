#!/bin/sh
# SPDX-License-Identifier: MIT
# Bounded TWO-lifetime join (proposal 0180) under EXPLICIT supplicant control.
# One active wlan0 vif and one running pinned supplicant serve both cycles; the
# supplicant's auto-reconnect is disabled (STA_AUTOCONNECT 0, source-verified in
# wpa_supplicant 2.11: auto_reconnect_disabled gates the post-disconnect
# reconnect in events.c), so a cycle ends with the driver's own bounded teardown
# and the supplicant stays idle until the wrapper explicitly starts the next
# cycle with select_network. No interface down, no supplicant stop, no retry.
# Cycle 2 is started only after BOTH the kernel re-arm record and the
# attributable cycle-1 host SSH session are observed; the kernel's first-effect
# scan cap is a secondary bound. Each cycle's DHCP/ping/SSH runs in its own
# directory with a fresh readiness marker and receipt; evidence is retained (not
# removed) for host sealing. Nothing prints the SSID, BSSID or PSK.
#
# Budgets: overall wall <= 300 s (monotonic /proc/uptime); per cycle one scan,
# one join, one data phase, one lease, one listener (<=90 s), one ping (3x2 s),
# udhcpc <=20 s; SSH-receipt wait and rearm wait bounded by the overall wall.
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
now_s() { $BB cut -d. -f1 /proc/uptime; }
# True while this boot is live, no named join fault has been recorded, and the
# wall deadline has not passed. Blocking host operations check it so a cycle's
# lease/listener/ping stay within the live data window and stop on a fault.
fatal_record() {
    # A named join fault, any form, is fatal: the stopped footer, a re-arm
    # refusal or a wire-identity wrap. None admits further control.
    $BB dmesg | $BB grep -Eq 'one-shot WLAN join (stopped:|rearm refused:|rearm wrap:)'
}
window_ok() {
    # $1 = current cycle. Live only while this boot holds, the wall deadline has
    # not passed, no named fault was recorded, and THIS cycle's data phase has
    # not yet ended (fewer than $1 "data phase end" records).
    [ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$EXPECTED_BOOT" ] || return 1
    [ "$(now_s)" -lt "${deadline:-0}" ] || return 1
    fatal_record && return 1
    ended=$($BB dmesg | $BB grep -Ec 'one-shot WLAN join data phase end: ' || true)
    [ -n "$ended" ] || ended=0
    [ "$ended" -lt "${1:-1}" ]
}
# Run one blocking host command bounded by BOTH its own timeout and the live
# window: start it as a child, poll the window each second, kill it the moment
# the window closes. $1 cycle, $2 max seconds, $3 log, then the command. Returns
# the child exit, or 137 if the window killed it, or 124 on the timeout.
run_bounded() {
    rb_cyc=$1; rb_max=$2; rb_log=$3; shift 3
    $BB timeout "$rb_max" "$@" > "$rb_log" 2>&1 &
    rb_pid=$!
    while kill -0 "$rb_pid" 2>/dev/null; do
        if ! window_ok "$rb_cyc"; then
            kill "$rb_pid" 2>/dev/null
            wait "$rb_pid" 2>/dev/null
            return 137
        fi
        $BB sleep 1
    done
    wait "$rb_pid"
}

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
04fdf3ae5615f7831461028331bcc6c62d7c6d6974c2676f5b3a93960e5afd22  bin/wpa_cli
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

stage=supplicant_config
$BB printf 'boot_before=%s\nkernel=%s\ninterface_created=1\ninterface_up=1\ncontrol=explicit\ncycles=2\n__IW_PASSIVE_BEGIN__\n' "$boot_before" "$kernel"
printf '__PHY_INFO_BEGIN__\n%s\n__PHY_INFO_END__\n' "$phy_info"
conf=/tmp/mt6797-wifi-phase-b-1/wpa.conf
wpa_log=/tmp/mt6797-wifi-phase-b-1/wpa.log
$BB mkdir -p /tmp/wpa
{
    # scan_res_valid_for_connect=0 forces select_network to scan every time:
    # fast_associate's os_reltime_expired(now,last_scan,0) is always true, so no
    # cached BSS short-circuits a cycle's scan (2.11 events.c). One scan per cycle,
    # independent of the data-phase duration.
    printf 'ctrl_interface=/tmp/wpa\npassive_scan=1\nap_scan=1\nscan_res_valid_for_connect=0\n'
    printf 'network={\n\tssid=%s\n\tbssid=%s\n\tscan_freq=5200\n\tfreq_list=5200\n' "$TARGET_SSID_HEX" "$TARGET_BSSID"
    printf '\tproto=RSN\n\tkey_mgmt=WPA-PSK\n\tpairwise=CCMP\n\tgroup=CCMP\n\tieee80211w=0\n\tdisabled=1\n\tpsk=%s\n}\n' "$WPA_PSK_HEX"
} > "$conf"
unset WPA_PSK_HEX
wpa_cli() { /bin/wpa_cli -p /tmp/wpa -i wlan0 "$@"; }
stage=supplicant_start
$BB printf '__JOIN_BEGIN__\n'
/bin/wpa_supplicant -Dnl80211 -iwlan0 -c "$conf" -d > "$wpa_log" 2>&1 &
supplicant_pid=$!
# Wait for the control socket, then disable auto-reconnect (the race fix).
csock=0
t=0
while [ "$t" -lt 20 ] && [ ! -S /tmp/wpa/wlan0 ]; do $BB sleep 0.5; t=$((t + 1)); done
[ -S /tmp/wpa/wlan0 ] && csock=1
sta_auto=err
if [ "$csock" = 1 ]; then
    [ "$(wpa_cli sta_autoconnect 0 2>/dev/null)" = "OK" ] && sta_auto=0
fi
$BB printf 'ctrl_socket=%s\nsta_autoconnect=%s\n' "$csock" "$sta_auto"
# No scan or any effect is admitted unless the control socket is up and
# auto-reconnect was explicitly disabled (exact OK). A failed control stops now.
stage=control_ready
[ "$csock" = 1 ] || { $BB printf '__STAGE_FAIL__ stage=%s rc=control-socket\n' "$stage" >&2; exit 1; }
[ "$sta_auto" = 0 ] || { $BB printf '__STAGE_FAIL__ stage=%s rc=sta-autoconnect\n' "$stage" >&2; exit 1; }

dropbear_sha256=10663dd45019bc1391730c36d779e6a5e4433fd86311543a714f1a198629bc54
deadline=$(( $(now_s) + 300 ))

# One cycle's Phase C3 data checks into a per-cycle directory. $1 = cycle.
# Returns 0 only when the lease bound, the listener came ready and ping was 3/3;
# otherwise non-zero (the caller stops: no further cycle). Evidence is retained.
data_checks() {
    cyc=$1
    cd="/tmp/mt6797-wifi-phase-b-1/c$cyc"
    $BB mkdir -p "$cd"
    dhcp_exit=255; dhcp_bound=0; dhcp_prefix=0; hook_status=none; lease_written=0
    dropbear_digest_ok=0; wifi_sshd_started=0; wifi_sshd_ready=0
    ping_transmitted=0; ping_received=0
    $BB --list | $BB grep -qx udhcpc || { $BB printf 'cycle=%s data_checks=no-udhcpc\n' "$cyc"; return 1; }
    # shellcheck disable=SC2016
    $BB printf '#!/bin/sh\nBB=/bin/busybox\ndir=%s\nstatus() { $BB printf %%s "$1" > "$dir/hook-status"; }\ncase "$1" in\n  bound|renew)\n    [ "$interface" = wlan0 ] || { status interface; exit 0; }\n    printf %%s "$ip" | $BB grep -Eq "^([0-9]{1,3}\\.){3}[0-9]{1,3}$" || { status address; exit 0; }\n    printf %%s "$mask" | $BB grep -Eq "^[0-9]{1,2}$" && [ "$mask" -ge 1 ] && [ "$mask" -le 32 ] || { status prefix; exit 0; }\n    $BB ip addr add "$ip/$mask" dev wlan0 || { status addr-failed; exit 0; }\n    for r in $router; do\n      if $BB ip route add default via "$r" dev wlan0 2>/dev/null; then $BB printf %%s "$r" > "$dir/router"; break; fi\n    done\n    $BB printf %%s "$mask" > "$dir/prefix"\n    $BB printf %%s "$ip" > "$dir/lease"\n    status bound\n    ;;\nesac\n' "$cd" > "$cd/dhcp.sh"
    $BB chmod 700 "$cd/dhcp.sh"
    dhcp_exit=0
    run_bounded "$cyc" 20 "$cd/udhcpc.log" $BB udhcpc -i wlan0 -f -n -q -t 4 -T 3 -s "$cd/dhcp.sh" || dhcp_exit=$?
    [ -f "$cd/hook-status" ] && hook_status=$($BB cat "$cd/hook-status")
    if [ "$hook_status" = bound ] && [ -f "$cd/lease" ] && [ -f "$cd/prefix" ]; then
        dhcp_bound=1; lease_written=1
        dhcp_prefix=$($BB cat "$cd/prefix")
        printf %s "$dhcp_prefix" | $BB grep -Eq '^[0-9]{1,2}$' || dhcp_prefix=0
    fi
    if [ "$dhcp_bound" = 1 ] && [ "$($BB sha256sum /bin/dropbear | $BB cut -c1-64)" = "$dropbear_sha256" ]; then
        dropbear_digest_ok=1
    fi
    if [ "$dropbear_digest_ok" = 1 ] && [ -f /etc/dropbear/host_key ] && [ -d /root/.ssh ] && window_ok "$cyc"; then
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
    if [ "$dhcp_bound" = 1 ] && [ -f "$cd/router" ] && window_ok "$cyc"; then
        run_bounded "$cyc" 12 "$cd/ping.log" $BB ping -c 3 -W 2 "$($BB cat "$cd/router")" || :
        ping_transmitted=$($BB sed -n 's/^\([0-9][0-9]*\) packets transmitted, \([0-9][0-9]*\) packets received.*/\1/p' "$cd/ping.log" | $BB head -n 1)
        ping_received=$($BB sed -n 's/^\([0-9][0-9]*\) packets transmitted, \([0-9][0-9]*\) packets received.*/\2/p' "$cd/ping.log" | $BB head -n 1)
        [ -n "$ping_transmitted" ] || ping_transmitted=0
        [ -n "$ping_received" ] || ping_received=0
    fi
    $BB printf 'cycle=%s dhcp_exit=%s dhcp_bound=%s dhcp_prefix=%s lease_written=%s dropbear_digest_ok=%s wifi_sshd_started=%s wifi_sshd_ready=%s ping_transmitted=%s ping_received=%s\n' \
        "$cyc" "$dhcp_exit" "$dhcp_bound" "$dhcp_prefix" "$lease_written" "$dropbear_digest_ok" "$wifi_sshd_started" "$wifi_sshd_ready" "$ping_transmitted" "$ping_received"
    [ "$dhcp_bound" = 1 ] && [ "$wifi_sshd_ready" = 1 ] && [ "$ping_received" = 3 ]
}

# Wait (bounded by the overall wall) for a dmesg record to reach at least COUNT.
# Fails on the fault terminal (stopped:) or boot change. Echoes reached count.
wait_record() {
    pat=$1; want=$2
    while [ "$(now_s)" -lt "$deadline" ]; do
        [ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$EXPECTED_BOOT" ] || return 2
        log=$($BB dmesg)
        if printf '%s\n' "$log" | $BB grep -Eq 'one-shot WLAN join (stopped:|rearm refused:|rearm wrap:)'; then
            return 3
        fi
        n=$(printf '%s\n' "$log" | $BB grep -Ec "$pat" || true)
        [ -n "$n" ] || n=0
        [ "$n" -ge "$want" ] && return 0
        $BB sleep 1
    done
    return 1
}
# Wait for the ATTRIBUTABLE per-cycle host acknowledgment: the host adapter does
# the Wi-Fi SSH exchange to this cycle's leased address over the authenticated
# path, validates the live boot, this cycle ordinal, the command output and the
# exit status, and writes "$cd/host-ack" containing "boot=<EXPECTED_BOOT>
# cycle=<N> ssh_exit=0" over authenticated USB. The device only consumes it; a
# generic dropbear session line is NOT accepted. Same fatal/boot/deadline checks
# as wait_record: a boot change, a named join fault (stopped:) or the wall
# deadline ends the wait with no further control. The ack file is retained.
wait_host_ack() {
    ack="/tmp/mt6797-wifi-phase-b-1/c$1/host-ack"
    while [ "$(now_s)" -lt "$deadline" ]; do
        [ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$EXPECTED_BOOT" ] || return 2
        if fatal_record; then
            return 3
        fi
        if [ -f "$ack" ] && [ ! -L "$ack" ] && \
           $BB grep -qxF "host_ack boot=$EXPECTED_BOOT cycle=$1 ssh_exit=0" "$ack"; then
            return 0
        fi
        $BB sleep 1
    done
    return 1
}

terminal_re='one-shot WLAN join cleanup: stage=3 credits=returned slots=retired deauth=[01]'
rearm_re='one-shot WLAN join rearm: lifetime='
data_re='one-shot WLAN join data phase: budget_ms='
overall_rc=0
cyc=1
while [ "$cyc" -le 2 ]; do
    stage=cycle_$cyc
    # Re-check immediately before this cycle's first effect (the select), after
    # the cycle-1 rearm wait: a named fault, a boot change or the wall deadline
    # since then forbids starting another cycle.
    if fatal_record; then $BB printf 'cycle=%s pre_select_fault=1\n' "$cyc"; overall_rc=1; break; fi
    [ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$EXPECTED_BOOT" ] || { $BB printf 'cycle=%s pre_select_boot_changed=1\n' "$cyc"; overall_rc=1; break; }
    [ "$(now_s)" -lt "$deadline" ] || { $BB printf 'cycle=%s pre_select_deadline=1\n' "$cyc"; overall_rc=1; break; }
    # Flush any stale address/route from the previous cycle before this DHCP.
    $BB ip addr flush dev wlan0 2>/dev/null || true
    $BB ip route flush dev wlan0 2>/dev/null || true
    # Explicitly start this cycle; no auto-reconnect is in play.
    sel=$(wpa_cli select_network 0 2>/dev/null || true)
    $BB printf 'cycle=%s select_network=%s\n' "$cyc" "$sel"
    [ "$sel" = "OK" ] || { $BB printf 'cycle=%s select_network_failed=1\n' "$cyc"; overall_rc=1; break; }
    # This cycle's open data phase (the cyc-th data phase record), then its checks.
    wr=0; wait_record "$data_re" "$cyc" || wr=$?
    if [ "$wr" != 0 ]; then $BB printf 'cycle=%s data_phase=fault_or_timeout rc=%s\n' "$cyc" "$wr"; overall_rc=1; break; fi
    stop_wifi_sshd
    dc=0; data_checks "$cyc" || dc=$?
    if [ "$dc" != 0 ]; then $BB printf 'cycle=%s data_checks_failed=1\n' "$cyc"; overall_rc=1; break; fi
    # The attributable per-cycle host acknowledgment (boot+cycle+exit bound).
    wr=0; wait_host_ack "$cyc" || wr=$?
    if [ "$wr" != 0 ]; then $BB printf 'cycle=%s host_ack=absent rc=%s\n' "$cyc" "$wr"; overall_rc=1; break; fi
    $BB printf 'cycle=%s host_ack=present\n' "$cyc"
    # This cycle's healthy terminal (stage 3); a fault stops immediately.
    wr=0; wait_record "$terminal_re" "$cyc" || wr=$?
    if [ "$wr" != 0 ]; then $BB printf 'cycle=%s terminal=fault_or_timeout rc=%s\n' "$cyc" "$wr"; overall_rc=1; break; fi
    stop_wifi_sshd
    wpa_cli disable_network 0 >/dev/null 2>&1 || true
    if [ "$cyc" = 1 ]; then
        # Cycle 2 starts only after BOTH the kernel re-arm and the cycle-1 SSH receipt.
        wr=0; wait_record "$rearm_re" 1 || wr=$?
        if [ "$wr" != 0 ]; then $BB printf 'rearm=absent rc=%s\n' "$wr"; overall_rc=1; break; fi
        $BB printf 'rearm=present\n'
    fi
    cyc=$((cyc + 1))
done

stage=finish
set +e
kill "$supplicant_pid" 2>/dev/null
wait "$supplicant_pid" 2>/dev/null
supplicant_exit=$?
set -e
supplicant_pid=
$BB rm -f "$conf"
stop_wifi_sshd
# Evidence under c1/ c2/ is RETAINED for host sealing; not removed here.
stage=supplicant_phrases
for phrase in 'nl80211: Received scan results' 'Associated with' 'WPA: RX message 1 of 4-Way Handshake' 'WPA: Sending EAPOL-Key 2/4' 'RX message 3 of 4-Way Handshake' 'WPA: Sending EAPOL-Key 4/4' 'WPA: Installing PTK' 'WPA: Installing GTK' 'WPA: Key negotiation completed' 'CTRL-EVENT-CONNECTED' 'CTRL-EVENT-DISCONNECTED'; do
    key=$(printf %s "$phrase" | $BB tr 'A-Z: /-' 'a-z____')
    $BB printf 'supplicant_%s=%s\n' "$key" "$($BB grep -cF -- "$phrase" "$wpa_log" || true)"
done
$BB printf 'supplicant_exit=%s\nsupplicant_log_bytes=%s\nlast_wifi_sshd_exit=%s\n' "$supplicant_exit" "$($BB wc -c < "$wpa_log" 2>/dev/null || echo 0)" "$wifi_sshd_exit"
stage=boot_after
rearms=$($BB dmesg | $BB grep -Ec "$rearm_re" || true); [ -n "$rearms" ] || rearms=0
terminals=$($BB dmesg | $BB grep -Ec "$terminal_re" || true); [ -n "$terminals" ] || terminals=0
$BB printf '__JOIN_END__\nconnect_exit=%s\ncycles_completed=%s\nrearms_observed=%s\nterminals_observed=%s\noverall_rc=%s\n' \
    "$supplicant_exit" "$((cyc - 1))" "$rearms" "$terminals" "$overall_rc"
boot_after=$($BB cat /proc/sys/kernel/random/boot_id)
$BB printf '__IW_PASSIVE_END__\nboot_after=%s\n' "$boot_after"
[ "$boot_after" = "$EXPECTED_BOOT" ]
[ "$overall_rc" = 0 ]
