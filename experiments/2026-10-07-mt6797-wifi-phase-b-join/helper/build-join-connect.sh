#!/bin/sh
# SPDX-License-Identifier: MIT
# Reproducible static aarch64 build of the join-connect helper on Buildbox-1.
# Usage: build-join-connect.sh OUTPUT_DIR ; prints the binary's SHA-256.
set -eu
here=$(cd -- "$(dirname -- "$0")" && pwd -P)
out=${1:?output directory}
mkdir -p "$out"
aarch64-linux-gnu-gcc -std=c11 -O2 -Wall -Wextra -Werror -static -s \
	-fno-asynchronous-unwind-tables -ffile-prefix-map="$here"=. \
	-Wl,--build-id=none -o "$out/join-connect" "$here/join-connect.c"
sha256sum "$out/join-connect"
