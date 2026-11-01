#!/bin/sh
# SPDX-License-Identifier: MIT
# Usage: run-tests.sh PREPARED_LINUX_SOURCE
# Compiles the fixtures against the actual engine and parser headers.
set -eu
src=$1
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
# The kernel-independent framing helpers, verbatim from the shared header.
sed -n '/^\/\* Selected Gemian full-mode/,/^\/\* Selected WMT command limit/p' \
    "$src/drivers/soc/mediatek/mt6797-wmt.h" > "$work/mt6797-wmt.h"
[ -s "$work/mt6797-wmt.h" ]
cp "$src/drivers/soc/mediatek/mt6797-stp-engine.h" "$src/drivers/gnss/mt6797-gfns.h" "$work/"
for t in test-stp-engine test-gfns; do
    cc -std=gnu11 -Wall -Wextra -Werror -fsanitize=address,undefined \
        -I"$work" "$here/$t.c" -o "$work/$t"
    "$work/$t"
done
