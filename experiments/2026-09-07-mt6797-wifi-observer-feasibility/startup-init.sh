#!/bin/busybox sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# Install as /init only in a separately admitted observation candidate.
[ "$$" -eq 1 ] || exit 1
PATH=/bin:/usr/bin:/sbin:/usr/sbin
export PATH
umask 077
stage=devtmpfs
log_ready=0
boot=unknown
mark() {
    stage=$1
    if [ "$log_ready" -eq 1 ]; then
        printf '<11>wifi-bootstrap-v1 boot=%s shell=%s\n' "$boot" "$stage" >&3
    fi
}
park() {
    trap - EXIT
    trap '' HUP INT TERM
    if [ "$log_ready" -eq 1 ]; then
        printf '<11>wifi-bootstrap-v1 boot=%s stopped=%s\n' "$boot" "$stage" >&3 || :
    fi
    printf '%s\n' 'wifi-startup: stopped; no retry or software restart' || :
    while :; do /bin/busybox sleep 3600; done
}
trap park EXIT HUP INT TERM
set -eu
/bin/busybox mount -t devtmpfs -o nosuid,noexec devtmpfs /dev
[ "$(/bin/busybox stat -c '%t:%T' /dev/kmsg)" = '1:b' ]
if [ ! -c /dev/kmsg ] || [ -L /dev/kmsg ]; then
    park
fi
exec 3>/dev/kmsg
log_ready=1
mark proc
/bin/busybox mount -t proc -o nosuid,nodev,noexec proc /proc
IFS= read -r boot < /proc/sys/kernel/random/boot_id
[ "${#boot}" -eq 36 ] || park
case "$boot" in *[!0-9a-f-]*|'') boot=invalid; park ;; esac
mark sysfs
/bin/busybox mount -t sysfs -o nosuid,nodev,noexec sysfs /sys
mark pstore
/bin/busybox mount -t pstore -o ro,nosuid,nodev,noexec pstore /sys/fs/pstore
mark console
exec </dev/console >/dev/console 2>&1
mark sysrq
printf '0\n' > /proc/sys/kernel/sysrq
mark run
/bin/busybox mount -t tmpfs -o size=8m,mode=0700,nosuid,nodev,noexec tmpfs /run
for directory in /lib/firmware /vendor/firmware /data/nvram /etc/wifi-cycle /opt/wifi-cycle /init; do
    mark "bind:$directory"
    /bin/busybox mount -o bind "$directory" "$directory"
    mark "readonly:$directory"
    /bin/busybox mount -o remount,bind,ro,nosuid,nodev,noexec "$directory"
done
mark python
exec /bin/busybox env -i PATH="$PATH" LC_ALL=C PYTHONDONTWRITEBYTECODE=1 \
    /usr/bin/python3.11 -B /opt/wifi-cycle/startup.py
