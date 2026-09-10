#!/bin/busybox sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# Install as /init only in a separately admitted observation candidate.
[ "$$" -eq 1 ] || exit 1
PATH=/bin:/usr/bin:/sbin:/usr/sbin
export PATH
umask 077
park() {
    printf '%s\n' 'wifi-startup: stopped; no retry or software restart'
    while :; do /bin/busybox sleep 3600; done
}
trap park EXIT HUP INT TERM
set -eu
/bin/busybox mount -t proc -o nosuid,nodev,noexec proc /proc
/bin/busybox mount -t sysfs -o nosuid,nodev,noexec sysfs /sys
/bin/busybox mount -t pstore -o ro,nosuid,nodev,noexec pstore /sys/fs/pstore
/bin/busybox mount -t devtmpfs -o nosuid,noexec devtmpfs /dev
exec </dev/console >/dev/console 2>&1
printf '0\n' > /proc/sys/kernel/sysrq
/bin/busybox mount -t tmpfs -o size=8m,mode=0700,nosuid,nodev,noexec tmpfs /run
for directory in /lib/firmware /vendor/firmware /data/nvram /etc/wifi-cycle /opt/wifi-cycle /init; do
    /bin/busybox mount -o bind "$directory" "$directory"
    /bin/busybox mount -o remount,bind,ro,nosuid,nodev,noexec "$directory"
done
exec /bin/busybox env -i PATH="$PATH" LC_ALL=C PYTHONDONTWRITEBYTECODE=1 \
    /usr/bin/python3.11 -B /opt/wifi-cycle/startup.py
