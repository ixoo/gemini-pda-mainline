#!/bin/sh
# SPDX-License-Identifier: MIT
# Builds the release's parent RAM root from public inputs pinned by hash: the Alpine
# minirootfs, the packages in packages.sha256 and Linux's default keymap. The
# userspace comes from Alpine as is, with its libraries; backlight-policy and
# console-unicode-mode are compiled here with Alpine's gcc. It holds no keys and no
# firmware, and goes to a private directory, never into Git. compose-station.py
# takes the output, with the tester's public key. Runs on an aarch64 Linux host with
# sudo, network, python3, cpio and readelf.
# Usage: build-parent.sh WORKDIR
# Output: WORKDIR/out/parent-initramfs.img, WORKDIR/out/tools/, WORKDIR/out/SHA256SUMS
set -eu
umask 022
here=$(cd "$(dirname "$0")" && pwd)
repo=$(cd "$here/../../.." && pwd)
work=$1
archive=alpine-minirootfs-3.22.7-aarch64.tar.gz
sha256=7e9b34ff3304381909e566e2c93de450664ccc724191261423974fc121c11623
base=https://dl-cdn.alpinelinux.org/alpine/v3.22
# generate-console-keymap.py refuses anything but this exact file, by its SHA-256.
keymap_url=https://raw.githubusercontent.com/torvalds/linux/v7.1/drivers/tty/vt/defkeymap.c_shipped
keymap_dir=$repo/experiments/2026-07-20-keyboard-console-map-diagnostic

mkdir -p "$work"
cd "$work"
[ -f "$archive" ] || curl -fsSLO "$base/releases/aarch64/$archive"
echo "$sha256  $archive" | sha256sum -c --quiet -
while read -r _ path; do
	[ -f "pkgs/$path" ] || curl -fsSL --create-dirs -o "pkgs/$path" "$base/$path"
done < "$here/packages.sha256"
(cd pkgs && sha256sum -c --quiet "$here/packages.sha256")
[ -f defkeymap.c_shipped ] || curl -fsSLO "$keymap_url"

sudo umount root/proc root/dev 2> /dev/null || true
sudo rm -rf --one-file-system root
mkdir root
sudo tar -xzpf "$archive" -C root
sudo truncate -s 0 root/etc/apk/repositories
sudo cp -r pkgs root/pkgs
sudo mount --bind /proc root/proc
sudo mount --bind /dev root/dev
trap 'sudo umount root/proc root/dev' EXIT
# shellcheck disable=SC2016 # expanded inside the chroot
sudo chroot root /bin/sh -c 'apk add -q --no-progress --no-network --no-cache $(find /pkgs -name "*.apk")'
sudo cp "$repo/experiments/2026-10-30-mainline-dev-station/backlight-policy.c" \
	"$keymap_dir/src/console-unicode-mode.c" root/tmp/
sudo chroot root gcc -static -O2 -s -Wall -Wextra -Werror -fno-ident \
	-o /tmp/backlight-policy /tmp/backlight-policy.c
sudo chroot root gcc -static -Os -s -std=c11 -Wall -Wextra -Werror -fno-ident \
	-o /tmp/console-unicode-mode /tmp/console-unicode-mode.c

rm -rf stage out
mkdir -p stage/bin stage/dev stage/etc stage/lib/firmware/mediatek/mt6797 stage/proc \
	stage/run stage/sys out/tools
install -d -m 700 stage/etc/dropbear stage/root stage/root/.ssh
printf 'root:x:0:\n' > stage/etc/group
python3 -I "$keymap_dir/scripts/generate-console-keymap.py" \
	--source defkeymap.c_shipped --output stage/etc/gemini-us.bkeymap
install -m 755 root/lib/ld-musl-aarch64.so.1 stage/lib/
ln -s ld-musl-aarch64.so.1 stage/lib/libc.musl-aarch64.so.1

add_libs() {
	for lib in $(readelf -d "$1" | sed -n 's/.*(NEEDED).*\[\(.*\)\]/\1/p'); do
		[ -e "stage/lib/$lib" ] && continue
		for dir in lib usr/lib; do
			[ -e "root/$dir/$lib" ] && install -m 644 "root/$dir/$lib" stage/lib/ && break
		done
		[ -e "stage/lib/$lib" ] || { echo "no $lib for $1" >&2; exit 1; }
		add_libs "stage/lib/$lib"
	done
}
install -m 755 root/bin/busybox.static stage/bin/busybox
install -m 755 root/tmp/console-unicode-mode root/usr/sbin/dropbear root/usr/bin/dropbearkey \
	root/usr/sbin/iw root/sbin/wpa_supplicant root/sbin/wpa_cli stage/bin/
install -m 755 root/tmp/backlight-policy root/usr/bin/amixer root/usr/bin/aplay out/tools/
for file in stage/bin/dropbear stage/bin/dropbearkey stage/bin/iw stage/bin/wpa_supplicant \
	stage/bin/wpa_cli out/tools/amixer out/tools/aplay; do
	add_libs "$file"
done
install -m 644 root/lib/firmware/regulatory.db root/lib/firmware/regulatory.db.p7s out/tools/
# The card configuration, without alsa-ucm-conf's 3 MiB of use-case profiles.
mkdir out/tools/alsa
tar -C root/usr/share/alsa --exclude=ucm2 -cf - . | tar -C out/tools/alsa -xf -

find stage -exec touch -h -d @0 {} +
(cd stage && find . | sed 's,^\./,,' | LC_ALL=C sort |
	cpio --quiet -o -H newc --reproducible --owner=+0:+0) |
	gzip -n -9 > out/parent-initramfs.img
sums=$(cd out && find . -type f | LC_ALL=C sort | xargs sha256sum)
printf '%s\n' "$sums" > out/SHA256SUMS
sha256sum out/parent-initramfs.img
