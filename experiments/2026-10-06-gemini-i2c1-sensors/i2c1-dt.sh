#!/bin/sh
# SPDX-License-Identifier: MIT
# Derive the I2C1 sensors H1 candidate DTB: the board-services candidate DTB
# plus I2C1 (/i2c@11008000) and its existing BMI160 child at 0x69 enabled.
# No pinctrl state: the loader applies the board DWS defaults, which put
# GPIO55/56 in mode 1 (SCL1_0/SDA1_0).
# Usage: i2c1-dt.sh PARENT.dtb OUTPUT.dtb
set -eu

I2C=/i2c@11008000
IMU=$I2C/bmi160@69
here=$(cd "$(dirname "$0")" && pwd)
board="$here/../2026-10-06-mt6797-board-only-profile/board-services-dt.sh"

[ "$#" -eq 2 ] || { echo "usage: $0 PARENT.dtb OUTPUT.dtb" >&2; exit 2; }
output=$2
if [ -e "$output" ] || [ -L "$output" ]; then
	echo "refusing to overwrite $output or follow a symlink" >&2
	exit 1
fi

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
"$board" "$1" "$work/board.dtb" >/dev/null
cp "$work/board.dtb" "$work/out.dtb"
dtb=$work/out.dtb

fdtget -t s "$dtb" "$I2C" compatible | tr ' ' '\n' | grep -qx 'mediatek,mt6797-i2c'
[ "$(fdtget -t s "$dtb" "$I2C" status)" = disabled ]
[ "$(fdtget -t s "$dtb" "$IMU" compatible)" = bosch,bmi160 ]
[ "$(fdtget -t s "$dtb" "$IMU" status)" = disabled ]
[ "$(fdtget -t x "$dtb" "$IMU" reg)" = 69 ]
# Exactly one child, so enabling the bus enables nothing else.
[ "$(fdtget -l "$dtb" "$I2C" | wc -l)" = 1 ]

fdtput -t s "$dtb" "$I2C" status okay
fdtput -t s "$dtb" "$IMU" status okay

dtc -q -I dtb -O dts -s "$work/board.dtb" > "$work/board.dts"
dtc -q -I dtb -O dts -s "$dtb" > "$work/out.dts"
diff "$work/board.dts" "$work/out.dts" | grep '^[<>]' |
	sed 's/^\([<>]\)[[:space:]]*/\1 /; s/[[:space:]]*$//' | LC_ALL=C sort > "$work/delta"
LC_ALL=C sort > "$work/expected" <<'DELTA'
< status = "disabled";
< status = "disabled";
> status = "okay";
> status = "okay";
DELTA
cmp -s "$work/delta" "$work/expected" || {
	echo "unexpected DT delta:" >&2
	diff "$work/expected" "$work/delta" >&2 || true
	exit 1
}
cp "$dtb" "$output"
sha256sum "$output"
