#!/bin/sh
# SPDX-License-Identifier: MIT
# Build Mesa's Panfrost GLES driver and gpu-gles for the station RAM root, into
# OUT with their libraries, to run from /run through the bundled loader.
# Run on a Buildbox. Usage: build-mesa.sh WORKDIR SOURCE_DIR
set -eu

MESA=mesa-24.3.4
MESA_SHA=e641ae27191d387599219694560d221b7feaa91c900bcec46bf444218ed66025
DRM=libdrm-2.4.124
DRM_SHA=ac36293f61ca4aafaf4b16a2a7afff312aa4f5c37c9fbd797de9e3c0863ca379
ZLIB=zlib-1.3.1
ZLIB_SHA=9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23
HOST=aarch64-linux-gnu

[ "$#" -eq 2 ] || { echo "usage: $0 WORKDIR SOURCE_DIR" >&2; exit 2; }
SRC=$(cd "$2" && pwd)
mkdir -p "$1"
cd "$1"
W=$(pwd)
[ -e "$MESA.tar.xz" ] || curl -fsSLo "$MESA.tar.xz" "https://archive.mesa3d.org/$MESA.tar.xz"
[ -e "$DRM.tar.xz" ] || curl -fsSLo "$DRM.tar.xz" "https://dri.freedesktop.org/libdrm/$DRM.tar.xz"
[ -e "$ZLIB.tar.gz" ] || curl -fsSLo "$ZLIB.tar.gz" "https://zlib.net/fossils/$ZLIB.tar.gz"
echo "$MESA_SHA  $MESA.tar.xz" | sha256sum -c -
echo "$DRM_SHA  $DRM.tar.xz" | sha256sum -c -
echo "$ZLIB_SHA  $ZLIB.tar.gz" | sha256sum -c -
rm -rf "$MESA" "$DRM" "$ZLIB" prefix out build-*
tar xf "$MESA.tar.xz"
tar xf "$DRM.tar.xz"
tar xf "$ZLIB.tar.gz"

python3 -m venv venv
venv/bin/pip -q install meson==1.5.2 mako==1.3.5 pyyaml==6.0.2
PATH=$W/venv/bin:$PATH

cat > cross.txt <<EOF
[binaries]
c = '$HOST-gcc'
cpp = '$HOST-g++'
ar = '$HOST-ar'
strip = '$HOST-strip'
pkg-config = 'pkg-config'
[host_machine]
system = 'linux'
cpu_family = 'aarch64'
cpu = 'cortex-a53'
endian = 'little'
EOF
PKG_CONFIG_LIBDIR=$W/prefix/lib/pkgconfig
PKG_CONFIG_PATH=
export PKG_CONFIG_LIBDIR PKG_CONFIG_PATH

(cd "$ZLIB" && CC=$HOST-gcc CFLAGS='-O2 -fPIC' ./configure --static --prefix="$W/prefix" >/dev/null && make -j32 install >/dev/null)
meson setup build-drm "$DRM" --cross-file cross.txt --prefix="$W/prefix" --libdir=lib \
    --buildtype=release -Dintel=disabled -Dradeon=disabled -Damdgpu=disabled \
    -Dnouveau=disabled -Dvmwgfx=disabled -Dtests=false -Dman-pages=disabled -Dcairo-tests=disabled
ninja -C build-drm install >/dev/null
meson setup build-mesa "$MESA" --cross-file cross.txt --prefix="$W/prefix" --libdir=lib \
    --buildtype=release -Dgallium-drivers=panfrost -Dvulkan-drivers= -Dglx=disabled \
    -Dplatforms= -Degl=enabled -Dgbm=enabled -Dgles1=disabled -Dgles2=enabled -Dopengl=true \
    -Dglvnd=disabled -Dllvm=disabled -Dzstd=disabled -Dxmlconfig=disabled -Dshared-glapi=enabled \
    -Dvalgrind=disabled -Dlibunwind=disabled -Dgallium-vdpau=disabled -Dgallium-va=disabled \
    -Dgallium-xa=disabled -Dgallium-nine=false -Dgallium-opencl=disabled -Dbuild-tests=false
ninja -C build-mesa install >/dev/null

mkdir -p out
$HOST-gcc -Wall -Wextra -O2 -I"$W/prefix/include" -o out/gpu-gles "$SRC/gpu-gles.c" \
    -L"$W/prefix/lib" -Wl,-rpath-link,"$W/prefix/lib" -lEGL -lGLESv2
for lib in libEGL.so.1 libGLESv2.so.2 libgbm.so.1 libglapi.so.0 libdrm.so.2 libexpat.so.1 \
           libgallium-24.3.4.so; do
    cp -L "prefix/lib/$lib" out/
done
for lib in ld-linux-aarch64.so.1 libc.so.6 libm.so.6 libdl.so.2 libpthread.so.0 librt.so.1 \
           libstdc++.so.6 libgcc_s.so.1; do
    cp -L "/usr/$HOST/lib/$lib" out/
done
$HOST-strip -s out/gpu-gles out/lib*.so*
(cd out && find . -type f | sort | xargs sha256sum > ../SHA256SUMS)
mv SHA256SUMS out/
du -sh out
