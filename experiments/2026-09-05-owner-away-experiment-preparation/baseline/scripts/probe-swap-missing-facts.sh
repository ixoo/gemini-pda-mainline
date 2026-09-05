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
printf 'swap_missing_facts=begin\n'
check_state
# Fixed candidates only. No recursive search, service action or configuration read
# beyond these startup paths. Output is private and is not source for republication.
for path in \
 /etc/rc.local /etc/init.d/zram-config /etc/init/zram-config.conf \
 /usr/bin/init-zram-swapping \
 /lib/systemd/system/zram-config.service /etc/systemd/system/zram-config.service \
 /var/lib/lxc/android/config \
 /init.rc /init.mt6797.rc /fstab.mt6797 \
 /var/lib/lxc/android/rootfs/init.rc \
 /var/lib/lxc/android/rootfs/init.mt6797.rc \
 /var/lib/lxc/android/rootfs/fstab.mt6797; do
 printf 'startup_path=%s\n' "$path"
 if [[ ! -e $path && ! -L $path ]]; then printf 'state=absent\n'; continue; fi
 if [[ -L $path || ! -f $path || ! -r $path ]]; then
  printf 'state=unresolved-type-or-access\n'; continue
 fi
 bytes=$(stat -Lc %s -- "$path")
 if [[ ! $bytes =~ ^(0|[1-9][0-9]{0,5})$ || $bytes -gt 65536 ]]; then
  printf 'state=unresolved-size\n'; continue
 fi
 # Read at most 64 KiB + one sentinel; never execute or source captured text.
 content=$(head -c 65537 -- "$path")
 [[ ${#content} -le 65536 && $(stat -Lc %s -- "$path") == "$bytes" ]]
 printf 'state=bounded-text\n'
 printf '%s' "$content" | sha256sum | awk '{print "text_sha256=" $1}'
 printf '%s\n' "$content" | awk '
  BEGIN {IGNORECASE=0}
  /[Zz][Rr][Aa][Mm]|swap(on|off)?|mkswap|^import |mount_all|^on |^service |ExecStart|Restart=|lxc.rootfs/ {
   n++; if(n<=32) print NR ":" substr($0,1,240)
  }
  END {if(n>32) print "matches_truncated=yes"; print "matching_lines=" n}'
done
for unit in zram-config.service lxc@android.service droid-hal-init.service; do
 systemctl show -p Id -p LoadState -p ActiveState -p SubState \
  -p FragmentPath -p SourcePath -p Restart -p ExecStart -- "$unit"
done
check_state
printf 'swap_missing_facts=complete\nstate_changes=none\n'
