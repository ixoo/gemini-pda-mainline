#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# One bounded Gemian last-client cycle with VCN28 PMIC readbacks.
set -euo pipefail
export LC_ALL=C
umask 077

readonly expected_release=3.18.41-gemini-wifi-ref8+
readonly output=/var/tmp/gemini-wifi-reference-vcn28-cycle-v8
readonly pmic=/sys/devices/platform/mt-pmic/pmic_access
readonly wifi_device=/dev/wmtWifi

fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# == 1 && $1 =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] ||
  fail 'pass the observed boot ID'
readonly expected_boot=$1
[[ $(id -u) == 0 && $(uname -m) == aarch64 &&
   $(uname -r) == "$expected_release" &&
   $(cat /proc/sys/kernel/random/boot_id) == "$expected_boot" ]] ||
  fail 'diagnostic boot identity changed'
for command in timeout connmanctl iw hciconfig hcitool; do
  command -v "$command" >/dev/null || fail "required command missing: $command"
done
[[ -r $pmic && -w $pmic && $(cat /sys/class/net/wlan0/carrier) == 1 ]] ||
  fail 'PMIC access or starting Wi-Fi unavailable'
[[ -d /sys/class/bluetooth/hci0 ]] || fail 'Bluetooth controller missing'
hciconfig hci0 | grep -Fq 'UP RUNNING' || fail 'Bluetooth is not up'
[[ $(timeout 3 hcitool con | wc -l) == 1 ]] || fail 'Bluetooth connection present'
[[ -c $wifi_device && $(stat -c '%t:%T' "$wifi_device") == 99:0 ]] ||
  fail 'WMT Wi-Fi control node changed'
[[ $(cat /sys/class/power_supply/battery/present) == 1 &&
   $(cat /sys/class/power_supply/battery/health) == Good ]] ||
  fail 'battery gate failed'
capacity=$(cat /sys/class/power_supply/battery/capacity)
[[ $capacity =~ ^[0-9]+$ ]] || fail 'battery capacity malformed'
(( capacity >= 40 )) || fail 'battery capacity too low'
[[ ! -e $output && ! -L $output ]] || fail 'single-use output already exists'
mkdir -m 0700 "$output"
exec >"$output/control.log" 2>&1

connman_disabled=no
connman_enable_calls=0
bt_down_attempted=no
bt_up_attempts=0
wmt_off_attempted=no
wmt_on_attempts=0
cleanup() {
  local status=$?
  trap - EXIT
  set +e
  if [[ $wmt_off_attempted == yes && $wmt_on_attempts == 0 ]]; then
    wmt_on_attempts=1
    timeout 15 bash -c 'printf 1 > /dev/wmtWifi'
  fi
  if [[ $bt_down_attempted == yes && $bt_up_attempts == 0 ]]; then
    bt_up_attempts=1
    timeout 15 hciconfig hci0 up
  fi
  if [[ $connman_disabled == yes && $connman_enable_calls == 0 ]]; then
    connman_enable_calls=1
    timeout 15 connmanctl enable wifi
  fi
  {
    printf 'boot_id=%s\nrelease=%s\nexit_code=%s\n' \
      "$(cat /proc/sys/kernel/random/boot_id)" "$(uname -r)" "$status"
    printf 'wmt_off_attempted=%s\nwmt_on_attempts=%s\n' \
      "$wmt_off_attempted" "$wmt_on_attempts"
    printf 'bt_down_attempted=%s\nbt_up_attempts=%s\n' \
      "$bt_down_attempted" "$bt_up_attempts"
    printf 'connman_disabled=%s\nconnman_enable_calls=%s\n' \
      "$connman_disabled" "$connman_enable_calls"
    printf 'carrier=%s\n' "$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo unavailable)"
    printf 'bluetooth_up=%s\n' "$(hciconfig hci0 2>/dev/null | grep -Fc 'UP RUNNING')"
  } >"$output/result.txt"
  exit "$status"
}
trap cleanup EXIT
trap 'exit 143' TERM

sample() {
  local label=$1 expected_bit=$2 value status
  # The exact three-byte input takes this vendor sysfs store's read branch;
  # adding a value or a sixth byte would take its PMIC write branch.
  if timeout 3 bash -c 'printf a0c > /sys/devices/platform/mt-pmic/pmic_access'; then
    status=0
    value=$(timeout 3 cat "$pmic") || status=$?
  else
    status=$?
    value=unavailable
  fi
  [[ $status == 0 && $value =~ ^[0-9]+$ && $value -le 65535 ]] ||
    fail "VCN28 read failed at $label"
  printf '%s status=%s value=0x%04x mode_bit=%u source_mode=%u source_enable=%u\n' \
    "$label" "$status" "$value" "$(( (value >> 3) & 1 ))" \
    "$(( (value >> 5) & 7 ))" "$(( (value >> 11) & 7 ))" >>"$output/vcn28.txt"
  (( ((value >> 3) & 1) == expected_bit )) ||
    fail "VCN28 mode did not reach expected value at $label"
}

sample before 1
connman_disabled=yes
timeout 15 connmanctl disable wifi
disconnected_samples=0
for _ in {1..25}; do
  if [[ $(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo 0) == 0 ]] &&
     iw dev wlan0 link | grep -Fxq 'Not connected.'; then
    (( disconnected_samples += 1 ))
  else
    disconnected_samples=0
  fi
  (( disconnected_samples >= 3 )) && break
  sleep 1
done
(( disconnected_samples >= 3 )) || fail 'association did not clear'

bt_down_attempted=yes
timeout 15 hciconfig hci0 down
for _ in {1..10}; do
  hciconfig hci0 | grep -Fq 'DOWN' && break
  sleep 1
done
hciconfig hci0 | grep -Fq 'DOWN' || fail 'Bluetooth did not stay down'

wmt_off_attempted=yes
timeout 15 bash -c 'printf 0 > /dev/wmtWifi'
for _ in {1..20}; do
  [[ ! -e /sys/class/net/wlan0 ]] && break
  sleep 1
done
[[ ! -e /sys/class/net/wlan0 ]] || fail 'WLAN netdev remained after WMT off'
sample after_off 0

wmt_on_attempts=1
timeout 15 bash -c 'printf 1 > /dev/wmtWifi'
for _ in {1..30}; do
  [[ -e /sys/class/net/wlan0 ]] && break
  sleep 1
done
[[ -e /sys/class/net/wlan0 ]] || fail 'WLAN netdev did not return'
sample after_on 1

bt_up_attempts=1
timeout 15 hciconfig hci0 up
for _ in {1..20}; do
  hciconfig hci0 | grep -Fq 'UP RUNNING' && break
  sleep 1
done
hciconfig hci0 | grep -Fq 'UP RUNNING' || fail 'Bluetooth did not return'

connman_enable_calls=1
timeout 15 connmanctl enable wifi
for _ in {1..90}; do
  [[ $(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo 0) == 1 ]] && break
  sleep 1
done
[[ $(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo 0) == 1 ]] ||
  fail 'Wi-Fi carrier did not return'
sample restored 1
