#!/bin/sh
# SPDX-License-Identifier: MIT
# shellcheck shell=dash
# Station Bluetooth userspace, fed over SSH: bt-start.sh ROOT_TARBALL
# Unpacks the chroot under /run/bt-root and starts dbus-daemon, bluetoothd and
# bluealsa. bluetoothd powers nothing on with AutoEnable off. The radio-side effects
# of this module set are at insmod, which opens the device once; see the record.
# Logs stay in RAM under /run/bt-root/run, are private and hold device addresses.
set -eu
root=/run/bt-root
if [ ! -d "$root/usr" ]; then
	mkdir -p "$root"
	tar -xzf "$1" -C "$root"
fi
mounted() { grep -q " $1 " /proc/mounts; }
mounted "$root/proc" || mount -t proc proc "$root/proc"
mounted "$root/sys" || mount -t sysfs sysfs "$root/sys"
mounted "$root/dev" || mount --bind /dev "$root/dev"
mkdir -p "$root/run/dbus" "$root/var/lib/bluetooth" "$root/var/lib/bluealsa"
in_root() { chroot "$root" /usr/bin/env PATH=/usr/bin:/bin:/usr/sbin:/sbin "$@"; }
pidof dbus-daemon > /dev/null || in_root dbus-daemon --system --nopidfile --fork
sleep 1
pidof bluetoothd > /dev/null || in_root sh -c \
	'exec /usr/lib/bluetooth/bluetoothd -n > /run/bluetoothd.log 2>&1' < /dev/null &
sleep 1
pidof bluealsa > /dev/null || in_root sh -c \
	'exec bluealsa -p a2dp-source --codec=-AAC --a2dp-force-audio-cd --initial-volume=30 > /run/bluealsa.log 2>&1' < /dev/null &
sleep 1
echo "dbus=$(pidof dbus-daemon) bluetoothd=$(pidof bluetoothd) bluealsa=$(pidof bluealsa)"
