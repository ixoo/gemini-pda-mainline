#!/bin/sh
# SPDX-License-Identifier: MIT
# Derive the display H2 candidate DTB: the board-services candidate DTB plus
# exactly one property, the framebuffer's MM power domain:
#   /chosen/framebuffer@7dfb0000  power-domains = <&scpsys MT6797_POWER_DOMAIN_MM>
# The board-services script pins the exact C1-5 parent and its four edits.
# Usage: display-h2-dt.sh PARENT.dtb OUTPUT.dtb
set -eu

MM_DOMAIN=3
FB=/chosen/framebuffer@7dfb0000
SCPSYS=/power-controller@10006000
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

# The provider must be the legacy MT6797 SCPSYS; the framebuffer must not
# already name a power domain.
fdtget -t s "$work/out.dtb" "$SCPSYS" compatible | tr ' ' '\n' | grep -qx 'mediatek,mt6797-scpsys'
[ "$(fdtget -t u "$work/out.dtb" "$SCPSYS" '#power-domain-cells')" = 1 ]
[ "$(fdtget -t s "$work/out.dtb" "$FB" compatible)" = simple-framebuffer ]
if fdtget "$work/out.dtb" "$FB" power-domains >/dev/null 2>&1; then exit 1; fi
phandle=$(fdtget -t u "$work/out.dtb" "$SCPSYS" phandle)

fdtput -t u "$work/out.dtb" "$FB" power-domains "$phandle" "$MM_DOMAIN"

dtc -q -I dtb -O dts -s "$work/board.dtb" > "$work/board.dts"
dtc -q -I dtb -O dts -s "$work/out.dtb" > "$work/out.dts"
diff "$work/board.dts" "$work/out.dts" | grep '^[<>]' |
	sed 's/^\([<>]\)[[:space:]]*/\1 /' > "$work/delta"
printf '> power-domains = <%s 0x%02x>;\n' \
	"$(printf '0x%02x' "$phandle")" "$MM_DOMAIN" > "$work/expected"
cmp -s "$work/delta" "$work/expected" || {
	echo "unexpected DT delta:" >&2
	cat "$work/delta" >&2
	exit 1
}
cp "$work/out.dtb" "$output"
sha256sum "$output"
