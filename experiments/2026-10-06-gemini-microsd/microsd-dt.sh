#!/bin/sh
# SPDX-License-Identifier: MIT
# Derive the microSD H3 candidate DTB: the board-services candidate DTB plus
#   regulators   ldo-vmch and ldo-vmc, each pinned at 3.0 V (the vendor value);
#   pinctrl      one pinmux-only state: GPIO129-134 in mode 1 (MSDC1), no
#                bias or drive (mainline lacks those MT6797 fields);
#   /mmc@11240000  okay, 4-bit, at most 50 MHz, high-speed, no 1.8 V, no
#                write-protect pin, card detect on GPIO67 active high, VMCH as
#                vmmc and VMC as vqmmc; the one pad state serves "default" and
#                "state_uhs" (mtk-sd requires both; UHS is never used).
# Usage: microsd-dt.sh PARENT.dtb OUTPUT.dtb
set -eu

PIO=/pinctrl@10005000
MMC=/mmc@11240000
REGS=/pwrap@1000d000/pmic/regulators
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

# Preconditions.
[ "$(fdtget -t s "$dtb" "$MMC" compatible)" = mediatek,mt6797-mmc ]
[ "$(fdtget -t s "$dtb" "$MMC" status)" = disabled ]
if fdtget "$dtb" "$MMC" pinctrl-0 >/dev/null 2>&1; then exit 1; fi
[ "$(fdtget -t s "$dtb" "$REGS" compatible)" = mediatek,mt6351-regulator ]
for n in ldo-vmch ldo-vmc; do
	if fdtget "$dtb" "$REGS/$n" regulator-name >/dev/null 2>&1; then exit 1; fi
done
if fdtget "$dtb" "$PIO/msdc1-pins" phandle >/dev/null 2>&1; then exit 1; fi
fdtget "$dtb" "$PIO" gpio-controller >/dev/null
pio=$(fdtget -t u "$dtb" "$PIO" phandle)
max=$(dtc -q -I dtb -O dts "$dtb" | sed -n 's/.*phandle = <\(0x[0-9a-f]*\)>;.*/\1/p' |
	while read -r h; do printf '%d\n' "$h"; done | sort -n | tail -1)
vmch=$((max + 1))
vmc=$((max + 2))
pins=$((max + 3))

fdtput -c "$dtb" "$REGS/ldo-vmch"
fdtput -t s "$dtb" "$REGS/ldo-vmch" regulator-name vmch
fdtput -t u "$dtb" "$REGS/ldo-vmch" regulator-min-microvolt 3000000
fdtput -t u "$dtb" "$REGS/ldo-vmch" regulator-max-microvolt 3000000
fdtput -t u "$dtb" "$REGS/ldo-vmch" phandle "$vmch"
fdtput -c "$dtb" "$REGS/ldo-vmc"
fdtput -t s "$dtb" "$REGS/ldo-vmc" regulator-name vmc
fdtput -t u "$dtb" "$REGS/ldo-vmc" regulator-min-microvolt 3000000
fdtput -t u "$dtb" "$REGS/ldo-vmc" regulator-max-microvolt 3000000
fdtput -t u "$dtb" "$REGS/ldo-vmc" phandle "$vmc"
fdtput -c "$dtb" "$PIO/msdc1-pins"
fdtput -t u "$dtb" "$PIO/msdc1-pins" phandle "$pins"
fdtput -c "$dtb" "$PIO/msdc1-pins/pins-sd"
# MTK_PIN_NO(n) | 1 for GPIO129..134 (MSDC1 CMD, DAT0-3, CLK).
fdtput -t u "$dtb" "$PIO/msdc1-pins/pins-sd" pinmux \
	$((129 << 8 | 1)) $((130 << 8 | 1)) $((131 << 8 | 1)) \
	$((132 << 8 | 1)) $((133 << 8 | 1)) $((134 << 8 | 1))
fdtput -t s "$dtb" "$MMC" status okay
fdtput -t s "$dtb" "$MMC" pinctrl-names default state_uhs
fdtput -t u "$dtb" "$MMC" pinctrl-0 "$pins"
fdtput -t u "$dtb" "$MMC" pinctrl-1 "$pins"
fdtput -t u "$dtb" "$MMC" bus-width 4
fdtput -t u "$dtb" "$MMC" max-frequency 50000000
fdtput "$dtb" "$MMC" cap-sd-highspeed
fdtput "$dtb" "$MMC" no-1-8-v
fdtput "$dtb" "$MMC" disable-wp
fdtput -t u "$dtb" "$MMC" cd-gpios "$pio" 67 0
fdtput -t u "$dtb" "$MMC" vmmc-supply "$vmch"
fdtput -t u "$dtb" "$MMC" vqmmc-supply "$vmc"

dtc -q -I dtb -O dts -s "$work/board.dtb" > "$work/board.dts"
dtc -q -I dtb -O dts -s "$dtb" > "$work/out.dts"
diff "$work/board.dts" "$work/out.dts" | grep '^[<>]' |
	sed 's/^\([<>]\)[[:space:]]*/\1 /; s/[[:space:]]*$//' | grep -v '^[<>]$' |
	LC_ALL=C sort > "$work/delta"
hex() { printf '0x%02x' "$1"; }
LC_ALL=C sort > "$work/expected" <<DELTA
< status = "disabled";
> status = "okay";
> pinctrl-names = "default\\0state_uhs";
> pinctrl-0 = <$(hex "$pins")>;
> pinctrl-1 = <$(hex "$pins")>;
> bus-width = <0x04>;
> max-frequency = <$(hex 50000000)>;
> cap-sd-highspeed;
> no-1-8-v;
> disable-wp;
> cd-gpios = <$(hex "$pio") $(hex 67) 0x00>;
> vmmc-supply = <$(hex "$vmch")>;
> vqmmc-supply = <$(hex "$vmc")>;
> ldo-vmch {
> regulator-name = "vmch";
> regulator-min-microvolt = <$(hex 3000000)>;
> regulator-max-microvolt = <$(hex 3000000)>;
> phandle = <$(hex "$vmch")>;
> };
> ldo-vmc {
> regulator-name = "vmc";
> regulator-min-microvolt = <$(hex 3000000)>;
> regulator-max-microvolt = <$(hex 3000000)>;
> phandle = <$(hex "$vmc")>;
> };
> msdc1-pins {
> phandle = <$(hex "$pins")>;
> pins-sd {
> pinmux = <$(hex $((129 << 8 | 1))) $(hex $((130 << 8 | 1))) $(hex $((131 << 8 | 1))) $(hex $((132 << 8 | 1))) $(hex $((133 << 8 | 1))) $(hex $((134 << 8 | 1)))>;
> };
> };
DELTA
cmp -s "$work/delta" "$work/expected" || {
	echo "unexpected DT delta:" >&2
	diff "$work/expected" "$work/delta" >&2 || true
	exit 1
}
cp "$dtb" "$output"
sha256sum "$output"
