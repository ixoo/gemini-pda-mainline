#!/bin/sh
# SPDX-License-Identifier: MIT
# Build static aarch64 amixer and aplay (arecord is aplay under another name)
# for the station RAM root, which has neither. Run on a Buildbox.
# Usage: build-alsa-tools.sh WORKDIR
set -eu

LIB=alsa-lib-1.2.12
UTILS=alsa-utils-1.2.12
LIB_SHA=4868cd908627279da5a634f468701625be8cc251d84262c7e5b6a218391ad0d2
UTILS_SHA=98bc6677d0c0074006679051822324a0ab0879aea558a8f68b511780d30cd924
URL=https://www.alsa-project.org/files/pub
HOST=aarch64-linux-gnu

[ "$#" -eq 1 ] || { echo "usage: $0 WORKDIR" >&2; exit 2; }
mkdir -p "$1"
cd "$1"
[ -e "$LIB.tar.bz2" ] || curl -fsSLo "$LIB.tar.bz2" "$URL/lib/$LIB.tar.bz2"
[ -e "$UTILS.tar.bz2" ] || curl -fsSLo "$UTILS.tar.bz2" "$URL/utils/$UTILS.tar.bz2"
echo "$LIB_SHA  $LIB.tar.bz2" | sha256sum -c -
echo "$UTILS_SHA  $UTILS.tar.bz2" | sha256sum -c -
rm -rf "$LIB" "$UTILS" prefix out
tar xf "$LIB.tar.bz2"
tar xf "$UTILS.tar.bz2"
prefix=$PWD/prefix

(cd "$LIB" && ./configure --host=$HOST --prefix="$prefix" \
	--enable-static --disable-shared --disable-ucm --disable-topology \
	--disable-rawmidi --disable-hwdep --disable-seq --disable-python \
	>/dev/null && make -j8 install >/dev/null)
# libtool drops -static; only -all-static reaches the linker.
(cd "$UTILS" && CPPFLAGS=-I"$prefix/include" LDFLAGS="-L$prefix/lib" \
	./configure --host=$HOST --with-alsa-prefix="$prefix/lib" \
	--with-alsa-inc-prefix="$prefix/include" --disable-alsamixer \
	--disable-alsaconf --disable-alsaloop --disable-alsaucm --disable-alsatest \
	--disable-bat --disable-topology --disable-nls --disable-rst2man \
	--disable-xmlto >/dev/null &&
	make -C amixer LDFLAGS="-L$prefix/lib -all-static" >/dev/null &&
	make -C aplay LDFLAGS="-L$prefix/lib -all-static" >/dev/null)
mkdir -p out/bin
cp "$UTILS/amixer/amixer" "$UTILS/aplay/aplay" out/bin/
$HOST-strip out/bin/amixer out/bin/aplay
ln -s aplay out/bin/arecord
cp -R "$prefix/share/alsa" out/alsa
sha256sum out/bin/amixer out/bin/aplay
for t in amixer aplay; do
	file "out/bin/$t" | grep -q "statically linked" || { echo "$t is not static" >&2; exit 1; }
done
