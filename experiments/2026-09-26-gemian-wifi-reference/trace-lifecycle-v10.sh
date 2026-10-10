#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# One bounded v10 lifecycle capture: disconnect, connect, target-only traffic,
# disconnect, under the gwref10 observer; then an outside-capture restoration.
# Run by the device custodian as root on the verified v10 boot, boot ID as the
# only argument, under systemd-run so it survives losing the LAN. Single use.
set -euo pipefail
export LC_ALL=C
umask 077

readonly expected_release=3.18.41-gemini-wifi-ref10+
readonly output=/var/tmp/gemini-wifi-reference-lifecycle-v10
readonly control=/sys/module/wlan_gen3/parameters/gwref10
readonly approved=/root/.gemini-wifi-reference/approved-service   # private, mode 0600: one ConnMan service name
readonly target=/root/.gemini-wifi-reference/ap-target.json        # private, mode 0600: ssid, bssid, frequency_mhz, channel
readonly iw=/sbin/iw
readonly kmsg_bound=8388608
readonly deadline_s=180

fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# == 1 && $1 =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] ||
  fail 'pass the observed v10 boot ID'
readonly expected_boot=$1
[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 &&
   "$(uname -r)" == "$expected_release" &&
   "$(cat /proc/sys/kernel/random/boot_id)" == "$expected_boot" ]] ||
  fail 'diagnostic boot identity changed'
for command in connmanctl ip ping timeout systemd-run sha256sum head cat date; do
  command -v "$command" >/dev/null || fail "required command missing: $command"
done
[[ -x "$iw" ]] || fail 'iw missing'
[[ -e "$output/consumed" ]] && fail 'single-use budget already consumed on this boot'
[[ -w "$control" && "$(cat "$control")" == 0 ]] || fail 'observer control missing or not idle'
[[ -r /dev/kmsg ]] || fail 'kmsg not readable'
[[ "$(cut -f1 /proc/sys/kernel/printk)" -le 7 ]] || fail 'console loglevel above 7 would mirror records'
[[ "$(cat /sys/class/net/wlan0/carrier)" == 1 ]] || fail 'Wi-Fi lacks starting carrier'
"$iw" dev wlan0 link | grep -Fq 'Connected to' || fail 'iw does not report a connection'
gateway=$(ip -4 route show default dev wlan0 | awk '/^default/ {print $3; exit}')
[[ -n "$gateway" ]] || fail 'no IPv4 default route on wlan0'
[[ "$(cat /sys/class/power_supply/battery/present)" == 1 &&
   "$(cat /sys/class/power_supply/battery/health)" == Good ]] || fail 'battery not present and Good'
[[ -f "$approved" && "$(stat -c %a "$approved")" == 600 ]] || fail 'approved-service file missing or not 0600'
[[ -f "$target" && "$(stat -c %a "$target")" == 600 ]] || fail 'ap-target file missing or not 0600'
# The bound target (the same file the mainline runs are bound to) is compared
# with iw's report before and after each association; only booleans are exported.
target_field() { sed -n 's/.*"'"$1"'"[[:space:]]*:[[:space:]]*"\{0,1\}\([^",}]*\)"\{0,1\}.*/\1/p' "$target" | head -n 1; }
target_ssid=$(target_field ssid); target_bssid=$(target_field bssid); target_freq=$(target_field frequency_mhz)
[[ -n "$target_ssid" && "$target_bssid" =~ ^[0-9a-f]{2}(:[0-9a-f]{2}){5}$ && "$target_freq" =~ ^[0-9]{4}$ ]] ||
  fail 'ap-target fields unreadable'
on_target() {
  local link
  link=$("$iw" dev wlan0 link) || return 1
  grep -Fxq "Connected to $target_bssid (on wlan0)" <<<"$link" &&
    grep -Fxq "	SSID: $target_ssid" <<<"$link" &&
    grep -Fxq "	freq: $target_freq" <<<"$link"
}
on_target || fail 'the current association is not the bound target'
service=$(connmanctl services | awk '/^\*A[OR]/ {print $NF; exit}')
[[ -n "$service" && "$service" == "$(cat "$approved")" ]] || fail 'connected service is not the approved one'
autoconnect=$(connmanctl services "$service" | awk '/AutoConnect/ {print $NF; exit}')
[[ "$autoconnect" == True || "$autoconnect" == False ]] || fail 'cannot read AutoConnect'

mkdir -p "$output"
: >"$output/consumed"
exec >>"$output/run.log" 2>&1
printf 'start=%s boot=%s release=%s autoconnect=%s target_match_before=1\n' "$(date -u +%FT%TZ)" "$expected_boot" "$expected_release" "$autoconnect"
dmesg >"$output/dmesg-before.log"
ip -4 addr show dev wlan0 >"$output/addr-before.txt"
ip route >"$output/route-before.txt"
connmanctl services >"$output/services-before.txt"
connmanctl services "$service" >"$output/service-before.txt"
cat /proc/sys/kernel/printk >"$output/printk.txt"

# The kmsg stream runs from before arm to after seal, bounded in bytes; the
# 128 KiB kernel ring is therefore irrelevant to completeness.
head -c "$kmsg_bound" /dev/kmsg >"$output/kmsg-cycle.log" &
kmsg_pid=$!
sleep 1

disconnected() {
  local i
  for i in 1 2 3; do
    "$iw" dev wlan0 link | grep -Fxq 'Not connected.' || return 1
    [[ $i == 3 ]] || sleep 1
  done
}
wait_disconnected() {
  for _ in $(seq 1 20); do disconnected && return 0; sleep 1; done
  return 1
}
wait_connected() {
  for _ in $(seq 1 40); do
    if "$iw" dev wlan0 link | grep -Fq 'Connected to' && ip -4 addr show dev wlan0 | grep -q 'inet '; then
      if on_target; then printf 'target_match=1\n'; return 0; fi
      printf 'target_match=0\n'
      return 1
    fi
    sleep 1
  done
  return 1
}
step() { printf 'step=%s t=%s\n' "$1" "$(date -u +%T)"; }

sealed=no
seal() {
  if [[ "$sealed" == no ]]; then
    sealed=yes
    echo 2 >"$control" || true
    sleep 1
    kill "$kmsg_pid" 2>/dev/null || true
    wait "$kmsg_pid" 2>/dev/null || true
  fi
}
restore() {
  seal
  dmesg >"$output/dmesg-after.log"
  cat "$control" >"$output/control-after.txt" || true
  connmanctl services >"$output/services-after.txt" || true
  connmanctl services "$service" >"$output/service-after.txt" || true
  ip -4 addr show dev wlan0 >"$output/addr-after.txt" || true
  connmanctl config "$service" --autoconnect "$( [[ "$autoconnect" == True ]] && echo yes || echo no )" || true
  (cd "$output" && sha256sum -- * >SHA256SUMS) || true
  # Restoration connect, outside the capture; the full private outputs are already saved.
  if ! disconnected && "$iw" dev wlan0 link | grep -Fq 'Connected to'; then
    printf 'restore=already-connected\n'
  else
    timeout 60 connmanctl connect "$service" || true
    if wait_connected; then printf 'restore=connected\n'; else printf 'restore=FAILED\n'; exit 3; fi
  fi
}
trap restore EXIT

connmanctl config "$service" --autoconnect no
step arm
echo 1 >"$control"
# Positive control: two read-only link queries one second apart. The driver
# caches link quality for 500 ms, so the second query sends CMD 0x81 and the
# firmware answers with event 0x02 carrying the same sequence number.
"$iw" dev wlan0 link >/dev/null
sleep 1
"$iw" dev wlan0 link >/dev/null
sleep 2
if ! grep -q 'gwref10 arm:' "$output/kmsg-cycle.log"; then printf 'positive_control=no-arm-line\n'; exit 2; fi
if ! grep -q 'gwref10 cmd: n=[0-9]* cid=0x81 ' "$output/kmsg-cycle.log"; then printf 'positive_control=no-link-quality-command\n'; exit 2; fi
if ! grep -q 'gwref10 event: n=[0-9]* eid=0x02 ' "$output/kmsg-cycle.log"; then printf 'positive_control=no-link-quality-event\n'; exit 2; fi
printf 'positive_control=pass\n'

start_s=$SECONDS
budget() { (( SECONDS - start_s < deadline_s )) || { printf 'budget=exhausted at step %s\n' "$1"; exit 4; }; }

step disconnect-1
budget disconnect-1
timeout 20 connmanctl disconnect "$service" || true
wait_disconnected || { printf 'teardown1=not-disconnected\n'; exit 5; }
step connect
budget connect
timeout 45 connmanctl connect "$service" || true
wait_connected || { printf 'connect=failed-or-off-target\n'; exit 5; }
step traffic
budget traffic
timeout 15 ping -c 5 -W 2 "$gateway" >"$output/ping.txt" || true
step disconnect-2
budget disconnect-2
timeout 20 connmanctl disconnect "$service" || true
wait_disconnected || { printf 'teardown2=not-disconnected\n'; exit 5; }
step seal
seal
printf 'cycle=complete\n'
