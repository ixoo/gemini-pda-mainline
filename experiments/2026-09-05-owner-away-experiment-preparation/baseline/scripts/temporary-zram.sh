#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Proposal only: exact action requires coordinator admission and private receipt.
set -euo pipefail
export LC_ALL=C
[[ ${ACTION:-} == deactivate || ${ACTION:-} == restore ]]
[[ $(id -u) == 0 && $(uname -r) == 3.18.41+ && $(uname -m) == aarch64 ]]
[[ ${EXPECTED_BOOT_ID:-} =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]]
identity() {
 [[ $(cat /proc/sys/kernel/random/boot_id) == "$EXPECTED_BOOT_ID" ]]
 [[ $(readlink /proc/self/ns/mnt) == "$(readlink /proc/1/ns/mnt)" ]]
 [[ $(readlink -f /dev/block/zram0) == /dev/zram0 && -b /dev/zram0 ]]
 [[ $(stat -Lc '%t:%T' /dev/zram0) == fe:0 ]]
 [[ $(cat /sys/class/block/zram0/dev) == 254:0 ]]
 [[ $(cat /sys/class/block/zram0/disksize) == 1976668160 ]]
 [[ $(cat /sys/class/block/zram0/ro) == 0 ]]
 [[ $(sha256sum /sbin/swapon) == '65a1f6e5ec6b2cfbab2c2f7d6689a6787b1a50835ab1b9d4d659bcd381272546  /sbin/swapon' ]]
 [[ $(sha256sum /sbin/swapoff) == '7c053a97715eb5bc6370abb351a3146f94d8da6a489ed7a6b5567aecdc830e3b  /sbin/swapoff' ]]
 awk '$1=="MemAvailable:" {n++; if(NF!=3 || $2!~/^[0-9]+$/ || $3!="kB" || $2<1114112) exit 1}
  END {if(n!=1) exit 1}' /proc/meminfo
}
active() {
 awk 'NR==1 {if($1!="Filename" || NF!=5) exit 1; next}
  NR==2 {if(NF!=5 || ($1!="/dev/block/zram0" && $1!="/dev/zram0") || $2!="partition" ||
   $3!="1930336" || $4!="0" || $5!="-1") exit 1; next}
  {exit 1} END {if(NR!=2) exit 1}' /proc/swaps || return 1
 local spelling
 spelling=$(awk 'NR==2 {print $1}' /proc/swaps) || return 1
 [[ $(readlink -f -- "$spelling") == /dev/zram0 ]]
}
inactive() {
 awk 'NR==1 {if($1!="Filename" || NF!=5) exit 1; next}
  {exit 1} END {if(NR!=1) exit 1}' /proc/swaps
}
restore_once() {
 identity && inactive || return 1
 /sbin/swapon -- /dev/block/zram0 || return 1
 identity && active || return 1
 printf 'restoration=verified\n'
}
changed=no
finished=no
cleanup() {
 status=$?
 trap - EXIT HUP INT TERM
 if [[ $changed == yes && $finished == no ]]; then
  if restore_once; then printf 'handled_abort=restored\n'; else printf 'handled_abort=restoration-unresolved\n'; fi
 fi
 exit "$status"
}
trap cleanup EXIT
trap 'exit 129' HUP
trap 'exit 130' INT
trap 'exit 143' TERM
identity
if [[ $ACTION == restore ]]; then
 # Separate admission must confirm no installer staging or writers remain.
 inactive
 restore_once
 finished=yes
 printf 'temporary_zram=restoration-complete\n'
 exit 0
fi
# Two fresh samples, then a separate immediate pre-mutation gate.
for sample in 1 2; do
 identity
 active
 printf 'pre_deactivation_sample=%s\n' "$sample"
 [[ $sample == 2 ]] || sleep 2
done
identity
active
printf 'temporary_zram=deactivation-begin\n'
# If this call is interrupted/indeterminate, changed stays no: reconcile before
# any further operation. No competing restoration during an unresolved kernel call.
/sbin/swapoff -- /dev/block/zram0
changed=yes
identity
inactive
cat /proc/swaps
awk '$1=="MemAvailable:" {print}' /proc/meminfo
printf 'temporary_zram=deactivation-complete\n'
finished=yes
