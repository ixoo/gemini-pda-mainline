#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# shellcheck disable=SC2317  # the seal, freeze, restore and finish functions run from the exit trap
# One bounded v10 lifecycle capture under the gwref10 observer: disconnect,
# connect, target-only traffic window, disconnect; seal; verify and freeze the
# capture; then one restoration connect outside the capture.
#
# Run by the device custodian as root on the verified v10 boot, boot ID as the
# only argument, launched under systemd 232 so it survives losing the LAN:
#   systemd-run --unit=gemini-wifi-lifecycle-v10 -p RuntimeMaxSec=300 \
#     -p KillMode=control-group /root/.gemini-wifi-reference/trace-lifecycle-v10.sh <boot-id>
# Phase budgets on the monotonic clock: preflight 30 s, setup 20 s, capture 150 s
# after arm (observer deadline 240 s), seal 10 s, preservation 20 s, restoration
# 60 s, finalisation 5 s; 295 s in all, under the unit's 300 s. Every external
# call and wait is clamped to its phase deadline (timeout with a 2 s kill-after).
# Inside the capture the readiness wait, the connect allowance (RPC and the
# connected wait share it) and the traffic window are each granted only what
# leaves the later stages their reserve, so the window is never opened without
# enough budget for itself and the second teardown.
# Live identity is checked before every observer write and every radio call.
# Single use per boot. Exit codes: 0 complete and restored, 2 refused before any
# radio action, 3 restoration or AutoConnect restoration failed, 4 a budget was
# exhausted, 5 a step failed (partial receipt), 6 the seal was not captured,
# 7 live identity was lost (no further action taken).
set -euo pipefail
export LC_ALL=C
umask 077

readonly expected_release=3.18.41-gemini-wifi-ref10+
readonly sysroot=${GWREF10_SYSROOT:-}
readonly output=${GWREF10_OUTPUT:-/var/tmp/gemini-wifi-reference-lifecycle-v10}
readonly control=$sysroot/sys/module/wlan_gen3/parameters/gwref10
readonly boot_file=$sysroot/proc/sys/kernel/random/boot_id
readonly printk_file=$sysroot/proc/sys/kernel/printk
readonly carrier_file=$sysroot/sys/class/net/wlan0/carrier
readonly battery=$sysroot/sys/class/power_supply/battery
here=$(dirname "$(readlink -f "$0")")
readonly here
readonly check=${GWREF10_CHECK:-$here/lifecycle/cycle-check.py}
readonly kmsg_source=${GWREF10_KMSG_SOURCE:-/dev/kmsg}
readonly kmsg_bound=8388608
readonly tick=${GWREF10_TICK:-1}
readonly iw=${GWREF10_IW:-/sbin/iw}
readonly wpa_cli=${GWREF10_WPA_CLI:-/sbin/wpa_cli}
# Freshness bound for the target BSS in wpa_supplicant's table before the measured
# connect: a chosen limit, not a claimed scan period.
readonly bss_fresh_limit=${GWREF10_BSS_FRESH_S:-10}
readonly bss_snapshot_limit=90   # private raw query outputs kept, at most
# Budgets in seconds; the divisor exists only for the offline fixture and is 1 on the device.
readonly divisor=${GWREF10_BUDGET_DIVISOR:-1}
readonly preflight_budget=$((30 / divisor)) setup_budget=$((20 / divisor)) capture_budget=$((150 / divisor))
readonly restore_budget=$((60 / divisor)) traffic_window=$((20 / divisor))
readonly disconnect_cap=$((25 / divisor)) connect_cap=$((40 / divisor)) call_cap=$((20 / divisor))
readonly ready_cap=$((60 / divisor))
# What the stages after the connect need: the traffic window, the second teardown's whole stage (its RPC
# and gate share disconnect_cap) and a margin.
readonly tail_reserve=$(( traffic_window + disconnect_cap + 5 / divisor ))
readonly seal_budget=10 preserve_budget=20 finalize_budget=5   # short phases keep their real length

now() { local up; read -r up _ </proc/uptime; printf '%s' "${up%.*}"; }   # monotonic seconds
fail() { printf 'refused: %s\n' "$*" >&2; exit 2; }
[[ $# == 1 && $1 =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || fail 'pass the observed v10 boot ID'
readonly expected_boot=$1
start_mono=$(now)
phase_deadline=$(( start_mono + preflight_budget ))

identity_ok() {
  [[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 && "$(uname -r)" == "$expected_release" &&
     "$(cat "$boot_file")" == "$expected_boot" ]]
}
step_deadline=0   # a stage allowance inside a phase; 0 when none is active
bounded() {  # bounded <cap-seconds> <command...>: clamped to the active phase deadline and, when one is set, the
  local cap=$1 limit left; shift  # step deadline (2 s reserved for the kill-after); when nothing remains the
  limit=$phase_deadline            # command is not started and 124 is returned
  (( step_deadline > 0 && step_deadline < limit )) && limit=$step_deadline
  left=$(( limit - $(now) - 2 ))
  (( left >= 1 )) || return 124
  (( cap > left )) && cap=$left
  timeout --kill-after=2 "$cap" "$@"
}
in_phase() { (( $(now) < phase_deadline )); }

# The approved service's D-Bus object. Run 1's measured Connect was answered with
# libdbus's UnknownMethod "doesn't exist" error right after the disconnect. In the
# ConnMan source the Gemian package is built from (github.com/gemian/connman at
# a884432, whose removal-path functions are identical to vanilla 1.36), a Wi-Fi
# service object may be unregistered when wpa_supplicant removes its BSS
# (gsupplicant signal_bss_removed -> plugins/wifi.c network_removed ->
# connman_device_remove_network -> network_remove ->
# __connman_service_remove_from_network -> service_free -> service_schedule_removed)
# or when a scan ends without it (__connman_device_cleanup_networks), and is
# registered again when a scan reports the BSS. That path is the inferred
# explanation of run 1, not an observed one. Both checks are read-only (no scan
# request) and bounded by the caller's phase. They are defined before any
# state-changing path because the exit trap's restoration may need them on an
# early branch; $service is resolved later in preflight.
properties=''
service_object_present() {  # listed, and GetProperties answers with a non-empty State
  local listing
  listing=$(bounded 10 connmanctl services) || return 1
  grep -q " $service\$" <<<"$listing" || return 1
  properties=$(bounded 10 connmanctl services "$service") || return 1
  grep -Eq '^  State = [a-z]+$' <<<"$properties"
}
service_object_ready() {    # for the measured Connect only: present and exactly idle
  service_object_present && grep -q '^  State = idle$' <<<"$properties"
}

identity_ok || fail 'diagnostic boot identity changed'
for command in connmanctl ip ping timeout sha256sum python3 stat; do
  command -v "$command" >/dev/null || fail "required command missing: $command"
done
[[ -x "$iw" && -x "$wpa_cli" && -f "$check" ]] || fail 'iw, wpa_cli or cycle-check missing'
[[ ! -e "$output" ]] || fail 'output directory exists: evidence from an earlier run must be moved first'
[[ -w "$control" && "$(cat "$control")" == 0 ]] || fail 'observer control missing or not idle'
[[ "$(cut -f1 "$printk_file")" -le 7 ]] || fail 'console loglevel above 7 would mirror records'
[[ "$(cat "$carrier_file")" == 1 ]] || fail 'Wi-Fi lacks starting carrier'
[[ "$(cat "$battery/present")" == 1 && "$(cat "$battery/health")" == Good ]] || fail 'battery not present and Good'
python3 "$check" bound-files >/dev/null || fail 'bound files invalid'
target_bssid=$(python3 "$check" target-bssid) || fail 'bound target unreadable'   # a device-local query argument only
services=$(bounded 10 connmanctl services) || fail 'connmanctl services failed'
# connmanctl (client/services.c print_service, identical at the Gemian package's
# a884432) prints three independent flag characters: favourite '*' or ' ',
# AutoConnect 'A' or ' ', state 'R' ready / 'O' online / other. Discovered
# neighbour networks appear as inactive wifi services. Exactly one wifi service
# may be ready or online, judged by the state character alone with the two flag
# positions validated, so an original AutoConnect=False or non-favourite active
# service is still admitted; it must then be the approved one.
active_wifi=$(awk '/^[* ][A ][OR] / && $NF ~ /^wifi_/ {print $NF}' <<<"$services")
[[ "$(grep -c . <<<"$active_wifi")" == 1 && -n "$active_wifi" ]] || fail 'expected exactly one active wifi service'
service=$active_wifi
printf '%s' "$service" | python3 "$check" service-match >/dev/null || fail 'connected service is not the approved one'
link=$(bounded 5 "$iw" dev wlan0 link) || fail 'iw link failed'
python3 "$check" link-match <<<"$link" >/dev/null || fail 'the association is not the bound target'
# The owner-LAN gateway from unambiguous on-link routes (no `ip route get`: iproute2
# 4.9 prints this kernel's RTA_UID attribute as `via ??? ???`), rechecked after the connect.
lan_gateway() {
  { bounded 5 ip -4 route show default dev wlan0; printf -- '----\n'; bounded 5 ip -4 addr show dev wlan0; printf -- '----\n';
    bounded 5 ip -4 route show dev wlan0; } | python3 "$check" gateway-check
}
gateway=$(lan_gateway) || fail 'gateway is not an owner-LAN endpoint on wlan0'
gateway_direct() { local again; again=$(lan_gateway) && [[ "$again" == "$gateway" ]]; }
autoconnect=$(bounded 10 connmanctl services "$service" | awk '/^  AutoConnect = / {print $3; exit}')
[[ "$autoconnect" == True || "$autoconnect" == False ]] || fail 'cannot read AutoConnect'
in_phase || fail 'preflight budget exhausted'

# From here on, state changes; the trap is installed before any of them.
mkdir "$output" || fail 'cannot create the output directory'
chmod 700 "$output"
exec >>"$output/run.log" 2>&1
receipt() { printf '%s\n' "$*" >>"$output/receipt.txt"; printf '%s\n' "$*"; }
ops_connect=0 ops_disconnect=0 ops_restore=0 ops_link_queries=0 ops_ping=0 ops_observer_writes=0 ops_autoconnect_writes=0 ops_bss_queries=0
logger_pid=
armed=no sealed=no seal_captured=0 identity_lost=0 frozen=0 restored=0 autoconnect_ok=0 logger_stopped=0 logger_rc=none
step=start
receipt "start=$(date -u +%FT%TZ) boot=$expected_boot release=$expected_release autoconnect_original=$autoconnect target_match_before=1 service_match=1"

finish() {
  local rc=$?
  trap - EXIT TERM INT
  step_finish "$rc"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

gate() {  # gate <action>: live identity before an observer write or a radio call; a loss stops all actions
  if [[ "$identity_lost" == 1 ]]; then return 1; fi
  if identity_ok; then return 0; fi
  identity_lost=1
  receipt "identity_lost_at=$1"
  return 1
}
link_query() { ops_link_queries=$((ops_link_queries + 1)); link=$(bounded 5 "$iw" dev wlan0 link) || link=''; }
disconnected_now() { link_query; [[ "$link" == 'Not connected.' ]]; }
connected_now() { link_query; grep -Fq 'Connected to' <<<"$link"; }
on_target_now() { python3 "$check" link-match <<<"$link" >/dev/null; }
has_address() { bounded 5 ip -4 addr show dev wlan0 | grep -q 'inet '; }

seal() {
  [[ "$sealed" == no ]] || return 0
  sealed=yes
  phase_deadline=$(( $(now) + seal_budget ))   # 10 s: control 3 s, logger stop 3 s, parser the rest
  local state=unwritten stage_deadline
  if [[ "$armed" == yes ]] && gate seal; then
    ops_observer_writes=$((ops_observer_writes + 1))
    printf 2 >"$control" || true
    stage_deadline=$(( $(now) + 3 ))
    while (( $(now) < stage_deadline )) && in_phase; do
      state=$(cat "$control" 2>/dev/null || echo unreadable)
      [[ "$state" == 2 ]] && break
      sleep "$tick"
    done
    state=$(cat "$control" 2>/dev/null || echo unreadable)
  fi
  receipt "seal_state=$state"
  logger_stopped=0 logger_rc=none
  if [[ -n "$logger_pid" ]]; then
    sleep "$tick"
    kill -TERM "$logger_pid" 2>/dev/null || true
    stage_deadline=$(( $(now) + 3 ))
    while kill -0 "$logger_pid" 2>/dev/null && (( $(now) < stage_deadline )) && in_phase; do sleep "$tick"; done
    if kill -0 "$logger_pid" 2>/dev/null; then kill -KILL "$logger_pid" 2>/dev/null || true; else logger_stopped=1; fi
    wait "$logger_pid" && logger_rc=0 || logger_rc=$?
    [[ "$logger_rc" == 0 ]] || logger_stopped=0
    logger_pid=
  fi
  receipt "logger_stopped=$logger_stopped logger_rc=$logger_rc logger_report=$(tr '\n' ' ' <"$output/logger.txt" 2>/dev/null | sed 's/ *$//' || echo none)"
  if [[ "$armed" == yes ]]; then
    local summary
    if summary=$(bounded 5 python3 "$check" seal-check "$output/kmsg-cycle.log" 2>&1); then seal_captured=1; else seal_captured=0; fi
    receipt "$(tr '\n' ' ' <<<"$summary" | sed 's/ *$//')"
    grep -q 'capped=0' "$output/logger.txt" 2>/dev/null || seal_captured=0
    [[ "$logger_stopped" == 1 ]] || seal_captured=0
    receipt "seal_captured=$seal_captured"
  fi
}

freeze() {  # verified manifest of the closed capture files, then read-only; failures are recorded, not hidden
  [[ "$frozen" == 0 && "$sealed" == yes ]] || return 0
  phase_deadline=$(( $(now) + preserve_budget ))
  bounded 10 dmesg >"$output/dmesg-after.log" || receipt 'snapshot_dmesg_after=0'
  cat "$control" >"$output/control-after.txt" 2>/dev/null || receipt 'snapshot_control_after=0'
  cat "$printk_file" >"$output/printk-after.txt" 2>/dev/null || receipt 'snapshot_printk_after=0'
  bounded 5 ip -4 addr show dev wlan0 >"$output/addr-after.txt" || receipt 'snapshot_addr_after=0'
  { bounded 10 connmanctl services "$service" 2>/dev/null || true; } |
    grep -E '^  (State|AutoConnect|Favorite|Type|Security|Strength) = ' >"$output/service-after.txt" || receipt 'snapshot_service_after=0'
  local identity=0; identity_ok && identity=1
  receipt "identity_post_seal=$identity"
  [[ "$identity" == 1 ]] || identity_lost=1
  local -a required=(kmsg-cycle.log dmesg-before.log dmesg-after.log addr-before.txt addr-after.txt route-before.txt
                     services-before.txt service-before.txt service-after.txt printk-before.txt printk-after.txt
                     control-after.txt logger.txt)
  local -a optional=(ping.txt traffic-window connect-output.txt bss-timeline.txt bss-snapshots.txt)
  local missing='' name sum complete=1
  : >"$output/MANIFEST"
  for name in "${required[@]}" "${optional[@]}"; do
    if [[ -f "$output/$name" ]] && sum=$(cd "$output" && sha256sum -- "$name"); then
      printf '%s %s\n' "$(stat -c %s "$output/$name")" "$sum" >>"$output/MANIFEST"
    elif [[ " ${required[*]} " == *" $name "* ]]; then
      complete=0; missing="$missing $name"
    fi
  done
  frozen=$complete
  receipt "manifest_complete=$complete manifest_missing=${missing:- none} frozen=$frozen"
  for name in MANIFEST "${required[@]}" "${optional[@]}"; do
    [[ -f "$output/$name" ]] && { chmod 0400 "$output/$name" || receipt "chmod_failed=$name"; }
  done
  receipt "ops_link_queries=$ops_link_queries ops_connect=$ops_connect ops_disconnect=$ops_disconnect ops_ping=$ops_ping ops_observer_writes=$ops_observer_writes ops_autoconnect_writes=$ops_autoconnect_writes ops_bss_queries=$ops_bss_queries"
}

restore() {  # one manual restoration connect outside the capture; AutoConnect restored only after verification
  phase_deadline=$(( $(now) + restore_budget ))
  exec >>"$output/restore.log" 2>&1
  if ! gate restore; then receipt 'restore_skipped=identity'; receipt 'autoconnect_left_off=1'; receipt "restore_connected=0 ops_restore=$ops_restore"; return 0; fi
  # The object may be unregistered again after the second disconnect; the restoration
  # waits only for its presence (any state: an association still online on an early
  # exit is already what restoration wants), within the restoration budget, then keeps
  # its original contract: one connect call, verification on the bound target, the
  # AutoConnect readback.
  local object_wait_start; object_wait_start=$(now)
  while ! service_object_present && in_phase; do sleep "$tick"; done
  if ! service_object_present; then
    receipt "restore_object_present=0 restore_object_wait_s=$(( $(now) - object_wait_start ))"
    receipt 'autoconnect_left_off=1'; receipt "restore_connected=0 ops_restore=$ops_restore"; return 0
  fi
  receipt "restore_object_present=1 restore_object_wait_s=$(( $(now) - object_wait_start ))"
  gate restore-connect || { receipt 'restore_skipped=identity'; receipt 'autoconnect_left_off=1'; receipt "restore_connected=0 ops_restore=$ops_restore"; return 0; }
  ops_restore=$((ops_restore + 1))
  bounded "$((30 / divisor))" connmanctl connect "$service" || true
  while in_phase; do
    if connected_now && has_address; then
      if on_target_now && gateway_direct && identity_ok; then restored=1; fi
      break
    fi
    sleep "$tick"
  done
  local property
  if [[ "$restored" == 1 ]]; then
    if [[ "$autoconnect" == True ]]; then
      ops_autoconnect_writes=$((ops_autoconnect_writes + 1))
      bounded 10 connmanctl config "$service" --autoconnect yes || true
    fi
    property=$(bounded 10 connmanctl services "$service" | awk '/^  AutoConnect = / {print $3; exit}' || echo unread)
    [[ "$property" == "$autoconnect" ]] && autoconnect_ok=1
    receipt "autoconnect_after=$property autoconnect_restored=$autoconnect_ok"
  else
    receipt 'autoconnect_left_off=1'
  fi
  receipt "restore_connected=$restored ops_restore=$ops_restore"
}

step_finish() {
  local rc=$1
  step_deadline=0   # a stage allowance active at an interruption or error must not bound the cleanup phases
  receipt "exit_step=$step rc_before_finish=$rc"
  seal
  freeze
  restore
  if [[ "$rc" == 0 && "$seal_captured" != 1 ]]; then rc=6; fi
  if [[ "$identity_lost" == 1 ]]; then rc=7; fi
  if [[ "$rc" == 0 && ( "$restored" != 1 || "$autoconnect_ok" != 1 || "$frozen" != 1 ) ]]; then rc=3; fi
  local result=partial; [[ "$rc" == 0 ]] && result=complete
  receipt "result=$result exit=$rc elapsed_s=$(( $(now) - start_mono ))"
  phase_deadline=$(( $(now) + finalize_budget ))
  exec >/dev/null 2>&1
  (cd "$output" && bounded 3 sha256sum -- run.log restore.log receipt.txt >SHA256SUMS.final) || true
  exit "$rc"
}

# ---- setup ----
phase_deadline=$(( $(now) + setup_budget ))
step='snapshots'
bounded 10 dmesg >"$output/dmesg-before.log"
bounded 5 ip -4 addr show dev wlan0 >"$output/addr-before.txt"
bounded 5 ip route >"$output/route-before.txt"
printf '%s\n' "$services" >"$output/services-before.txt"
{ bounded 10 connmanctl services "$service" || true; } | grep -E '^  (State|AutoConnect|Favorite|Type|Security|Strength) = ' >"$output/service-before.txt"
cat "$printk_file" >"$output/printk-before.txt"

step='logger'
python3 "$check" kmsg-stream "$kmsg_source" "$output/kmsg-cycle.log" "$kmsg_bound" >"$output/logger.txt" &
logger_pid=$!
sleep "$tick"
kill -0 "$logger_pid" 2>/dev/null || { receipt 'logger_started=0'; exit 5; }
receipt 'logger_started=1'

step='autoconnect-off'
gate autoconnect-off || exit 7
ops_autoconnect_writes=$((ops_autoconnect_writes + 1))
bounded 10 connmanctl config "$service" --autoconnect no || { receipt 'autoconnect_off=0'; exit 5; }
receipt 'autoconnect_off=1'

# ---- capture ----
step='arm'
gate arm || exit 7
ops_observer_writes=$((ops_observer_writes + 1))
printf 1 >"$control"
armed=yes
arm_mono=$(now)
phase_deadline=$(( arm_mono + capture_budget ))
since_arm() { printf '%s' "$(( $(now) - arm_mono ))"; }
arm_seq=
for _ in 1 2 3 4 5; do
  arm_seq=$(grep -m1 'gwref10 arm: ' "$output/kmsg-cycle.log" 2>/dev/null | cut -d, -f2) && [[ -n "$arm_seq" ]] && break
  sleep "$tick"
done
[[ "$arm_seq" =~ ^[0-9]+$ ]] || { receipt 'arm_line=0'; exit 5; }
receipt "arm_line=1 arm_seq=$arm_seq"

step='positive-control'
# Two read-only link queries one second apart: iw link reaches get_station and
# wlanoidQueryRssi, whose 500 ms cache expires before the second query, which
# sends CMD 0x81; the firmware answers with EVENT 0x02 carrying the same seq.
gate positive-control || exit 7
link_query; sleep "$tick"; link_query
pc=0
for _ in 1 2 3 4 5; do
  python3 "$check" positive-control "$output/kmsg-cycle.log" "$arm_seq" >/dev/null && pc=1 && break
  sleep "$tick"
done
receipt "positive_control=$pc"
[[ "$pc" == 1 ]] || exit 2

wait_by() {  # wait_by <predicate> <absolute-deadline>: every call inside the predicate is clamped to the deadline,
  local ok=1  # and a true predicate counts only when the deadline has not passed by the time it returns
  step_deadline=$2
  while (( $(now) < $2 )); do
    if "$1"; then (( $(now) <= $2 )) && ok=0; break; fi
    sleep "$tick"
  done
  step_deadline=0
  return "$ok"
}
budget_left() { in_phase || { receipt "budget_exhausted_at=$step"; exit 4; }; }
allowance() {  # allowance <cap> <reserve-for-later-stages>: seconds grantable now, or a refusal (exit 4)
  local left=$(( phase_deadline - $(now) - $2 ))
  if (( left < 1 )); then receipt "budget_refused_at=$step remaining_s=$(( phase_deadline - $(now) )) reserve_s=$2"; exit 4; fi
  (( left < $1 )) && printf '%s' "$left" || printf '%s' "$1"
}
three_disconnected() {
  local i
  for i in 1 2 3; do disconnected_now || return 1; [[ $i == 3 ]] || sleep "$tick"; done
}
connected_on_target() { connected_now && has_address && on_target_now; }

step='disconnect-1'
budget_left
gate disconnect-1 || exit 7
ops_disconnect=$((ops_disconnect + 1))
teardown_deadline=$(( $(now) + disconnect_cap )); step_deadline=$teardown_deadline   # RPC and gate share the stage
bounded "$call_cap" connmanctl disconnect "$service" || true
wait_by three_disconnected "$teardown_deadline" || { receipt 'teardown1=0'; exit 5; }
receipt 'teardown1=1'

# ---- readiness: the approved object idle and the target BSS fresh in wpa_supplicant's table ----
# Observed: run 1's measured connect met an unregistered service object; run 2's met
# an idle object and was answered Operation aborted at an unrecorded time, with the
# BSS state unmeasured; both restorations, issued later, associated within seconds.
# Hypothesis, not observation: the target BSS was missing from wpa_supplicant's table
# for a while after the teardown. This gate measures that state instead of assuming
# it. It is read-only (`wpa_cli -i wlan0 bss <target>` and ConnMan property reads, no
# scan request) and numeric: query rc 0, listed, bssid and freq equal the bound
# target, unsigned age at most $bss_fresh_limit s. Raw query outputs stay in the
# private bss-snapshots.txt (bounded); bss-timeline.txt carries only offsets, return
# codes, booleans and ages.
step='readiness'
budget_left
bss_checks=0 bss_visible_checks=0 bss_match_checks=0 bss_fresh_age=none object_idle=0 object_idle_checks=0 bss_fresh=0 bss_snapshots=0
readiness_probe() {  # one timeline line per probe; true when both conditions hold at this probe
  local raw rc=0 verdict vrc=0 age
  object_idle=0; service_object_ready && { object_idle=1; object_idle_checks=$((object_idle_checks + 1)); }
  ops_bss_queries=$((ops_bss_queries + 1)); bss_checks=$((bss_checks + 1))
  raw=$(bounded 5 "$wpa_cli" -i wlan0 bss "$target_bssid" 2>&1) || rc=$?
  if (( bss_snapshots < bss_snapshot_limit )); then
    bss_snapshots=$((bss_snapshots + 1))
    printf 't=%s rc=%s\n%s\n----\n' "$(since_arm)" "$rc" "$raw" >>"$output/bss-snapshots.txt"
  fi
  verdict=$(python3 "$check" bss-fresh "$bss_fresh_limit" <<<"$raw") || vrc=$?
  [[ "$verdict" == bss_visible=* ]] || { verdict='bss_visible=0 bss_match=0 bss_age=none bss_fresh=0'; vrc=2; }
  printf 't=%s object_idle=%s query_rc=%s verdict_rc=%s %s\n' "$(since_arm)" "$object_idle" "$rc" "$vrc" "$verdict" >>"$output/bss-timeline.txt"
  [[ "$verdict" == *' bss_visible=1'* || "$verdict" == 'bss_visible=1'* ]] && bss_visible_checks=$((bss_visible_checks + 1))
  [[ "$verdict" == *'bss_match=1'* ]] && bss_match_checks=$((bss_match_checks + 1))
  bss_fresh=0
  if [[ "$rc" == 0 && "$vrc" == 0 ]]; then   # a query that did not succeed never admits, whatever it printed
    bss_fresh=1
    age=${verdict##*bss_age=}; bss_fresh_age=${age%% *}
  fi
  [[ "$object_idle" == 1 && "$bss_fresh" == 1 ]]
}
ready_allow=$(allowance "$ready_cap" $(( connect_cap + tail_reserve )))
ready_start=$(now)
if ! wait_by readiness_probe $(( ready_start + ready_allow )); then
  receipt "readiness=0 readiness_wait_s=$(( $(now) - ready_start )) readiness_allow_s=$ready_allow object_idle_last=$object_idle bss_fresh_last=$bss_fresh bss_checks=$bss_checks object_idle_checks=$object_idle_checks bss_visible_checks=$bss_visible_checks bss_match_checks=$bss_match_checks"
  exit 5
fi
receipt "readiness=1 readiness_wait_s=$(( $(now) - ready_start )) readiness_allow_s=$ready_allow bss_checks=$bss_checks object_idle_checks=$object_idle_checks bss_visible_checks=$bss_visible_checks bss_match_checks=$bss_match_checks bss_fresh_age_s=$bss_fresh_age"

# ---- the single measured connect: the RPC and the connected wait share one allowance ----
step='connect'
budget_left
connect_allow=$(allowance "$connect_cap" "$tail_reserve")
gate connect || exit 7   # live identity immediately before the radio call, after the wait
ops_connect=$((ops_connect + 1))
connect_deadline=$(( $(now) + connect_allow )); step_deadline=$connect_deadline
connect_rpc_start=$(since_arm); connect_rc=0
connect_output=$(bounded "$connect_allow" connmanctl connect "$service" 2>&1) || connect_rc=$?
connect_rpc_end=$(since_arm); step_deadline=0
printf '%s\n' "$connect_output" >"$output/connect-output.txt"
# The reply is classified by text class only; the text itself stays in the private file. No retry on any class.
if grep -q "doesn't exist" <<<"$connect_output"; then connect_reply=unknown_method
elif grep -q 'Operation aborted' <<<"$connect_output"; then connect_reply=aborted
elif [[ "$connect_rc" == 124 || "$connect_rc" == 137 ]]; then connect_reply=timeout
elif [[ "$connect_rc" != 0 ]]; then connect_reply=error
else connect_reply=ok; fi
receipt "connect_rpc_start_s=$connect_rpc_start connect_rpc_end_s=$connect_rpc_end connect_rpc_elapsed_s=$(( connect_rpc_end - connect_rpc_start )) connect_rpc_rc=$connect_rc connect_reply=$connect_reply connect_allow_s=$connect_allow"
[[ "$connect_reply" == unknown_method ]] && receipt 'connect_unknown_method=1'
[[ "$connect_reply" == aborted ]] && receipt 'connect_aborted=1'
[[ "$connect_reply" == ok ]] || exit 5
if ! wait_by connected_on_target "$connect_deadline"; then
  if connected_now; then receipt 'connect=1 target_match=0'; else receipt 'connect=0'; fi
  exit 5
fi
receipt "connect=1 target_match=1 connected_at_s=$(since_arm)"
gateway_direct || { receipt 'gateway_recheck=0'; exit 5; }
receipt 'gateway_recheck=1'

step='traffic'
budget_left
remaining=$(( phase_deadline - $(now) ))
if (( remaining < tail_reserve )); then receipt "traffic_window_refused=1 remaining_s=$remaining needed_s=$tail_reserve"; exit 4; fi
window_start=$(date +%s)
window_end=$(( window_start + traffic_window ))
printf '%s %s %s\n' "$window_start" "$window_end" "$expected_boot" >"$output/traffic-window"
receipt "traffic_window_start=$window_start traffic_window_end=$window_end"
ops_ping=$((ops_ping + 1))
bounded 15 ping -c 5 -W 2 "$gateway" >"$output/ping.txt" || true
while (( $(date +%s) < window_end )) && in_phase; do sleep "$tick"; done

step='disconnect-2'
budget_left
gate disconnect-2 || exit 7
ops_disconnect=$((ops_disconnect + 1))
teardown_deadline=$(( $(now) + disconnect_cap )); step_deadline=$teardown_deadline   # RPC and gate share the stage
bounded "$call_cap" connmanctl disconnect "$service" || true
wait_by three_disconnected "$teardown_deadline" || { receipt 'teardown2=0'; exit 5; }
receipt 'teardown2=1'

step='seal'
seal
[[ "$seal_captured" == 1 ]] || exit 6
receipt 'cycle=complete'
exit 0
