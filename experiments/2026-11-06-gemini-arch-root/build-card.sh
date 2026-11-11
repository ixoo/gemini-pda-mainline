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
#   - Umbriel built from ./umbriel's pinned commit, and gemini-base built from
#     ./gemini-base, both installed, with gemini-base's units enabled, and the GNSS
#     daemon built from ../2026-11-10-gemini-gnss-daemon, installed but not enabled;
#   - root locked and the default alarm user removed; sshd masked;
#   - the stock systemd-firstboot.service masked: it asks on /dev/console, which is
#     the serial port here, and holds sysinit.target until answered (R1);
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
# Everything runs in a private mount namespace: otherwise the card's mounts
# propagate into long-running services' namespaces, and their copies keep the
# loop device attached after the build (seen 2026-11-06).
if [ -z "${BUILD_CARD_PRIVATE_NS:-}" ]; then
	exec env BUILD_CARD_PRIVATE_NS=1 unshare --mount --propagation private "$0" "$@"
fi
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

here=$(cd "$(dirname "$0")" && pwd)
# Umbriel, gemini-base's compositor, from ./umbriel's pinned upstream commit: no repository
# ships it. Built by makepkg as nobody on the image's disk, since the build is larger
# than /run; its build tools go in as dependencies and leave again once nothing needs them.
umbriel_makedeps=(base-devel meson ninja nlohmann-json pkgconf wayland-protocols)
umbriel_deps=$(sed -n "/^depends=(/,/)/p" "$here/umbriel/PKGBUILD" | tr -d "()'" | sed 's/^depends=//')
# shellcheck disable=SC2086 # the dependency list splits on purpose
in_root pacman --gpgdir /run/pacman-gnupg -S --needed --asdeps --noconfirm --noprogressbar \
	"${umbriel_makedeps[@]}" $umbriel_deps >>"$work/pacman.log" 2>&1 ||
	{ tail -20 "$work/pacman.log" >&2; echo "build-card: Umbriel's dependencies failed" >&2; exit 1; }
ubuild=$mnt/var/tmp/umbriel-build
mkdir -p "$ubuild/src" "$ubuild/out"
cp "$here"/umbriel/* "$ubuild/src/"
chown -R 65534:65534 "$ubuild"
chroot "$mnt" /usr/bin/runuser -u nobody -- /usr/bin/env -i PATH=/usr/bin HOME=/var/tmp/umbriel-build LANG=C \
	PKGDEST=/var/tmp/umbriel-build/out sh -c 'cd /var/tmp/umbriel-build/src && makepkg --nodeps --noprogressbar' \
	>"$work/umbriel-makepkg.log" 2>&1 ||
	{ tail -30 "$work/umbriel-makepkg.log" >&2; echo "build-card: building Umbriel failed" >&2; exit 1; }
umbriel_pkg=$(ls "$ubuild"/out/umbriel-*.pkg.tar.*)
cp "$umbriel_pkg" "$out/"
umbriel_sha=$(sha256sum "$umbriel_pkg" | cut -d' ' -f1)
in_root pacman --gpgdir /run/pacman-gnupg -U --noconfirm --noprogressbar "/var/tmp/umbriel-build/out/${umbriel_pkg##*/}" >>"$work/pacman.log" 2>&1 ||
	{ tail -20 "$work/pacman.log" >&2; echo "build-card: installing Umbriel failed" >&2; exit 1; }
rm -rf "$ubuild"

# gemini-base (step 3), built from this directory with the station's audio-start and
# display-start staged beside it, by makepkg as nobody; fakeroot only for the build.
station=$here/../2026-10-30-mainline-dev-station/initramfs
build=$mnt/run/build
mkdir -p "$build/src" "$build/out"
cp "$here"/gemini-base/* "$station/audio-start" "$station/display-start" "$build/src/"
chown -R 65534:65534 "$build"
# gemini-base's makedepends: perl and kbd come with the tarball; xkeyboard-config stays,
# since the compositor needs it too.
in_root pacman --gpgdir /run/pacman-gnupg -S --needed --noconfirm --noprogressbar fakeroot perl kbd xkeyboard-config >>"$work/pacman.log" 2>&1
chroot "$mnt" /usr/bin/runuser -u nobody -- /usr/bin/env -i PATH=/usr/bin HOME=/run/build LANG=C \
	PKGDEST=/run/build/out sh -c 'cd /run/build/src && makepkg --nodeps --noprogressbar' >"$work/makepkg.log" 2>&1 ||
	{ tail -20 "$work/makepkg.log" >&2; echo "build-card: makepkg failed" >&2; exit 1; }
base_pkg=$(ls "$build"/out/gemini-base-*.pkg.tar.*)
cp "$base_pkg" "$out/"
base_sha=$(sha256sum "$base_pkg" | cut -d' ' -f1)
in_root pacman --gpgdir /run/pacman-gnupg -U --noconfirm --noprogressbar "/run/build/out/${base_pkg##*/}" >>"$work/pacman.log" 2>&1 ||
	{ tail -20 "$work/pacman.log" >&2; echo "build-card: installing gemini-base failed" >&2; exit 1; }
# The GNSS daemon (owner, 2026-11-10: "gnss userland to produce a fix and position"), the
# GNSS session's package, built the same way from its own directory. Not enabled: starting
# gnss-mt6797.service switches the GPS radio on.
gnss=$here/../2026-11-10-gemini-gnss-daemon
mkdir -p "$build/gnss"
cp "$gnss/PKGBUILD" "$gnss/gnss-mt6797d" "$gnss/gnss-mt6797.service" "$gnss/geoclue-gnss-mt6797.conf" "$build/gnss/"
chown -R 65534:65534 "$build/gnss"
chroot "$mnt" /usr/bin/runuser -u nobody -- /usr/bin/env -i PATH=/usr/bin HOME=/run/build LANG=C \
	PKGDEST=/run/build/out sh -c 'cd /run/build/gnss && makepkg --nodeps --noprogressbar' >"$work/gnss-makepkg.log" 2>&1 ||
	{ tail -20 "$work/gnss-makepkg.log" >&2; echo "build-card: building the GNSS daemon failed" >&2; exit 1; }
gnss_pkg=$(ls "$build"/out/gnss-mt6797d-*.pkg.tar.*)
cp "$gnss_pkg" "$out/"
gnss_sha=$(sha256sum "$gnss_pkg" | cut -d' ' -f1)
in_root pacman --gpgdir /run/pacman-gnupg -U --noconfirm --noprogressbar "/run/build/out/${gnss_pkg##*/}" >>"$work/pacman.log" 2>&1 ||
	{ tail -20 "$work/pacman.log" >&2; echo "build-card: installing the GNSS daemon failed" >&2; exit 1; }
in_root pacman -Rns --noconfirm fakeroot >>"$work/pacman.log" 2>&1 || true
rm -rf "$build"
# The build tools that nothing installed needs now (Umbriel's and gemini-base's), even as
# an optional dependency (base-devel is pacman's).
mapfile -t orphans < <(in_root pacman -Qdttq || true)
[ "${#orphans[@]}" -eq 0 ] || in_root pacman -Rns --noconfirm "${orphans[@]}" >>"$work/pacman.log" 2>&1
in_root systemctl enable -q gemini-modules.service gemini-audio.service gemini-display.service \
	gemini-wifi.service gemini-firstboot.service iwd.service systemd-pstore.service bluetooth.service \
	gpsd.socket
# bluetoothd runs from boot so Noctalia sees the adapter, but bluez powers every adapter it
# finds unless AutoEnable is false; the owner turns the radio on (owner, 2026-11-08).
# bluez owns main.conf and has no drop-in directory, so the image's copy is edited.
sed -i 's/^#\?AutoEnable=.*/AutoEnable=false/' "$mnt/etc/bluetooth/main.conf"
grep -qx 'AutoEnable=false' "$mnt/etc/bluetooth/main.conf" ||
	{ echo "build-card: AutoEnable not set in bluetooth/main.conf" >&2; exit 1; }
in_root systemctl set-default -q multi-user.target

in_root gpgconf --homedir /run/pacman-gnupg --kill all
# gpgconf doesn't stop every helper the keyring started, and a survivor keeps
# the card's loop device attached until it exits.
if pgrep -f pacman-gnupg >"$work/gpg-left.txt"; then
	echo "build-card: stopping $(wc -l <"$work/gpg-left.txt") keyring helpers: $(pgrep -af pacman-gnupg | awk '{print $2}' | sort -u | tr '\n' ' ')" >&2
	pkill -f pacman-gnupg
	sleep 1
fi
rm -f "$resolv"
if [ -e "$work/resolv.conf.saved" ] || [ -L "$work/resolv.conf.saved" ]; then mv "$work/resolv.conf.saved" "$resolv"; fi
rm -rf "$mnt"/var/cache/pacman/pkg/*

in_root passwd -q -l root
if in_root id alarm >/dev/null 2>&1; then in_root userdel -r alarm 2>/dev/null; fi
in_root systemctl disable -q sshd.service
in_root systemctl mask -q sshd.service
in_root systemctl mask -q systemd-firstboot.service
rm -f "$mnt"/etc/ssh/ssh_host_*
echo uninitialized >"$mnt/etc/machine-id"
# The tarball's LANG=C makes foot warn and fall back; C.UTF-8 needs no locale-gen.
echo LANG=C.UTF-8 >"$mnt/etc/locale.conf"
rm -f "$mnt/var/lib/systemd/random-seed"
# No /nvdata: stage 1 mounts nvdata into the root only where that directory exists.
mkdir -p "$mnt/usr/lib/modules"
echo 'PARTLABEL=gemini-arch / ext4 rw,noatime 0 1' >>"$mnt/etc/fstab"

! in_root pacman -Qq | grep -qE '^(linux-aarch64|linux-firmware|mkinitcpio)' ||
	{ echo "build-card: an ignored package came back" >&2; exit 1; }
packages=$(in_root pacman -Q | sha256sum | cut -d' ' -f1)
count=$(in_root pacman -Qq | wc -l)
systemd=$(in_root pacman -Q systemd | cut -d' ' -f2)
in_root pacman -Q >"$out/packages.txt"
# Only the directories that exist are searched: WIFI.storage is copied in on the
# device by gemian-firmware, never at build time.
[ ! -e "$mnt/nvdata" ] || { echo "build-card: the root has /nvdata" >&2; exit 1; }
private=$(find "$mnt/usr/lib/firmware" "$mnt/root" "$mnt/etc/ssh" -maxdepth 4 -type f \
	\( -name 'ssh_host_*' -o -name 'WIFI*' -o -name 'WMT_SOC*' -o -name 'authorized_keys' \) \
	2>/dev/null | wc -l || true)
[ "$private" -eq 0 ] || { echo "build-card: private files in the root" >&2; exit 1; }
used=$(df -B1 --output=used "$mnt" | tail -1 | tr -d ' ')

for m in run dev sys proc; do umount -R "$mnt/$m"; done
umount "$mnt"
[ -z "$(mounts_under "$work")" ] || { echo "build-card: mounts remain under $work" >&2; exit 1; }
e2fsck -fn "${loop}p1" >/dev/null
# Flush the loop device and wait until it is really gone before hashing: a
# detach is deferred while udev still holds it, and its last writes then reach
# the file after an early hash (seen once, 2026-11-06).
sync
blockdev --flushbufs "${loop}p1" "$loop"
udevadm settle
losetup -d "$loop"
detach_wait=0
while losetup -j "$image" | grep -q .; do
	[ "$detach_wait" -ge 300 ] && { echo "build-card: $loop still attached after 300 s" >&2; exit 1; }
	sleep 1
	detach_wait=$((detach_wait + 1))
done
loop=
sync
image_sha=$(sha256sum "$image" | cut -d' ' -f1)
sleep 2
sync
[ "$(sha256sum "$image" | cut -d' ' -f1)" = "$image_sha" ] || { echo "build-card: image changed after detach" >&2; exit 1; }
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
  "umbriel_sha256": "$umbriel_sha",
  "gemini_base_sha256": "$base_sha",
  "gnss_mt6797d_sha256": "$gnss_sha",
  "systemd": "$systemd",
  "root_bytes_used": $used,
  "image_size": "$size",
  "detach_wait_s": $detach_wait,
  "image_sha256": "$image_sha"
}
EOF
cat "$out/card.json"
