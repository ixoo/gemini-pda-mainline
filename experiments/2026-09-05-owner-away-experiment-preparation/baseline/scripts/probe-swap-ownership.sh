#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Read-only proposal; requires separate admission and bounded private transport.
set -euo pipefail
export LC_ALL=C
[[ $(id -u) == 0 && $(uname -r) == 3.18.41+ && $(uname -m) == aarch64 ]]
[[ ${EXPECTED_BOOT_ID:-} =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]]
[[ ${EXPECTED_SWAP_SIZE:-} =~ ^[1-9][0-9]{0,9}$ ]]
check_state() {
 [[ $(cat /proc/sys/kernel/random/boot_id) == "$EXPECTED_BOOT_ID" ]]
 awk -v size="$EXPECTED_SWAP_SIZE" '
  NR==1 {if ($1!="Filename" || NF!=5) exit 1; next}
  NR==2 {if (NF!=5 || $1!="/dev/block/zram0" || $2!="partition" ||
   $3!=size || $4!="0" || $5!="-1") exit 1; next}
  {exit 1}
  END {if (NR!=2) exit 1}' /proc/swaps
 [[ $(readlink -f /dev/block/zram0) == /dev/zram0 && -b /dev/zram0 ]]
 awk '$1=="MemAvailable:" {n++; if (NF!=3 || $2!~/^[0-9]+$/ ||
  $3!="kB" || $2<1114112) exit 1; print}
  END {if(n!=1) exit 1}' /proc/meminfo
 cat /proc/swaps
}
printf 'swap_ownership=begin\n'
check_state
root=/var/lib/lxc/android/rootfs
for component in /var /var/lib /var/lib/lxc /var/lib/lxc/android "$root"; do
 [[ -d $component && ! -L $component ]]
done
# Exactly twenty observed literal paths; no dynamic import expansion or recursion.
for name in init.rc init.mt6797.rc fstab.mt6797 init.environ.rc \
 init.connectivity.rc init.project.rc FWUpgradeInit.rc init.aee.rc init.fon.rc \
 init.rilproxy.rc init.volte.rc init.mal.rc init.epdg.rc init.wfca.rc \
 init.trustonic.rc init.common_svc.rc init.microtrust.rc init.sensor_bio.rc \
 init.sensor.rc init.modem.rc; do
 [[ $name =~ ^[A-Za-z0-9_.-]+$ && $name != .* ]]
 path=$root/$name
 printf 'startup_file=%s\n' "$name"
 if [[ ! -e $path && ! -L $path ]]; then printf 'state=absent\n'; continue; fi
 [[ ! -L $path && -f $path && -r $path ]]
 bytes=$(stat -Lc %s -- "$path")
 [[ $bytes =~ ^(0|[1-9][0-9]{0,5})$ && $bytes -le 65536 ]]
 content=$(head -c 65537 -- "$path")
 [[ ${#content} -le 65536 && $(stat -Lc %s -- "$path") == "$bytes" ]]
 printf 'state=bounded-text\n'
 printf '%s' "$content" | sha256sum | awk '{print "text_sha256=" $1}'
 printf '%s\n' "$content" | awk '
  BEGIN {header="<no preceding stanza>"; headerline=0; hits=0; imports=0}
  /^[[:space:]]*(on|service)[[:space:]]/ {header=$0; headerline=NR}
  /^[[:space:]]*import[[:space:]]/ {print "import:" NR ":" $0; imports++}
  {lower=tolower($0)}
  lower ~ /swap|zram/ {
   print "stanza:" headerline ":" header
   print "match:" NR ":" $0
   hits++
  }
  END {print "swap_matching_lines=" hits; print "import_lines=" imports}'
done
check_state
printf 'swap_ownership=complete\nstate_changes=none\n'
