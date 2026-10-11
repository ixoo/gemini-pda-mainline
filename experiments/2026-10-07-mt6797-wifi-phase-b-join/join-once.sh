#!/bin/sh
# SPDX-License-Identifier: MIT
# One passive scan followed by one bounded legacy join to the private AP target;
# with a private PSK bound (Phase C2) the pinned supplicant performs the one
# passive scan, the join and the handshake instead, and the driver's bounded
# lifetime ends it. Nothing here prints the SSID, BSSID or PSK.
set -eu
umask 077
BB=/bin/busybox
# Name the failing prerequisite on stderr only when exiting non-zero. The
# success path prints nothing before __IW_PASSIVE_BEGIN__ and keeps stderr empty.
stage=start
event_pid=
# The Phase C3 Wi-Fi listener (started inside data_checks) is owned here. The
# pinned busybox 1.36.1 timeout applet forks a grandchild watchdog and then
# execs the program in its own process, so the shell's $! is Dropbear's pid
# (its pid file repeats it) and the watchdog signals that same pid after the
# absolute limit. Stopping is one signal to the owned pid and one wait, which
# reaps it and records its status; the pid is cleared and never signalled
# again. Called at the terminal record and unconditionally on EXIT, so an
# early failure or signal after the launch cannot leave the listener running.
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
on_exit() {
    rc=$?
    stop_wifi_sshd
    if [ -n "$event_pid" ]; then
        kill "$event_pid" 2>/dev/null || true
    fi
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
[ "$(printf %s "$TARGET_SSID" | $BB wc -c)" -ge 1 ]
[ "$(printf %s "$TARGET_SSID" | $BB wc -c)" -le 32 ]
printf %s "$TARGET_BSSID" | $BB grep -Eq '^[0-9a-f]{2}(:[0-9a-f]{2}){5}$'
stage=kernel_release
kernel=$($BB uname -r)
[ "$kernel" = 7.1.3-gemini-a53-wifi-phase-b-compile ]
stage=boot_identity
boot_before=$($BB cat /proc/sys/kernel/random/boot_id)
[ "$boot_before" = "$EXPECTED_BOOT" ]
stage=single_phy0
[ -d /sys/class/ieee80211/phy0 ]
[ "$($BB cat /sys/class/ieee80211/phy0/index)" = 0 ]
[ "$($BB readlink -f /sys/class/ieee80211/phy0/device)" = "$($BB readlink -f /sys/bus/platform/devices/10001340.consys)" ]
count=0
for phy in /sys/class/ieee80211/phy*; do
    [ -d "$phy" ] || continue
    count=$((count + 1))
done
[ "$count" = 1 ]
stage=no_wlan0
[ ! -e /sys/class/net/wlan0 ]
stage=tmp_leaf
# This small RAM root may omit /tmp. Preserve the one-use leaf refusal.
if [ ! -e /tmp ]; then
    $BB mkdir /tmp
fi
[ -d /tmp ] && [ ! -L /tmp ]
$BB mkdir /tmp/mt6797-wifi-phase-b-1
# The authenticated shell limits regular files to 128 KiB. Keep this
# prerequisite snapshot in memory; the parent exports the complete log later.
stage=pre_scan_readiness
pre_scan_log=$($BB dmesg)
[ "$(printf '%s\n' "$pre_scan_log" | $BB grep -c 'one-shot WLAN TC4 reconciliation: snapshot=2 status=0 ')" = 1 ]
[ "$(printf '%s\n' "$pre_scan_log" | $BB grep -c 'one-shot WLAN regulatory configuration: status=0')" = 1 ]
[ "$(printf '%s\n' "$pre_scan_log" | $BB grep -c 'one-shot WLAN private record prepare: status=0')" = 1 ]
if printf '%s\n' "$pre_scan_log" | $BB grep -q 'one-shot WLAN firmware stopped ('; then
    exit 1
fi
stage=userspace_tools
cd /
$BB sha256sum -c > /dev/null <<'SUMS'
a244c8cc1740d8e3e92589dfd1b9527dbbfc97692cc23e8cfb96cd9d10d8d7da  bin/iw
17538b8f9889a470c061f69a8fea8124da89627311cd16546c133a89f09056df  lib/ld-linux-aarch64.so.1
e4ac8ae1d81e4865e3aadedb962879cf9415903b3f2ba81ec75e9962b86ab8b0  lib/libc.so.6
046856f95f4636f1fc7c3a12bf4f3cd5634c2fc5145c3fdf7395d4f349fa69c7  lib/libgcc_s.so.1
b6152b2f0ef8c2e09de975cd938273db8ad4a33f41dc398945e7081bd4ea6dd4  lib/libnl-3.so.200
08f2d205cb25b90a1a0271a58f9cbfd91810d8067b1b4ebbefa6ba85e83320c9  lib/libnl-genl-3.so.200
bc499f28bc052a24713ead3175e5b6405e2e5f787acf276e4e82c1278241d5ca  bin/join-connect
SUMS
if [ -n "${WPA_PSK_HEX:-}" ]; then
    $BB sha256sum -c > /dev/null <<'SUMS'
0487b7109c0a456eabf3aef33d74d38e5aa4e6dddcb586c03bb203803dd27da7  bin/wpa_supplicant
SUMS
    printf %s "$WPA_PSK_HEX" | $BB grep -Eq '^[0-9a-f]{64}$'
    : "${TARGET_SSID_HEX:?private target SSID hex is required}"
    printf %s "$TARGET_SSID_HEX" | $BB grep -Eq '^([0-9a-f]{2}){1,32}$'
fi
iw() {
    /lib/ld-linux-aarch64.so.1 --library-path /lib /bin/iw "$@"
}
[ "$(iw --version)" = 'iw version 5.19' ]
# Query host cfg80211 state only; require the known-good channel to be usable
# for the passive scan. Under the world regulatory domain channel 40 carries
# NO-IR until a beacon is found there (Phase A scanned in exactly that state);
# transmission is gated separately after the scan, below.
stage=channel40_pre_scan
phy_info=$(iw phy phy0 info)
channel40=$(printf '%s\n' "$phy_info" | $BB grep '\* 5200 MHz \[40\]')
[ "$(printf '%s\n' "$phy_info" | $BB grep -c '\* 5200 MHz \[40\]')" = 1 ]
if printf '%s\n' "$channel40" | $BB grep -Eq 'disabled|radar detection'; then
    exit 1
fi
stage=wlan0_add
iw phy phy0 interface add wlan0 type managed
[ -d /sys/class/net/wlan0 ]
[ "$($BB readlink -f /sys/class/net/wlan0/phy80211)" = "$($BB readlink -f /sys/class/ieee80211/phy0)" ]
[ "$($BB cat /sys/class/net/wlan0/address)" = "$($BB cat /sys/class/ieee80211/phy0/macaddress)" ]
stage=wlan0_up
$BB ip link set wlan0 up
[ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$EXPECTED_BOOT" ]
if [ -n "${WPA_PSK_HEX:-}" ]; then
    # Phase C2: the supplicant owns the connection (control-port frames reach
    # only the connection owner). Its configuration lives in RAM, mode 0600,
    # is never printed and is removed once the supplicant has exited;
    # the complete debug log stays in RAM for the custodian to preserve
    # privately before recovery. No -K: no key material is logged.
    # channel40=1 only when the wiphy query succeeds and exactly one channel-40
    # line is present without disabled, no IR or radar detection; otherwise 0,
    # with the query status, the line count and the flag words found (fixed
    # words only) recorded so a 0 names its reason (runtime 15 reported 0 after
    # an association without them). Never aborts collection.
    channel40_flag() {
        channel40=0
        channel40_lines=0
        channel40_words=none
        # The query's failure is recorded, never fatal under set -e.
        if info=$(iw phy phy0 info 2>/dev/null); then
            channel40_query_exit=0
        else
            channel40_query_exit=$?
            return 0
        fi
        line=$(printf '%s\n' "$info" | $BB grep '\* 5200 MHz \[40\]' || true)
        channel40_lines=$(printf '%s\n' "$line" | $BB grep -c '\* 5200 MHz \[40\]' || true)
        words=$(printf '%s\n' "$line" | $BB grep -Eo 'disabled|no IR|radar detection' | $BB tr ' \n' '_,' || true)
        [ -n "$words" ] && channel40_words=${words%,}
        [ "$channel40_lines" = 1 ] || return 0
        [ "$channel40_words" = none ] && channel40=1
        return 0
    }
    stage=supplicant_config
    $BB printf 'boot_before=%s\nkernel=%s\ninterface_created=1\ninterface_up=1\n__IW_PASSIVE_BEGIN__\n' "$boot_before" "$kernel"
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
    # The mode-0600 RAM configuration stays until the supplicant has exited
    # (no startup race) and is removed before the framed result ends.
    # The pinned static build has no CONFIG_DEBUG_FILE, so -f is not an
    # option it implements (runtime 13: usage text, exit 0, no log); the
    # debug stream goes to stdout and is redirected, with stderr, into the
    # private RAM log created here under umask 077 (mode 0600). No -K.
    /bin/wpa_supplicant -Dnl80211 -iwlan0 -c "$conf" -d > "$wpa_log" 2>&1 &
    supplicant_pid=$!
    # Phase C3 data checks, run once when the driver records the open data
    # phase: busybox udhcpc (foreground, at most 4 tries of 3 s, one lease) with
    # a hook that admits only wlan0, a dotted-quad address and a prefix length
    # of 1..32 (busybox udhcpc exports mask as prefix bits; an absent or odd
    # value is a fixed status, never a guessed /24), adds the address on wlan0,
    # tries the default route through the router, and writes the private
    # lease and prefix files only after the address operation succeeded. Then,
    # on a bound lease, a second Dropbear listener on wlan0's leased address
    # only: the retained binary by digest, the retained host key and the
    # approved authorized-key directory, foreground, password and forwarding
    # disabled like the USB service, idle 30 s, each connection 60 s at most,
    # two auth tries, the whole listener at most 90 s under the admitted
    # busybox timeout (which execs Dropbear in place, so $! is its pid); the
    # readiness marker is written last, after the pid file (written by Dropbear
    # after its listening sockets exist) names that owned pid and it is alive,
    # and the listener is stopped and waited for at the terminal record. Then
    # busybox ping to the router (3 requests, 2 s each). Each step is bounded
    # by busybox timeout. Only counts, statuses and the prefix length are
    # printed; addresses stay in the private RAM files, removed before the
    # framed result ends.
    data_dir=/tmp/mt6797-wifi-phase-b-1
    dropbear_sha256=10663dd45019bc1391730c36d779e6a5e4433fd86311543a714f1a198629bc54
    data_phase_seen=0
    tool_udhcpc=0
    tool_ping=0
    dhcp_exit=255
    dhcp_bound=0
    dhcp_prefix=0
    hook_status=none
    lease_written=0
    dropbear_digest_ok=0
    wifi_sshd_started=0
    wifi_sshd_ready=0
    ping_transmitted=0
    ping_received=0
    data_checks() {
        if $BB --list | $BB grep -qx udhcpc; then tool_udhcpc=1; fi
        if $BB --list | $BB grep -qx ping; then tool_ping=1; fi
        [ "$tool_udhcpc" = 1 ] || return 0
        # shellcheck disable=SC2016  # the hook's own variables stay literal
        $BB printf '#!/bin/sh\nBB=/bin/busybox\ndir=%s\nstatus() { $BB printf %%s "$1" > "$dir/hook-status"; }\ncase "$1" in\n  bound|renew)\n    [ "$interface" = wlan0 ] || { status interface; exit 0; }\n    printf %%s "$ip" | $BB grep -Eq "^([0-9]{1,3}\\.){3}[0-9]{1,3}$" || { status address; exit 0; }\n    printf %%s "$mask" | $BB grep -Eq "^[0-9]{1,2}$" && [ "$mask" -ge 1 ] && [ "$mask" -le 32 ] || { status prefix; exit 0; }\n    $BB ip addr add "$ip/$mask" dev wlan0 || { status addr-failed; exit 0; }\n    for r in $router; do\n      if $BB ip route add default via "$r" dev wlan0 2>/dev/null; then $BB printf %%s "$r" > "$dir/router"; break; fi\n    done\n    $BB printf %%s "$mask" > "$dir/prefix"\n    $BB printf %%s "$ip" > "$dir/lease"\n    status bound\n    ;;\nesac\n' "$data_dir" > "$data_dir/dhcp.sh"
        $BB chmod 700 "$data_dir/dhcp.sh"
        set +e
        $BB timeout 20 $BB udhcpc -i wlan0 -f -n -q -t 4 -T 3 -s "$data_dir/dhcp.sh" > "$data_dir/udhcpc.log" 2>&1
        dhcp_exit=$?
        set -e
        [ -f "$data_dir/hook-status" ] && hook_status=$($BB cat "$data_dir/hook-status")
        if [ "$hook_status" = bound ] && [ -f "$data_dir/lease" ] && [ -f "$data_dir/prefix" ]; then
            dhcp_bound=1
            lease_written=1
            dhcp_prefix=$($BB cat "$data_dir/prefix")
            printf %s "$dhcp_prefix" | $BB grep -Eq '^[0-9]{1,2}$' || dhcp_prefix=0
        fi
        if [ "$dhcp_bound" = 1 ] && [ "$($BB sha256sum /bin/dropbear | $BB cut -c1-64)" = "$dropbear_sha256" ]; then
            dropbear_digest_ok=1
        fi
        if [ "$dropbear_digest_ok" = 1 ] && [ -f /etc/dropbear/host_key ] && [ -d /root/.ssh ]; then
            $BB timeout 90 /bin/dropbear -F -s -j -k -l wlan0 -p "$($BB cat "$data_dir/lease"):22" -D /root/.ssh \
                -r /etc/dropbear/host_key -P "$data_dir/sshd-pid" -I 30 -M 60 -T 2 2> "$data_dir/dropbear.log" &
            wifi_sshd_pid=$!
            wifi_sshd_started=1
            sshd_tick=0
            while [ "$sshd_tick" -lt 6 ] && [ ! -s "$data_dir/sshd-pid" ]; do $BB sleep 0.5; sshd_tick=$((sshd_tick + 1)); done
            if [ -s "$data_dir/sshd-pid" ] && [ "$($BB cat "$data_dir/sshd-pid")" = "$wifi_sshd_pid" ] && kill -0 "$wifi_sshd_pid" 2>/dev/null; then
                $BB cat "$data_dir/lease" > "$data_dir/wifi-ssh"
                wifi_sshd_ready=1
            fi
        fi
        if [ "$dhcp_bound" = 1 ] && [ "$tool_ping" = 1 ] && [ -f "$data_dir/router" ]; then
            set +e
            $BB timeout 12 $BB ping -c 3 -W 2 "$($BB cat "$data_dir/router")" > "$data_dir/ping.log" 2>&1
            set -e
            ping_transmitted=$($BB sed -n 's/^\([0-9][0-9]*\) packets transmitted, \([0-9][0-9]*\) packets received.*/\1/p' "$data_dir/ping.log" | $BB head -n 1)
            ping_received=$($BB sed -n 's/^\([0-9][0-9]*\) packets transmitted, \([0-9][0-9]*\) packets received.*/\2/p' "$data_dir/ping.log" | $BB head -n 1)
            [ -n "$ping_transmitted" ] || ping_transmitted=0
            [ -n "$ping_received" ] || ping_received=0
        fi
    }
    # One bounded wait (at most 100 s): the supplicant's own scan, join and
    # handshake, the driver's data phase of at most 60 s with the data checks
    # inside it, then the driver's lifetime ends with its deauthentication and
    # teardown. A supplicant that fails or exits early cannot abort this
    # script before the framed result and the private log are complete.
    # Terminal records only: the exact final cleanup record (stage 3, credits
    # returned, slots retired) or the explicit stopped (fail-stop) record. An
    # intermediate cleanup stage is not terminal: the supplicant is not
    # signalled while the key removals, station removal, channel abort or BSS
    # off are still in flight. Within the same bound; a timeout is recorded.
    terminal_re='one-shot WLAN join (cleanup: stage=3 credits=returned slots=retired deauth=[01]|stopped:)'
    # The channel-40 IR state is sampled every tick while the supplicant owns
    # the connection: cfg80211 clears the world-domain no-IR flag on the
    # beacon hint and, once every interface is idle after the disconnection
    # (sme.c disconnect_work, reg.c regulatory_hint_disconnect and
    # restore_regulatory_settings), restores it, so the query after the
    # supplicant's exit shows no_IR again (runtime 16). The gate is the
    # state observed during the join; the after-exit state is recorded too.
    tick=0
    terminal=0
    current_log=
    channel40_ir_during_join=0
    channel40_ir_ticks=0
    while [ "$tick" -lt 100 ]; do
        [ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$EXPECTED_BOOT" ]
        current_log=$($BB dmesg)
        if [ "$data_phase_seen" = 0 ] && printf '%s\n' "$current_log" | $BB grep -q 'one-shot WLAN join data phase: budget_ms='; then
            data_phase_seen=1
            data_checks
        fi
        channel40_flag
        if [ "$channel40" = 1 ]; then
            channel40_ir_during_join=1
            channel40_ir_ticks=$((channel40_ir_ticks + 1))
        fi
        if printf '%s\n' "$current_log" | $BB grep -Eq "$terminal_re"; then
            terminal=1
            break
        fi
        tick=$((tick + 1))
        # Runtime 23: the USB listener closes an idle session after 60 s and the
        # wait can run 100 s; one fixed line every 20 ticks keeps it open (the
        # pinned Dropbear counts sent packets as activity). Parsed as a field.
        if [ $((tick % 20)) -eq 0 ]; then
            $BB printf 'keepalive=%s\n' "$tick"
        fi
        $BB sleep 1
    done
    # Driver lifecycle when the wait ended: terminal, intermediate (a cleanup
    # stage without the final record) or none. Recorded; collection goes on.
    lifecycle=none
    if [ "$terminal" = 1 ]; then
        lifecycle=terminal
    elif printf '%s\n' "$current_log" | $BB grep -Eq 'one-shot WLAN join cleanup: stage='; then
        lifecycle=intermediate
    fi
    set +e
    kill "$supplicant_pid" 2>/dev/null
    wait "$supplicant_pid" 2>/dev/null
    supplicant_exit=$?
    set -e
    $BB rm -f "$conf"
    stop_wifi_sshd
    $BB rm -f "$data_dir/lease" "$data_dir/router" "$data_dir/prefix" "$data_dir/dhcp.sh" "$data_dir/wifi-ssh" "$data_dir/sshd-pid" "$data_dir/hook-status"
    stage=supplicant_phrases
    # Fixed phrases only, counted; the complete log is preserved privately.
    # CTRL-EVENT-SCAN-RESULTS is sent only to attached control-interface
    # monitors (wpa_msg_ctrl), never to the debug log, so the one scan is
    # counted by the nl80211 driver's own debug line; the handshake messages
    # are the supplicant's debug lines, printed with -d.
    # Message 3 is logged with the "RSN:" prefix on the WPA2 path
    # (rsn_supp/wpa.c, wpa_supplicant_process_3_of_4) and "WPA:" on the WPA
    # path, so its phrase carries no prefix; the key installs are counted too.
    for phrase in 'nl80211: Received scan results' 'Associated with' 'WPA: RX message 1 of 4-Way Handshake' 'WPA: Sending EAPOL-Key 2/4' 'RX message 3 of 4-Way Handshake' 'WPA: Sending EAPOL-Key 4/4' 'WPA: Installing PTK' 'WPA: Installing GTK' 'WPA: Key negotiation completed' 'CTRL-EVENT-CONNECTED' 'CTRL-EVENT-DISCONNECTED'; do
        key=$(printf %s "$phrase" | $BB tr 'A-Z: /-' 'a-z____')
        $BB printf 'supplicant_%s=%s\n' "$key" "$($BB grep -cF -- "$phrase" "$wpa_log" || true)"
    done
    $BB printf 'supplicant_exit=%s\nsupplicant_log_bytes=%s\n' "$supplicant_exit" "$($BB wc -c < "$wpa_log" 2>/dev/null || echo 0)"
    # The one passive scan is classified from the kernel records by the session;
    # this field only says whether the nl80211 driver reported exactly one result set.
    scan_exit=1
    if [ "$($BB grep -cF -- 'nl80211: Received scan results' "$wpa_log" 2>/dev/null || true)" = 1 ]; then
        scan_exit=0
    fi
    channel40_flag
    $BB printf 'channel40_ir_after_beacon=%s\nchannel40_query_exit=%s\nchannel40_lines=%s\nchannel40_words=%s\n' "$channel40" "$channel40_query_exit" "$channel40_lines" "$channel40_words"
    $BB printf 'channel40_ir_during_join=%s\nchannel40_ir_ticks=%s\n' "$channel40_ir_during_join" "$channel40_ir_ticks"
    $BB printf 'data_phase_seen=%s\ntool_udhcpc=%s\ntool_ping=%s\ndhcp_exit=%s\ndhcp_bound=%s\ndhcp_prefix=%s\nhook_status=%s\nlease_written=%s\n' "$data_phase_seen" "$tool_udhcpc" "$tool_ping" "$dhcp_exit" "$dhcp_bound" "$dhcp_prefix" "$hook_status" "$lease_written"
    $BB printf 'dropbear_digest_ok=%s\nwifi_sshd_started=%s\nwifi_sshd_ready=%s\nwifi_sshd_exit=%s\nping_transmitted=%s\nping_received=%s\n' "$dropbear_digest_ok" "$wifi_sshd_started" "$wifi_sshd_ready" "$wifi_sshd_exit" "$ping_transmitted" "$ping_received"
    stage=boot_after
    $BB printf '__JOIN_END__\nconnect_exit=%s\njoin_terminal=%s\njoin_lifecycle=%s\n' "$supplicant_exit" "$terminal" "$lifecycle"
    boot_after=$($BB cat /proc/sys/kernel/random/boot_id)
    $BB printf '__IW_PASSIVE_END__\nscan_exit=%s\nboot_after=%s\n' "$scan_exit" "$boot_after"
    [ "$boot_after" = "$EXPECTED_BOOT" ]
    exit 0
fi
stage=passive_scan
$BB printf 'boot_before=%s\nkernel=%s\ninterface_created=1\ninterface_up=1\n__IW_PASSIVE_BEGIN__\n' "$boot_before" "$kernel"
printf '__PHY_INFO_BEGIN__\n%s\n__PHY_INFO_END__\n' "$phy_info"
set +e
# One known-good permitted channel; fixed 500 ms dwell is encoded by this candidate.
$BB timeout 12 /lib/ld-linux-aarch64.so.1 --library-path /lib /bin/iw dev wlan0 scan freq 5200 passive > /tmp/mt6797-wifi-phase-b-1/scan.txt
scan_exit=$?
set -e
$BB cat /tmp/mt6797-wifi-phase-b-1/scan.txt
[ "$scan_exit" = 0 ]
stage=bss_match
# Only a matching BSS block on the fixed permitted channel admits connect.
# shellcheck disable=SC2016 # awk field references are intentional
$BB awk -v target="$TARGET_BSSID" '
    /^BSS / { found = ($2 == target "(on") }
    found && $1 == "freq:" && $2 == 5200 { accepted = 1 }
    END { exit !accepted }
' /tmp/mt6797-wifi-phase-b-1/scan.txt
[ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$EXPECTED_BOOT" ]
# The found beacon must have lifted NO-IR on channel 40 (cfg80211 beacon hint)
# before this host transmits anything there.
stage=channel40_ir_after_beacon
channel40_after=$(iw phy phy0 info | $BB grep '\* 5200 MHz \[40\]')
[ "$(printf '%s\n' "$channel40_after" | $BB grep -c '\* 5200 MHz \[40\]')" = 1 ]
if printf '%s\n' "$channel40_after" | $BB grep -Eq 'disabled|no IR|radar detection'; then
    exit 1
fi
$BB printf 'channel40_ir_after_beacon=1\n'
stage=join_readiness
join_log=$($BB dmesg)
[ "$(printf '%s\n' "$join_log" | $BB grep -c 'one-shot passive WLAN scan: status=0 complete=1 ')" = 1 ]
if printf '%s\n' "$join_log" | $BB grep -Eq 'one-shot WLAN (join stopped:|firmware stopped \()'; then
    exit 1
fi
# Event subscription has no radio command. Stop it after this single attempt.
$BB timeout 13 /lib/ld-linux-aarch64.so.1 --library-path /lib /bin/iw event -t > /tmp/mt6797-wifi-phase-b-1/events.txt 2>&1 &
event_pid=$!
stage=connect
$BB printf '__JOIN_BEGIN__\n'
set +e
# One privacy-flagged open-system connect request through the reviewed static
# helper: cfg80211's own station management entity then finds the already
# scanned protected BSS and authenticates and associates without any scan.
# No key, cipher or information element is carried. Its output stays inside
# the framed body: the inherited scan classifier treats any stderr as a failed
# scan, and the scan is independent.
$BB timeout 3 /bin/join-connect wlan0 "$TARGET_SSID" 5200 "$TARGET_BSSID" 2>&1
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
event_pid=
stage=boot_after
$BB cat /tmp/mt6797-wifi-phase-b-1/events.txt
$BB printf '__JOIN_END__\nconnect_exit=%s\njoin_terminal=%s\n' "$connect_exit" "$terminal"
boot_after=$($BB cat /proc/sys/kernel/random/boot_id)
$BB printf '__IW_PASSIVE_END__\nscan_exit=%s\nboot_after=%s\n' "$scan_exit" "$boot_after"
[ "$boot_after" = "$EXPECTED_BOOT" ]
