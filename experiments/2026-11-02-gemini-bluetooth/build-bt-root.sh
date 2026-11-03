#!/bin/sh
# SPDX-License-Identifier: MIT
# Builds the station's Bluetooth userspace as an Alpine chroot, on an aarch64 Linux
# host with sudo and network. Prints the tarball's SHA-256. It goes to a private
# directory, never into Git. Usage: build-bt-root.sh WORKDIR
set -eu
work=$1
version=3.22
archive=alpine-minirootfs-3.22.7-aarch64.tar.gz
sha256=7e9b34ff3304381909e566e2c93de450664ccc724191261423974fc121c11623
base=https://dl-cdn.alpinelinux.org/alpine/v$version
mkdir -p "$work"
cd "$work"
[ -f "$archive" ] || curl -fsSLO "$base/releases/aarch64/$archive"
echo "$sha256  $archive" | sha256sum -c -
sudo umount root/proc root/dev 2> /dev/null || true
sudo rm -rf --one-file-system root
mkdir root
sudo tar -xzpf "$archive" -C root
printf '%s/main\n%s/community\n' "$base" "$base" | sudo tee root/etc/apk/repositories > /dev/null
sudo cp /etc/resolv.conf root/etc/resolv.conf
sudo mount --bind /proc root/proc
sudo mount --bind /dev root/dev
trap 'sudo umount root/proc root/dev' EXIT
sudo chroot root /sbin/apk update -q
sudo chroot root /sbin/apk add -q --no-progress \
	bluez=5.82-r0 bluez-btmon=5.82-r0 bluez-deprecated=5.82-r0 \
	bluez-alsa=4.3.1-r0 bluez-alsa-utils=4.3.1-r0 dbus=1.16.2-r1 alsa-utils=1.2.14-r0
sudo chroot root /sbin/apk info -v 2> /dev/null | sort > packages.txt
sudo rm -f root/etc/resolv.conf
sudo rm -rf root/var/cache/apk/*
# Classic Bluetooth only, and the adapter stays off until asked.
sudo sh -c 'printf "[General]\nControllerMode = bredr\n[Policy]\nAutoEnable = false\n" > root/etc/bluetooth/main.conf'
sudo tar --numeric-owner -czf bt-root.tar.gz -C root .
sha256sum bt-root.tar.gz
