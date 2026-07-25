#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ "$(uname -s)" == Linux ]] || die "run inside the Linux development VM"
[[ $# -eq 2 ]] || die "usage: build-keyboard-polling-dtb.sh PACKAGE_DTB OUTPUT"
input=$1
output=$2
[[ -s "$input" ]] || die "package DTB is missing"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
for tool in fdtget fdtput; do command -v "$tool" >/dev/null || die "$tool is required"; done

readonly I2C5=/i2c@1101c000
readonly AW=/i2c@1101c000/gpio-expander@5b
readonly MATRIX=/keyboard-matrix
for node in "$I2C5" "$AW" "$MATRIX"; do
	[[ "$(fdtget -t s "$input" "$node" status)" == disabled ]] || \
		die "expected disabled source node: $node"
done
[[ "$(fdtget -t x "$input" "$AW" interrupts)" == 'a 8' ]] || \
	die "inactive source does not describe GPIO87 as raw EINT10 level-low"
for property in interrupt-parent interrupts interrupt-controller '#interrupt-cells'; do
	fdtget "$input" "$AW" "$property" >/dev/null 2>&1 || \
		die "inactive source is missing AW property: $property"
done
! fdtget "$input" "$I2C5" clock-frequency >/dev/null 2>&1 || \
	die "source unexpectedly contains I2C5 property: clock-frequency"
for property in poll-interval debounce-delay-ms col-scan-delay-us; do
	! fdtget "$input" "$MATRIX" "$property" >/dev/null 2>&1 || \
		die "source unexpectedly contains matrix property: $property"
done

install -m 0600 "$input" "$output"
for node in "$I2C5" "$AW" "$MATRIX"; do
	fdtput -t s "$output" "$node" status okay
done
for property in interrupt-parent interrupts interrupt-controller '#interrupt-cells'; do
	fdtput -d "$output" "$AW" "$property"
done
fdtput -t i "$output" "$I2C5" clock-frequency 400000
fdtput -t i "$output" "$MATRIX" poll-interval 20
fdtput -t i "$output" "$MATRIX" col-scan-delay-us 2

[[ "$(fdtget -t u "$output" "$I2C5" clock-frequency)" == 400000 ]] || die "I2C5 rate mismatch"
[[ "$(fdtget -t u "$output" "$MATRIX" poll-interval)" == 20 ]] || die "poll interval mismatch"
! fdtget "$output" "$MATRIX" debounce-delay-ms >/dev/null 2>&1 || \
	die "polling DTB unexpectedly contains inert debounce-delay-ms"
for property in interrupt-parent interrupts interrupt-controller '#interrupt-cells'; do
	! fdtget "$output" "$AW" "$property" >/dev/null 2>&1 || \
		die "active polling DTB retained AW property: $property"
done
fdtget "$output" /pinctrl@10005000/keyboard-soc-pins/pins-irq pinmux >/dev/null || \
	die "GPIO87/EINT10 pinmux state was not retained"
printf 'output=%s\nsha256=%s\n' "$output" "$(sha256sum "$output" | awk '{print $1}')"
printf 'enabled=%s,%s,%s\n' "$I2C5" "$AW" "$MATRIX"
printf 'poll_interval_ms=20\npolling_debounce=none\ncol_scan_delay_us=2\ni2c5_hz=400000\n'
printf 'aw_parent_irq=removed\ngpio87_pinmux=retained-input\n'
