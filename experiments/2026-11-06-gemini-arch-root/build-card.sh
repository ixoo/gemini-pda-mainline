#!/bin/bash
# SPDX-License-Identifier: MIT
# Build the microSD root image for the Arch root (README.md, step 2), in the dev VM.
# usage: sudo build-card.sh CACHE_DIR OUTPUT_DIR [SIZE]
#
# Fetches the official Arch Linux ARM aarch64 tarball and its signature into
# CACHE_DIR (resumable, kept between runs), and verifies them with gpgv against
# the build-system key, which is fetched by its pinned fingerprint and refused
# unless that fingerprint matches. Writes OUTPUT_DIR/card.img (sparse, SIZE,
# default 4G): a GPT with one partition named gemini-arch, of the
# Discoverable Partitions root type for 64-bit ARM, holding ext4 labelled
# gemini-arch. The root is the tarball, with:
#   - the kernel, linux-firmware and mkinitcpio packages removed, and ignored;
#   - upgraded from the official repositories, with iwd, iw, wireless-regdb and sudo;
#   - root locked and the default alarm user removed; sshd masked;
#   - an uninitialised machine-id, so systemd treats the first boot as first;
#   - an fstab line for the root, and the mount points stage 1 needs.
# No firmware, keys or calibration go in. The VM is aarch64, so the root's own
# pacman runs in a chroot. OUTPUT_DIR/card.json records every input and output
# checksum. Nothing here touches a device.
set -euo pipefail

FINGERPRINT=68B3537F39A313B3E574D06777193F152BDBE6A6
URL=http://os.archlinuxarm.org/os/ArchLinuxARM-aarch64-latest.tar.gz
ROOT_TYPE=b921b045-1df0-41c3-af44-4c6f280d3fae
KEYSERVER=hkps://keyserver.ubuntu.com
# Not in the tarball, and needed before the root has any network.
EXTRA=(iwd iw wireless-regdb sudo)

[ "$#" -ge 2 ] && [ "$#" -le 3 ] || { sed -n '3,4p' "$0" >&2; exit 2; }
[ "$(id -u)" = 0 ] || { echo "build-card: run as root" >&2; exit 2; }
[ "$(uname -m)" = aarch64 ] || { echo "build-card: needs an aarch64 host for the chroot" >&2; exit 2; }
cache=$1
out=$2
size=${3:-4G}
[ ! -e "$out" ] || { echo "build-card: $out exists" >&2; exit 2; }
mkdir -p "$cache"
mkdir -m 0755 "$out"

tarball=$cache/${URL##*/}
curl -fsSL --retry 3 -C - -o "$tarball" "$URL"
curl -fsSL --retry 3 -o "$tarball.sig" "$URL.sig"

# The key comes from a keyserver, so only its fingerprint is trusted.
work=$(mktemp -d)
mnt=$work/root
loop=
mounts_under() { awk -v p="$1/" 'index($2 "/", p) == 1 {print $2}' /proc/mounts | sort -r; }
# The chroot binds the host's /dev and /sys, so the work directory is removed only
# when nothing is mounted under it any more: an rm -rf through a live /dev bind
# deletes the host's device nodes.
cleanup() {
	set +e
	pkill -f 'pacman-gnupg' 2>/dev/null && sleep 1
	for m in $(mounts_under "$work"); do umount -R "$m" 2>/dev/null || umount -l "$m"; done
	[ -n "$loop" ] && losetup -d "$loop"
	if [ -n "$(mounts_under "$work")" ]; then
		echo "build-card: mounts remain under $work; left in place" >&2
	else
		rm -rf "$work"
	fi
}
trap cleanup EXIT
export GNUPGHOME=$work/gnupg
mkdir -m 0700 "$GNUPGHOME"
gpg -q --batch --keyserver "$KEYSERVER" --recv-keys "$FINGERPRINT"
got=$(gpg --batch --with-colons --fingerprint "$FINGERPRINT" | awk -F: '$1 == "fpr" {print $10; exit}')
[ "$got" = "$FINGERPRINT" ] || { echo "build-card: key fingerprint $got is not $FINGERPRINT" >&2; exit 1; }
gpg -q --batch --export "$FINGERPRINT" >"$work/key.gpg"
gpgv --keyring "$work/key.gpg" "$tarball.sig" "$tarball" 2>"$work/gpgv.log" ||
	{ cat "$work/gpgv.log" >&2; echo "build-card: signature check failed" >&2; exit 1; }
tarball_sha=$(sha256sum "$tarball" | cut -d' ' -f1)

image=$out/card.img
truncate -s "$size" "$image"
sgdisk -o -n1:0:0 -c1:gemini-arch -t1:"$ROOT_TYPE" "$image" >/dev/null
loop=$(losetup -P --show -f "$image")
udevadm settle
for _ in $(seq 50); do [ -b "${loop}p1" ] && break; sleep 0.2; done
blockdev --setrw "$loop" "${loop}p1"
mkfs.ext4 -q -L gemini-arch "${loop}p1"
mkdir "$mnt"
mount "${loop}p1" "$mnt"
bsdtar -xpf "$tarball" -C "$mnt"

mount -t proc proc "$mnt/proc"
mount --rbind /sys "$mnt/sys"
mount --make-rslave "$mnt/sys"
mount --rbind /dev "$mnt/dev"
mount --make-rslave "$mnt/dev"
mount -t tmpfs tmpfs "$mnt/run"
in_root() { chroot "$mnt" /usr/bin/env -i PATH=/usr/bin LANG=C "$@"; }

mapfile -t remove < <(in_root pacman -Qq | grep -E '^(linux-aarch64|linux-firmware.*|mkinitcpio.*)$' || true)
[ "${#remove[@]}" -eq 0 ] || in_root pacman -Rdd --noconfirm "${remove[@]}" >/dev/null
removed="${remove[*]}"
sed -i 's/^#\?IgnorePkg *=.*/IgnorePkg = linux-aarch64 linux-firmware mkinitcpio/' "$mnt/etc/pacman.conf"
grep -qx 'IgnorePkg = linux-aarch64 linux-firmware mkinitcpio' "$mnt/etc/pacman.conf"

# The tarball lacks the Wi-Fi tools, and Wi-Fi is the root's only way to its
# packages, so they go in here. The whole root is upgraded with them, since adding
# packages to an older tarball would be a partial upgrade. pacman checks every
# package against a keyring kept in /run, outside the image: a keyring made here
# would put one generated secret in every copy, so the first boot makes its own.
resolv=$mnt/etc/resolv.conf
mv "$resolv" "$work/resolv.conf.saved" 2>/dev/null || true
cp -L /etc/resolv.conf "$resolv"
in_root pacman-key --gpgdir /run/pacman-gnupg --init >/dev/null 2>&1
in_root pacman-key --gpgdir /run/pacman-gnupg --populate archlinuxarm >/dev/null 2>&1
in_root pacman --gpgdir /run/pacman-gnupg -Syu --needed --noconfirm --noprogressbar "${EXTRA[@]}" >"$work/pacman.log" 2>&1 ||
	{ tail -20 "$work/pacman.log" >&2; echo "build-card: pacman failed" >&2; exit 1; }
in_root gpgconf --homedir /run/pacman-gnupg --kill all
rm -f "$resolv"
if [ -e "$work/resolv.conf.saved" ] || [ -L "$work/resolv.conf.saved" ]; then mv "$work/resolv.conf.saved" "$resolv"; fi
rm -rf "$mnt"/var/cache/pacman/pkg/*

in_root passwd -q -l root
if in_root id alarm >/dev/null 2>&1; then in_root userdel -r alarm 2>/dev/null; fi
in_root systemctl disable -q sshd.service
in_root systemctl mask -q sshd.service
rm -f "$mnt"/etc/ssh/ssh_host_*
echo uninitialized >"$mnt/etc/machine-id"
rm -f "$mnt/var/lib/systemd/random-seed"
mkdir -p "$mnt/nvdata" "$mnt/usr/lib/modules"
echo 'PARTLABEL=gemini-arch / ext4 rw,noatime 0 1' >>"$mnt/etc/fstab"

! in_root pacman -Qq | grep -qE '^(linux-aarch64|linux-firmware|mkinitcpio)' ||
	{ echo "build-card: an ignored package came back" >&2; exit 1; }
packages=$(in_root pacman -Q | sha256sum | cut -d' ' -f1)
count=$(in_root pacman -Qq | wc -l)
systemd=$(in_root pacman -Q systemd | cut -d' ' -f2)
in_root pacman -Q >"$out/packages.txt"
# Only the directories that exist are searched.
private=$(find "$mnt/usr/lib/firmware" "$mnt/nvdata" "$mnt/root" "$mnt/etc/ssh" -maxdepth 4 \
	\( -name 'ssh_host_*' -o -name 'WIFI*' -o -name 'WMT_SOC*' -o -name 'authorized_keys' \) \
	2>/dev/null | wc -l || true)
[ "$private" -eq 0 ] || { echo "build-card: private files in the root" >&2; exit 1; }
used=$(df -B1 --output=used "$mnt" | tail -1 | tr -d ' ')

for m in run dev sys proc; do umount -R "$mnt/$m"; done
umount "$mnt"
[ -z "$(mounts_under "$work")" ] || { echo "build-card: mounts remain under $work" >&2; exit 1; }
e2fsck -fn "${loop}p1" >/dev/null
losetup -d "$loop"
loop=
image_sha=$(sha256sum "$image" | cut -d' ' -f1)
cat >"$out/card.json" <<EOF
{
  "tarball_url": "$URL",
  "tarball_sha256": "$tarball_sha",
  "signature": "$(grep -o 'Good signature from "[^"]*"' "$work/gpgv.log" | head -1 | sed 's/"/\\"/g')",
  "key_fingerprint": "$FINGERPRINT",
  "packages_removed": "$removed",
  "package_count": $count,
  "package_list_sha256": "$packages",
  "packages_added": "${EXTRA[*]}",
  "systemd": "$systemd",
  "root_bytes_used": $used,
  "image_size": "$size",
  "image_sha256": "$image_sha"
}
EOF
cat "$out/card.json"
