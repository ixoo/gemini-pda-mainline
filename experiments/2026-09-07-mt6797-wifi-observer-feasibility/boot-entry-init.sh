#!/bin/busybox sh
# SPDX-License-Identifier: MIT
# One boot-entry control; this is not the Wi-Fi export or cycle launcher.
# Keep the control UUID equal to BOOT_ENTRY_CYCLE_ID in startup.py.
[ "$$" -eq 1 ] || exit 1
PATH=/bin:/usr/bin:/sbin:/usr/sbin
export PATH
umask 077
park() {
    trap - EXIT
    trap '' HUP INT TERM
    while :; do /bin/busybox sleep 3600; done
}
trap park EXIT HUP INT TERM
set -efu
/bin/busybox mount -t devtmpfs -o nosuid,noexec devtmpfs /dev
/bin/busybox mount -t proc -o nosuid,nodev,noexec proc /proc
[ "$(/bin/busybox uname -m)" = aarch64 ]
[ "$(/bin/busybox uname -r)" = 3.18.41+ ]
IFS= read -r boot < /proc/sys/kernel/random/boot_id
case "$boot" in
    *[!0-9a-f-]*|'') park ;;
esac
case "$boot" in
    ????????-????-????-????-????????????) ;;
    *) park ;;
esac
[ "$boot" != 00000000-0000-0000-0000-000000000000 ]
IFS= read -r cmdline < /proc/cmdline
selected=
for argument in $cmdline; do
    case "$argument" in
        rdinit=*|panic=*|cpuidle.off=*|ramoops.pmsg_capture=*|wifi_cycle=*|sysrq_always_enabled*)
            selected="$selected $argument" ;;
    esac
done
[ "$selected" = ' rdinit=/init panic=0 cpuidle.off=1 ramoops.pmsg_capture=1 wifi_cycle=7f21b732-da47-4245-ad83-e985044054a6' ]
[ -c /dev/kmsg ]
[ ! -L /dev/kmsg ]
[ "$(/bin/busybox stat -c '%t:%T' /dev/kmsg)" = '1:b' ]
exec 3>/dev/kmsg
# One write attempt. A failed marker parks before the restart request.
printf '<11>wifi-boot-entry-v1 control=7f21b732-da47-4245-ad83-e985044054a6 boot=%s stage=before-normal-restart\n' "$boot" >&3
# Disable traps before the sole attempt. A returned call never retries.
trap - EXIT
trap '' HUP INT TERM
/bin/busybox reboot -f || :
park
