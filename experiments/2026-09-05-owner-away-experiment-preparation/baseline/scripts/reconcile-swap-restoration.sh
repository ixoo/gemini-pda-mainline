#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Read-only proposal following an unclassified restoration return.
set -euo pipefail
export LC_ALL=C
[[ $(id -u) == 0 && $(uname -r) == 3.18.41+ && $(uname -m) == aarch64 ]]
[[ ${EXPECTED_BOOT_ID:-} =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]]
[[ $(cat /proc/sys/kernel/random/boot_id) == "$EXPECTED_BOOT_ID" ]]
printf 'swap_restoration_reconciliation=begin\n'
printf 'self_mount_namespace=%s\ninit_mount_namespace=%s\n' "$(readlink /proc/self/ns/mnt)" "$(readlink /proc/1/ns/mnt)"
[[ $(wc -l < /proc/swaps) -le 5 ]]
cat /proc/swaps
awk '$1=="MemAvailable:" || $1=="SwapTotal:" || $1=="SwapFree:" {print}' /proc/meminfo
printf 'canonical_swap=%s\n' "$(readlink -f /dev/block/zram0)"
stat -Lc 'backing=%F|%t:%T|%u|%g|%a' /dev/zram0
for field in dev disksize ro; do printf '%s=%s\n' "$field" "$(cat "/sys/class/block/zram0/$field")"; done
sha256sum /sbin/swapon /sbin/swapoff
[[ $(cat /proc/sys/kernel/random/boot_id) == "$EXPECTED_BOOT_ID" ]]
printf 'swap_restoration_reconciliation=complete\nstate_changes=none\n'
