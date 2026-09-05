#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Read-only, admission-required reconciliation after failed frozen upload.
set -euo pipefail
export LC_ALL=C
[[ $(id -u) == 0 && $(uname -r) == 3.18.41+ && $(uname -m) == aarch64 ]]
[[ ${EXPECTED_BOOT_ID:-} =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]]
check_state() {
 [[ $(cat /proc/sys/kernel/random/boot_id) == "$EXPECTED_BOOT_ID" ]]
 [[ $(readlink /proc/self/ns/mnt) == "$(readlink /proc/1/ns/mnt)" ]]
 awk 'NR!=1 || NF!=5 || $1!="Filename" {bad=1} END {exit(bad || NR!=1)}' /proc/swaps
 [[ -d /dev/shm && ! -L /dev/shm && $(readlink -f /dev/shm) == /dev/shm ]]
 [[ $(findmnt -rn -o TARGET,FSTYPE --target /dev/shm) == '/dev/shm tmpfs' ]]
 [[ $(stat -c '%u %a' /dev/shm) == '0 1777' ]]
}
check_state
printf 'staging_reconciliation=begin\n'
expected=a423ad63fbb97d0f3fc4726d3957e05d3951480996b754d839a89d80a1232821
shopt -s nullglob
stages=(/dev/shm/.gemini-a53-"$expected".*)
[[ ${#stages[@]} -le 1 ]]
printf 'stage_count=%s\ngemini_uid=%s\n' "${#stages[@]}" "$(id -u gemini)"
for path in "${stages[@]}"; do
 [[ $path =~ ^/dev/shm/\.gemini-a53-[0-9a-f]{64}\.[A-Za-z0-9]{8}$ ]]
 [[ -f $path && ! -L $path ]]
 printf 'stage_path=%s\n' "$path"
 stat -c 'stage_metadata=%u|%a|%s|%h|%d|%i' -- "$path"
 [[ $(stat -c %s "$path") =~ ^[0-9]{1,8}$ ]]
 [[ $(stat -c %s "$path") -le 16777216 ]]
 # Do not read candidate contents or restore swap. Inspect bounded fd metadata.
done
processes=(/proc/[0-9]*)
[[ ${#processes[@]} -le 1024 ]]
fd_count=0
for process in "${processes[@]}"; do
 [[ -d $process ]] || continue
 [[ -r $process/fd && -x $process/fd ]] || { [[ ! -d $process ]] && continue; exit 2; }
 fds=("$process"/fd/[0-9]*)
 [[ ${#fds[@]} -le 1024 ]]
 for fd in "${fds[@]}"; do
  fd_count=$((fd_count+1)); [[ $fd_count -le 32768 ]]
  if ! destination=$(readlink "$fd"); then
   [[ ! -L $fd ]] && continue
   exit 2
  fi
  case "$destination" in
   /dev/shm/.gemini-a53-"$expected".*)
    printf 'stage_fd=%s\ndestination=%s\n' "$fd" "$destination"
    ;;
  esac
 done
done
check_state
printf 'staging_reconciliation=complete\nstate_changes=none\n'
