#!/bin/sh
# SPDX-License-Identifier: MIT
# Derive the audio H3 candidate DTB: the display H2 DTB (simplefb holds MM;
# SCPSYS adopt mode provides the AFE's AUDIO domain) plus
#   /audio-controller@11220000  okay, with a new phandle;
#   /pwrap@1000d000/pmic/audio-codec  mediatek,mt6351-sound, new phandle;
#   /sound  mediatek,mt6797-mt6351-sound card linking the two.
# The five codec pads (GPIO146-150) keep the board DWS default, mode 1, which
# the preloader applies; no pinctrl state is added.
# Usage: audio-h3-dt.sh PARENT.dtb OUTPUT.dtb
set -eu

AFE=/audio-controller@11220000
PMIC=/pwrap@1000d000/pmic
CODEC=$PMIC/audio-codec
SOUND=/sound
here=$(cd "$(dirname "$0")" && pwd)
h2="$here/../2026-10-06-gemini-display-h2/display-h2-dt.sh"

[ "$#" -eq 2 ] || { echo "usage: $0 PARENT.dtb OUTPUT.dtb" >&2; exit 2; }
output=$2
if [ -e "$output" ] || [ -L "$output" ]; then
	echo "refusing to overwrite $output or follow a symlink" >&2
	exit 1
fi

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
"$h2" "$1" "$work/h2.dtb" >/dev/null
cp "$work/h2.dtb" "$work/out.dtb"
dtb=$work/out.dtb

[ "$(fdtget -t s "$dtb" "$AFE" compatible)" = mediatek,mt6797-audio ]
[ "$(fdtget -t s "$dtb" "$AFE" status)" = disabled ]
[ "$(fdtget -t u "$dtb" "$AFE" power-domains | cut -d' ' -f2)" = 4 ]
if fdtget "$dtb" "$AFE" phandle >/dev/null 2>&1; then exit 1; fi
fdtget -t s "$dtb" "$PMIC" compatible | tr ' ' '\n' | grep -qx mediatek,mt6351
if fdtget "$dtb" "$CODEC" compatible >/dev/null 2>&1; then exit 1; fi
if fdtget "$dtb" "$SOUND" compatible >/dev/null 2>&1; then exit 1; fi
max=$(dtc -q -I dtb -O dts "$dtb" | sed -n 's/.*phandle = <\(0x[0-9a-f]*\)>;.*/\1/p' |
	while read -r h; do printf '%d\n' "$h"; done | sort -n | tail -1)
afe=$((max + 1))
codec=$((max + 2))

fdtput -t s "$dtb" "$AFE" status okay
fdtput -t u "$dtb" "$AFE" phandle "$afe"
fdtput -c "$dtb" "$CODEC"
fdtput -t s "$dtb" "$CODEC" compatible mediatek,mt6351-sound
fdtput -t u "$dtb" "$CODEC" phandle "$codec"
fdtput -c "$dtb" "$SOUND"
fdtput -t s "$dtb" "$SOUND" compatible mediatek,mt6797-mt6351-sound
fdtput -t u "$dtb" "$SOUND" mediatek,platform "$afe"
fdtput -t u "$dtb" "$SOUND" mediatek,audio-codec "$codec"

dtc -q -I dtb -O dts -s "$work/h2.dtb" > "$work/h2.dts"
dtc -q -I dtb -O dts -s "$dtb" > "$work/out.dts"
diff "$work/h2.dts" "$work/out.dts" | grep '^[<>]' |
	sed 's/^\([<>]\)[[:space:]]*/\1 /; s/[[:space:]]*$//' | grep -v '^[<>]$' |
	LC_ALL=C sort > "$work/delta"
hex() { printf '0x%02x' "$1"; }
LC_ALL=C sort > "$work/expected" <<DELTA
< status = "disabled";
> status = "okay";
> phandle = <$(hex "$afe")>;
> audio-codec {
> compatible = "mediatek,mt6351-sound";
> phandle = <$(hex "$codec")>;
> };
> sound {
> compatible = "mediatek,mt6797-mt6351-sound";
> mediatek,platform = <$(hex "$afe")>;
> mediatek,audio-codec = <$(hex "$codec")>;
> };
DELTA
cmp -s "$work/delta" "$work/expected" || {
	echo "unexpected DT delta:" >&2
	diff "$work/expected" "$work/delta" >&2 || true
	exit 1
}
cp "$dtb" "$output"
sha256sum "$output"
