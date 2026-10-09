#!/bin/sh
# SPDX-License-Identifier: MIT
# Reproducible static aarch64 build of wpa_supplicant 2.11 with libnl 3.11.0.
# Usage: build-wpa-supplicant.sh SOURCES_DIR OUTPUT_DIR
#   SOURCES_DIR holds wpa_supplicant-2.11.tar.gz and libnl-3.11.0.tar.gz,
#   verified against the pinned SHA-256 values below before anything is built.
set -eu
here=$(cd -- "$(dirname -- "$0")" && pwd -P)
src=${1:?sources directory}
out=${2:?output directory}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$src"
printf '%s  %s\n' 912ea06f74e30a8e36fbb68064d6cdff218d8d591db0fc5d75dee6c81ac7fc0a wpa_supplicant-2.11.tar.gz \
	2a56e1edefa3e68a7c00879496736fdbf62fc94ed3232c0baba127ecfa76874d libnl-3.11.0.tar.gz | sha256sum -c -
tar xzf libnl-3.11.0.tar.gz -C "$work"
tar xzf wpa_supplicant-2.11.tar.gz -C "$work"
cd "$work/libnl-3.11.0"
./configure --host=aarch64-linux-gnu --prefix="$work/stage" --disable-shared --enable-static \
	--disable-cli --disable-pthreads --disable-debug CC=aarch64-linux-gnu-gcc \
	CFLAGS="-O2 -ffile-prefix-map=$work=." > "$work/libnl.log" 2>&1
make -j"$(nproc)" >> "$work/libnl.log" 2>&1
make install >> "$work/libnl.log" 2>&1
cd "$work/wpa_supplicant-2.11/wpa_supplicant"
grep -v "^# SPDX" "$here/wpa_supplicant.config" > .config
make -j"$(nproc)" CC=aarch64-linux-gnu-gcc \
	EXTRA_CFLAGS="-O2 -ffile-prefix-map=$work=. -I$work/stage/include/libnl3 -fno-asynchronous-unwind-tables" \
	LDFLAGS="-static -L$work/stage/lib -Wl,--build-id=none" LIBS="-lnl-genl-3 -lnl-3" \
	wpa_supplicant > "$work/wpa.log" 2>&1 || { tail -20 "$work/wpa.log"; exit 1; }
aarch64-linux-gnu-strip -s wpa_supplicant
mkdir -p "$out"
cp wpa_supplicant "$out/wpa_supplicant"
sha256sum "$out/wpa_supplicant"
