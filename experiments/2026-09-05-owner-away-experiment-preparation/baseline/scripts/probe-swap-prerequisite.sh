#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Proposed one-shot read-only probe. No invocation/admission is created here.
set -euo pipefail
export LC_ALL=C
[[ $(id -u) == 0 && $(uname -r) == 3.18.41+ && $(uname -m) == aarch64 ]]
[[ ${EXPECTED_BOOT_ID:-} =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]]
[[ $(cat /proc/sys/kernel/random/boot_id) == "$EXPECTED_BOOT_ID" ]]
# BEGIN OPTIONAL_CONFIG
optional_config() {
 local path=$1 before after digest
 if [[ ! -e $path && ! -L $path ]]; then
  printf 'optional_config_state=absent\n'; return 0
 fi
 if [[ -L $path || ! -f $path ]]; then
  printf 'optional_config_state=unsafe-type\n'; return 1
 fi
 if [[ ! -r $path ]]; then
  printf 'optional_config_state=unreadable\n'; return 1
 fi
 before=$(wc -c < "$path") || { printf 'optional_config_state=unreadable\n'; return 1; }
 before=${before//[[:space:]]/}
 if [[ ! $before =~ ^(0|[1-9][0-9]{0,5})$ || $before -gt 65536 ]]; then
  printf 'optional_config_state=invalid-size\n'; return 1
 fi
 digest=$(head -c 65537 -- "$path" | sha256sum) || { printf 'optional_config_state=read-failed\n'; return 1; }
 digest=${digest%% *}
 if [[ ! $digest =~ ^[0-9a-f]{64}$ ]]; then
  printf 'optional_config_state=invalid-digest\n'; return 1
 fi
 after=$(wc -c < "$path") || { printf 'optional_config_state=unreadable\n'; return 1; }
 after=${after//[[:space:]]/}
 if [[ -L $path || ! -f $path || $before != "$after" ]]; then
  printf 'optional_config_state=changed\n'; return 1
 fi
 printf 'optional_config_state=regular\noptional_config_sha256=%s\n' "$digest"
}
# END OPTIONAL_CONFIG
printf 'swap_prerequisite_probe=begin\n'
for sample in 1 2; do
 printf 'sample=%s\n' "$sample"
 cat /proc/swaps
 awk '$1 ~ /^(MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree|SwapCached|Dirty|Writeback):$/ {print}' /proc/meminfo
 [[ $sample == 2 ]] || sleep 2
done
count=$(awk 'END {print NR-1}' /proc/swaps)
[[ $count == 1 ]]
read -r path type size used priority extra < <(awk 'NR == 2 {print}' /proc/swaps)
[[ $path =~ ^/[A-Za-z0-9_./-]+$ && -z ${extra:-} && ( $type == partition || $type == file ) ]]
[[ $size =~ ^[0-9]+$ && $used =~ ^[0-9]+$ && $priority =~ ^-?[0-9]+$ ]]
resolved=$(readlink -f -- "$path")
printf 'swap_path=%s\nresolved_path=%s\n' "$path" "$resolved"
stat -Lc 'backing_metadata=%F|%d|%i|%s|%h|%u|%g|%a|%t:%T' -- "$resolved"
if [[ -b $resolved ]]; then
 node=${resolved##*/}
 [[ $node =~ ^[A-Za-z0-9_-]+$ ]]
 for field in dev size ro; do printf 'block_%s=%s\n' "$field" "$(cat "/sys/class/block/$node/$field")"; done
 if [[ $node =~ ^zram[0-9]+$ ]]; then
  for field in disksize orig_data_size mem_used_total backing_dev; do
   if [[ -r /sys/class/block/$node/$field ]]; then
    printf 'zram_%s=%s\n' "$field" "$(cat "/sys/class/block/$node/$field")"
   else printf 'zram_%s=absent\n' "$field"; fi
  done
 fi
else
 [[ -f $resolved ]]
 findmnt -rn -o SOURCE,TARGET,FSTYPE --target "$resolved"
fi
printf 'swap_utilities=\n'
for tool in swapon swapoff; do executable=$(command -v "$tool"); sha256sum "$executable"; done
dpkg-query -W -f='util_linux_version=${Version}\n' util-linux
printf 'swap_units=\n'
units=$(systemctl list-units --all --type=swap --no-pager --no-legend --plain)
printf '%s\n' "$units"
[[ $(printf '%s\n' "$units" | awk 'NF {n++} END {print n+0}') -le 4 ]]
while read -r unit _; do
 [[ -n $unit ]] || continue
 systemctl show -p Id -p What -p ActiveState -p SubState -p FragmentPath -p SourcePath \
  -p Options -p Priority -p TriggeredBy -p PartOf -- "$unit"
done <<<"$units"
config_ok=yes
optional_config /etc/fstab || config_ok=no
[[ $(cat /proc/sys/kernel/random/boot_id) == "$EXPECTED_BOOT_ID" ]]
printf 'final_boot_identity=matched\n'
[[ $config_ok == yes ]]
printf 'swap_prerequisite_probe=complete\nstate_changes=none\n'
