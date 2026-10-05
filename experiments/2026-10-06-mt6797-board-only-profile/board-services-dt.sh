#!/bin/sh
# SPDX-License-Identifier: MIT
# Derive the board-services candidate DTB from the exact C1-5 parent DTB.
# Only these edits are made, and the decompiled difference must be exactly them:
#   /i2c@1100e000            status = "disabled"; access-controllers removed
#   /dvfsp-handoff@11015000  status = "disabled"
#   /cpus/cpu@200, cpu@201   status = "disabled" (intent only; the retained
#                            custom enable-method keeps them out of possible)
# Usage: board-services-dt.sh PARENT.dtb OUTPUT.dtb
set -eu

PARENT_SHA256=ce3d4d2368a6be47f72a474a813ade47fec2a292707864b528a084cfb62efe38

[ "$#" -eq 2 ] || { echo "usage: $0 PARENT.dtb OUTPUT.dtb" >&2; exit 2; }
parent=$1
output=$2
if [ -L "$parent" ] || [ ! -f "$parent" ]; then
	echo "parent must be a regular file, not a symlink" >&2
	exit 1
fi
if [ -e "$output" ] || [ -L "$output" ]; then
	echo "refusing to overwrite $output or follow a symlink" >&2
	exit 1
fi
[ "$(sha256sum "$parent" | cut -d' ' -f1)" = "$PARENT_SHA256" ] ||
	{ echo "parent DTB is not the reviewed C1-5 parent" >&2; exit 1; }

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp "$parent" "$work/out.dtb"

# Every edited node must exist with the expected parent values first.
[ "$(fdtget -t s "$work/out.dtb" /i2c@1100e000 status)" = okay ]
[ "$(fdtget -t s "$work/out.dtb" /dvfsp-handoff@11015000 status)" = okay ]
fdtget "$work/out.dtb" /i2c@1100e000 access-controllers >/dev/null
for cpu in cpu@200 cpu@201; do
	[ "$(fdtget -t s "$work/out.dtb" "/cpus/$cpu" enable-method)" = mediatek,mt6797-psci ]
	if fdtget "$work/out.dtb" "/cpus/$cpu" status >/dev/null 2>&1; then exit 1; fi
done

fdtput -t s "$work/out.dtb" /i2c@1100e000 status disabled
fdtput -d "$work/out.dtb" /i2c@1100e000 access-controllers
fdtput -t s "$work/out.dtb" /dvfsp-handoff@11015000 status disabled
for cpu in cpu@200 cpu@201; do
	fdtput -t s "$work/out.dtb" "/cpus/$cpu" status disabled
done

# The decompiled difference must be exactly the declared edits.
dtc -q -I dtb -O dts -s "$parent" > "$work/parent.dts"
dtc -q -I dtb -O dts -s "$work/out.dtb" > "$work/out.dts"
diff "$work/parent.dts" "$work/out.dts" | grep '^[<>]' | sed 's/^\([<>]\)[[:space:]]*/\1 /' |
	LC_ALL=C sort > "$work/delta"
LC_ALL=C sort > "$work/expected" <<'DELTA'
< access-controllers = <0x2c>;
< status = "okay";
< status = "okay";
> status = "disabled";
> status = "disabled";
> status = "disabled";
> status = "disabled";
DELTA
cmp -s "$work/delta" "$work/expected" || {
	echo "unexpected DT delta:" >&2
	cat "$work/delta" >&2
	exit 1
}
for cpu in cpu@200 cpu@201; do
	[ "$(fdtget -t s "$work/out.dtb" "/cpus/$cpu" enable-method)" = mediatek,mt6797-psci ]
done
cp "$work/out.dtb" "$output"
sha256sum "$output"
