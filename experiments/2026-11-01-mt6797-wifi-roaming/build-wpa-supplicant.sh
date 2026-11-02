#!/bin/sh
# SPDX-License-Identifier: MIT
# Build a static wpa_supplicant 2.11 with bgscan for the station's RAM root, whose
# own build has none. Run on an aarch64 machine with gcc, make and libnl's static
# libraries. Usage: build-wpa-supplicant.sh <empty work directory>
set -eu
TAG=hostap_2_11
COMMIT=d945ddd368085f255e68328f2d3b020ceea359af
cd "$1"
git clone -q --depth 1 -b "$TAG" https://w1.fi/hostap.git hostap
cd hostap
[ "$(git rev-parse HEAD)" = "$COMMIT" ]
cd wpa_supplicant
cat > .config <<C
CONFIG_DRIVER_NL80211=y
CONFIG_LIBNL32=y
CONFIG_CTRL_IFACE=y
CONFIG_BGSCAN_SIMPLE=y
CONFIG_TLS=internal
CONFIG_INTERNAL_LIBTOMMATH=y
CONFIG_IEEE80211N=y
CONFIG_IEEE80211AC=y
CONFIG_WNM=y
CONFIG_HT_OVERRIDES=y
C
LDFLAGS=-static make -j8 wpa_supplicant wpa_cli
strip wpa_supplicant wpa_cli
sha256sum wpa_supplicant wpa_cli
./wpa_supplicant -v | head -1
