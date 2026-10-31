#!/bin/sh
# SPDX-License-Identifier: MIT
# Derive the station DTB from the package's wifi-service DTB:
#   /gpio-keys                the hall lid switch (0074), enabled as
#                             gpio-keys-polled every 100 ms: GPIO66's level
#                             follows the lid on mainline, but EINT5 has never
#                             fired (C1 to C1-5 boots, and station boot
#                             bac0f387);
#   /pwm@1100f000, /backlight the PWM backlight (display H8): pwm_sel on the
#                             26 MHz oscillator, 1024 levels at 39385 ns,
#                             default level 512. The PWM's MM power-domains
#                             reference is removed: this kernel registers only
#                             the CONN domain, so an MM consumer waits forever
#                             (bac0f387), and nothing here can switch MM off.
#   /i2c@11007000             I2C0 enabled with no child bound (its FAN49101
#                             node stays disabled), for power-status's
#                             read-only charger reads through i2c-dev
#                             (2026-10-31-gemini-power-status).
# The framebuffer is left as the package has it.
# Usage: station-dt.sh PARENT.dtb OUTPUT.dtb
set -eu

KEYS=/gpio-keys
POLL_MS=100
PWM=/pwm@1100f000
TOP=/topckgen@10000000
OSC=/oscillator-26m
BL=/backlight
MUX_PWM=7
PERIOD_NS=39385
I2C0=/i2c@11007000

[ "$#" -eq 2 ] || { echo "usage: $0 PARENT.dtb OUTPUT.dtb" >&2; exit 2; }
output=$2
if [ -e "$output" ] || [ -L "$output" ]; then
	echo "refusing to overwrite $output or follow a symlink" >&2
	exit 1
fi

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cp "$1" "$work/parent.dtb"
cp "$1" "$work/out.dtb"
dtb=$work/out.dtb

# Preconditions.
[ "$(fdtget -t s "$dtb" "$KEYS" compatible)" = gpio-keys ]
[ "$(fdtget -t s "$dtb" "$KEYS" status)" = disabled ]
[ "$(fdtget -t s "$dtb" "$KEYS/hall-switch" label)" = "Hall lid" ]
[ "$(fdtget -t u "$dtb" "$KEYS/hall-switch" linux,input-type)" = 5 ]
[ "$(fdtget -t u "$dtb" "$KEYS/hall-switch" linux,code)" = 0 ]
if fdtget "$dtb" "$KEYS" poll-interval >/dev/null 2>&1; then exit 1; fi
[ "$(fdtget -t s "$dtb" "$PWM" compatible)" = mediatek,mt6797-disp-pwm ]
[ "$(fdtget -t s "$dtb" "$PWM" status)" = disabled ]
[ "$(fdtget -t u "$dtb" "$PWM" power-domains | tr ' ' ,)" = 11,3 ]
if fdtget "$dtb" "$PWM" phandle >/dev/null 2>&1; then exit 1; fi
fdtget -t s "$dtb" "$TOP" compatible | tr ' ' '\n' | grep -qx mediatek,mt6797-topckgen
[ "$(fdtget -t u "$dtb" "$TOP" '#clock-cells')" = 1 ]
[ "$(fdtget -t s "$dtb" "$OSC" compatible)" = fixed-clock ]
[ "$(fdtget -t s "$dtb" "$OSC" clock-output-names)" = clk26m ]
[ "$(fdtget -t u "$dtb" "$OSC" clock-frequency)" = 26000000 ]
if fdtget "$dtb" "$BL" compatible >/dev/null 2>&1; then exit 1; fi
fdtget -t s "$dtb" "$I2C0" compatible | tr ' ' '\n' | grep -qx mediatek,mt6797-i2c
[ "$(fdtget -t s "$dtb" "$I2C0" status)" = disabled ]
[ "$(fdtget -t s "$dtb" "$I2C0/regulator@70" status)" = disabled ]
top=$(fdtget -t u "$dtb" "$TOP" phandle)
osc=$(fdtget -t u "$dtb" "$OSC" phandle)
max=$(dtc -q -I dtb -O dts "$dtb" | sed -n 's/.*phandle = <\(0x[0-9a-f]*\)>;.*/\1/p' |
	while read -r h; do printf '%d\n' "$h"; done | sort -n | tail -1)
pwm=$((max + 1))

fdtput -t s "$dtb" "$KEYS" compatible gpio-keys-polled
fdtput -t u "$dtb" "$KEYS" poll-interval "$POLL_MS"
fdtput -t s "$dtb" "$KEYS" status okay
fdtput -d "$dtb" "$PWM" power-domains
fdtput -t s "$dtb" "$PWM" status okay
fdtput -t u "$dtb" "$PWM" phandle "$pwm"
fdtput -t u "$dtb" "$PWM" assigned-clocks "$top" "$MUX_PWM"
fdtput -t u "$dtb" "$PWM" assigned-clock-parents "$osc"
fdtput -c "$dtb" "$BL"
fdtput -t s "$dtb" "$BL" compatible pwm-backlight
fdtput -t u "$dtb" "$BL" pwms "$pwm" 0 "$PERIOD_NS"
fdtput -t u "$dtb" "$BL" brightness-levels 0 1023
fdtput -t u "$dtb" "$BL" num-interpolated-steps 1023
fdtput -t u "$dtb" "$BL" default-brightness-level 512
fdtput -t s "$dtb" "$I2C0" status okay

dtc -q -I dtb -O dts -s "$work/parent.dtb" > "$work/parent.dts"
dtc -q -I dtb -O dts -s "$dtb" > "$work/out.dts"
diff "$work/parent.dts" "$work/out.dts" | grep '^[<>]' |
	sed 's/^\([<>]\)[[:space:]]*/\1 /; s/[[:space:]]*$//' | LC_ALL=C sort > "$work/delta"
hex() { printf '0x%02x' "$1"; }
LC_ALL=C sort > "$work/expected" <<DELTA
< compatible = "gpio-keys";
> compatible = "gpio-keys-polled";
> poll-interval = <$(hex "$POLL_MS")>;
< status = "disabled";
< status = "disabled";
< status = "disabled";
> status = "okay";
> status = "okay";
> status = "okay";
< power-domains = <0x0b 0x03>;
> phandle = <$(hex "$pwm")>;
> assigned-clocks = <$(hex "$top") $(hex "$MUX_PWM")>;
> assigned-clock-parents = <$(hex "$osc")>;
> backlight {
> compatible = "pwm-backlight";
> pwms = <$(hex "$pwm") 0x00 $(hex "$PERIOD_NS")>;
> brightness-levels = <0x00 $(hex 1023)>;
> num-interpolated-steps = <$(hex 1023)>;
> default-brightness-level = <$(hex 512)>;
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
