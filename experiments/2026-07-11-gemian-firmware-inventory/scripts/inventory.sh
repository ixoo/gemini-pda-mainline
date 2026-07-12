#!/usr/bin/env bash

# Read-only inventory of Gemian's system-partition firmware directories.

set -u
export LC_ALL=C

readonly ROOTS=(
  /system/etc/firmware
  /system/vendor/firmware
)

printf 'path|bytes|sha256\n'
for root in "${ROOTS[@]}"; do
  [[ -d "${root}" ]] || continue
  find "${root}" -xdev -type f -print0 2>/dev/null
done | sort -z -u | while IFS= read -r -d '' path; do
  bytes="$(stat -c '%s' "${path}" 2>/dev/null || printf unavailable)"
  digest="$(sha256sum "${path}" 2>/dev/null | awk '{print $1}')"
  printf '%s|%s|%s\n' "${path}" "${bytes}" "${digest:-unavailable}"
done

printf '\nobserved firmware-related boot messages (sanitized)\n'
dmesg 2>/dev/null \
  | grep -Ei 'firmware|request_firmware|load.*(bin|rom|patch|fw)' \
  | grep -Eiv 'imei|serial(number|no)?|mac address|key|credential' \
  | head -n 500 || true

