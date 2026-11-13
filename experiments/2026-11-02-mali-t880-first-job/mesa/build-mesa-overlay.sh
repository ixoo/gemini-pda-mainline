#!/bin/bash
# SPDX-License-Identifier: MIT
# Build Mesa's Panfrost EGL/GLES/GL driver, patched, in a throwaway Arch Linux
# ARM chroot, as an overlay under /opt/mesa-overlay for the station's Arch root.
# Clients opt in per process; the installed Mesa stays untouched. Also
# carries panquick, Mesa's GPU counter sampler.
# Run as root in the aarch64 dev VM:
#   ALARM_TARBALL=ArchLinuxARM-aarch64-latest.tar.gz build-mesa-overlay.sh ROOT OUT PATCH...
set -euo pipefail
if [ -z "${PRIV_NS:-}" ]; then
	exec env PRIV_NS=1 unshare --mount --propagation private "$0" "$@"
fi
MESA=mesa-26.2.6
MESA_SHA=b9436b3e1a8be76fbd4823dc884f90596ab7c6ac5e1867a305e66ffccfb31a92
tarball=${ALARM_TARBALL:?set ALARM_TARBALL to the Arch Linux ARM aarch64 rootfs tarball}
root=$1 out=$2
shift 2
patches=("$@")
mkdir -p "$root" "$out"
[ -e "$root/etc/arch-release" ] || bsdtar -xpf "$tarball" -C "$root"
# Only the device nodes pacman and the build need; no /dev bind mount.
for n in "null 1 3" "zero 1 5" "random 1 8" "urandom 1 9" "tty 5 0"; do
	# shellcheck disable=SC2086 # split "name major minor"
	set -- $n
	[ -e "$root/dev/$1" ] || mknod -m 666 "$root/dev/$1" c "$2" "$3"
done
mount --bind "$root" "$root"
ln -sfn /proc/self/fd "$root/dev/fd"
mount -t proc proc "$root/proc"
rm -f "$root/etc/resolv.conf"
grep "^nameserver" /run/systemd/resolve/resolv.conf >"$root/etc/resolv.conf"
sed -i 's/^#\?DisableSandbox.*/DisableSandbox/' "$root/etc/pacman.conf"
grep -q '^DisableSandbox' "$root/etc/pacman.conf" || sed -i '/^\[options\]/a DisableSandbox' "$root/etc/pacman.conf"
rm -rf "$root/build" && mkdir -p "$root/build"
for p in "${patches[@]}"; do cp "$p" "$root/build/"; done
# shellcheck disable=SC2016 # expanded inside the chroot
chroot "$root" /bin/bash -c '
set -e
pacman-key --init >/dev/null 2>&1
pacman-key --populate archlinuxarm >/dev/null 2>&1
pacman -Rdd --noconfirm $(pacman -Qq | grep -E "^(linux-aarch64|linux-firmware)") >/dev/null 2>&1 || true
pacman -Syu --noconfirm --needed base-devel meson python-mako python-yaml \
	python-packaging python-ply libdrm wayland wayland-protocols libglvnd \
	expat zstd libelf llvm clang libclc spirv-llvm-translator spirv-tools \
	glslang mesa >/tmp/pacman.log 2>&1 || { tail -30 /tmp/pacman.log; exit 1; }
pacman -Q mesa libdrm llvm clang libglvnd wayland gcc
'
chroot "$root" /bin/bash -c "
set -e
cd /build
curl -fsSLo $MESA.tar.xz https://archive.mesa3d.org/$MESA.tar.xz
echo '$MESA_SHA  $MESA.tar.xz' | sha256sum -c -
tar xf $MESA.tar.xz
cd $MESA
for p in /build/*.patch; do patch -p1 <\"\$p\"; done
meson setup b --prefix=/opt/mesa-overlay --buildtype=release \
	-Dplatforms=wayland -Dgallium-drivers=panfrost -Dvulkan-drivers= \
	-Dglvnd=enabled -Degl=enabled -Dgbm=enabled -Dgles1=disabled \
	-Dgles2=enabled -Dopengl=true -Dglx=disabled -Dllvm=enabled \
	-Dvideo-codecs= -Dgallium-va=disabled \
	-Dgallium-rusticl=false -Dtools=panfrost -Dvalgrind=disabled \
	-Dlibunwind=disabled -Dlmsensors=disabled >/build/meson.log
ninja -C b >/build/ninja.log
DESTDIR=/build/dest ninja -C b install >/build/install.log
# panquick (named GPU counters) is built but not installed by Mesa.
install -Dm755 b/src/panfrost/perf/panquick /build/dest/opt/mesa-overlay/bin/panquick
"
tar -C "$root/build/dest" --owner=0 --group=0 -cJf "$out/mesa-overlay.tar.xz" opt
sha256sum "$out/mesa-overlay.tar.xz"
umount "$root/proc"
umount "$root"
