#!/bin/sh
# SPDX-License-Identifier: MIT
# Usage: run-tests.sh PREPARED_LINUX_SOURCE
# Compiles the fixtures against the actual engine, H:4 and driver sources.
set -eu
src=$1
here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
for h in stp-full stp-full-link stp-full-task stp-full-stream mt6797-stp-engine; do
    cp "$src/drivers/soc/mediatek/$h.h" "$work/"
done
cp "$src/drivers/bluetooth/btmt6797-h4.h" "$work/"
# The IRQ-side receive callback, verbatim from the driver.
sed -n '/^static int btmt6797_rx(void \*context/,/^}/p' \
    "$src/drivers/bluetooth/btmt6797.c" > "$work/btmt6797-rx.inc"
[ -s "$work/btmt6797-rx.inc" ]
for t in test-stp-engine test-bt-h4 test-bt-rx; do
    cc -std=gnu11 -Wall -Wextra -Werror -fsanitize=address,undefined \
        -I"$work" "$here/$t.c" -o "$work/$t"
    setarch "$(uname -m)" -R "$work/$t"
done
