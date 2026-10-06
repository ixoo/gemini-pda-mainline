#!/bin/sh
# SPDX-License-Identifier: MIT
# Derive the C2b candidate DTB: the board-services candidate DTB plus I2C0
# enabled and one BQ25896 node at 0x6b with a verified charge start.
# Values sit exactly on driver table steps: 4.192 V (the step at or below
# 4.2 V), 512 mA charge, 128 mA precharge and termination, 3.5 V minimum
# system, 5.126 V boost (chip default, OTG unused), 500 mA boost limit and a
# verified 500 mA input limit. The interrupt is EINT158 (GPIO246, vendor
# "CHR_STAT"); the driver requests it falling-edge.
# Usage: c2b-dt.sh PARENT.dtb OUTPUT.dtb
set -eu

I2C=/i2c@11007000
NODE=$I2C/charger@6b
PIO=/pinctrl@10005000
EINT=158
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

# Preconditions: I2C0 is the MT6797 controller, disabled; no node at 0x6b;
# the pin controller is a two-cell interrupt controller.
fdtget -t s "$dtb" "$I2C" compatible | tr ' ' '\n' | grep -qx 'mediatek,mt6797-i2c'
[ "$(fdtget -t s "$dtb" "$I2C" status)" = disabled ]
if fdtget "$dtb" "$NODE" compatible >/dev/null 2>&1; then exit 1; fi
fdtget "$dtb" "$PIO" interrupt-controller >/dev/null
[ "$(fdtget -t u "$dtb" "$PIO" '#interrupt-cells')" = 2 ]
pio=$(fdtget -t u "$dtb" "$PIO" phandle)

fdtput -t s "$dtb" "$I2C" status okay
fdtput -c "$dtb" "$NODE"
fdtput -t s "$dtb" "$NODE" compatible ti,bq25896 ti,bq25890
fdtput -t x "$dtb" "$NODE" reg 6b
fdtput -t u "$dtb" "$NODE" interrupt-parent "$pio"
fdtput -t u "$dtb" "$NODE" interrupts "$EINT" 2
fdtput -t u "$dtb" "$NODE" ti,battery-regulation-voltage 4192000
fdtput -t u "$dtb" "$NODE" ti,charge-current 512000
fdtput -t u "$dtb" "$NODE" ti,termination-current 128000
fdtput -t u "$dtb" "$NODE" ti,precharge-current 128000
fdtput -t u "$dtb" "$NODE" ti,minimum-sys-voltage 3500000
fdtput -t u "$dtb" "$NODE" ti,boost-voltage 5126000
fdtput -t u "$dtb" "$NODE" ti,boost-max-current 500000
fdtput "$dtb" "$NODE" linux,skip-reset
fdtput "$dtb" "$NODE" linux,verified-charge-start
fdtput -t u "$dtb" "$NODE" linux,verified-input-current-limit-microamp 500000

# The decompiled difference must be exactly these edits.
dtc -q -I dtb -O dts -s "$work/board.dtb" > "$work/board.dts"
dtc -q -I dtb -O dts -s "$dtb" > "$work/out.dts"
diff "$work/board.dts" "$work/out.dts" | grep '^[<>]' |
	sed 's/^\([<>]\)[[:space:]]*/\1 /; s/[[:space:]]*$//' | LC_ALL=C sort > "$work/delta"
hex() { printf '0x%02x' "$1"; }
LC_ALL=C sort > "$work/expected" <<DELTA
< status = "disabled";
> status = "okay";
> charger@6b {
> compatible = "ti,bq25896\\0ti,bq25890";
> reg = <0x6b>;
> interrupt-parent = <$(hex "$pio")>;
> interrupts = <$(hex "$EINT") 0x02>;
> ti,battery-regulation-voltage = <$(hex 4192000)>;
> ti,charge-current = <$(hex 512000)>;
> ti,termination-current = <$(hex 128000)>;
> ti,precharge-current = <$(hex 128000)>;
> ti,minimum-sys-voltage = <$(hex 3500000)>;
> ti,boost-voltage = <$(hex 5126000)>;
> ti,boost-max-current = <$(hex 500000)>;
> linux,skip-reset;
> linux,verified-charge-start;
> linux,verified-input-current-limit-microamp = <$(hex 500000)>;
> };
>
DELTA
cmp -s "$work/delta" "$work/expected" || {
	echo "unexpected DT delta:" >&2
	diff "$work/expected" "$work/delta" >&2 || true
	exit 1
}
cp "$dtb" "$output"
sha256sum "$output"
