#!/usr/bin/env bash

set -euo pipefail
export LC_ALL=C
umask 077

die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ "$(uname -s)" == Linux ]] || die "run inside the Linux development VM"
[[ $# -eq 3 ]] || \
	die "usage: build-keyboard-watchdog-dtb.sh P_DTB PACKAGE_ORACLE_DTB OUTPUT"
p_dtb=$1
oracle=$2
output=$3
[[ -s "$p_dtb" && -s "$oracle" ]] || die "P or package-oracle DTB is missing"
[[ ! -e "$output" ]] || die "refusing to overwrite $output"
for tool in awk fdtget fdtput grep install sha256sum uname; do
	command -v "$tool" >/dev/null 2>&1 || die "$tool is required"
done

readonly P_DTB_SHA256=c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379
readonly PACKAGE_DTB_SHA256=f9be46ffed6cf598f7892d88d8702ff6a4ede074c5b477734ae11bcb4c093db5
readonly PINCTRL=/pinctrl@10005000
readonly I2C5_PINS=$PINCTRL/i2c5-pins
readonly KEYBOARD_PINS=$PINCTRL/keyboard-soc-pins
readonly RESET_PINS=$KEYBOARD_PINS/pins-reset
readonly IRQ_PINS=$KEYBOARD_PINS/pins-irq
readonly I2C5=/i2c@1101c000
readonly AW=$I2C5/gpio-expander@5b
readonly MATRIX=/keyboard-matrix
readonly WATCHDOG=/watchdog@10007000
readonly P_I2C5_PINS_PHANDLE=0x2a
readonly P_KEYBOARD_PINS_PHANDLE=0x2b

[[ "$(sha256sum "$p_dtb" | awk '{print $1}')" == "$P_DTB_SHA256" ]] || \
	die "base is not exact Candidate P DTB"
[[ "$(sha256sum "$oracle" | awk '{print $1}')" == "$PACKAGE_DTB_SHA256" ]] || \
	die "keyboard oracle is not the pinned polling-package DTB"

for node in "$I2C5" "$AW" "$MATRIX"; do
	[[ "$(fdtget -t s "$p_dtb" "$node" status)" == disabled ]] || \
		die "Candidate P keyboard node is not disabled: $node"
	[[ "$(fdtget -t s "$oracle" "$node" status)" == disabled ]] || \
		die "package-oracle keyboard node is not disabled: $node"
done
! fdtget "$p_dtb" "$WATCHDOG" interrupts >/dev/null 2>&1 || \
	die "Candidate P lost its proven no-IRQ watchdog contract"
fdtget "$p_dtb" /chosen/framebuffer@7dfb0000 clocks >/dev/null || \
	die "Candidate P loader simplefb contract is absent"

# The package is an oracle only. Assert the corrected resources before
# recreating them with P-local phandles; never use the package DT as a base.
[[ "$(fdtget -t x "$oracle" "$AW" interrupts)" == 'a 8' ]] || \
	die "oracle does not describe GPIO87 as raw EINT10 level-low"
[[ "$(fdtget -t x "$oracle" "$RESET_PINS" pinmux)" == 3a00 ]] || \
	die "oracle reset pin is not GPIO58"
[[ "$(fdtget -t x "$oracle" "$IRQ_PINS" pinmux)" == 5701 ]] || \
	die "oracle IRQ pin is not GPIO87/EINT10"
fdtget "$oracle" "$RESET_PINS" output-high >/dev/null || \
	die "oracle reset pin lacks output-high release state"
oracle_aw_phandle="$(fdtget -t x "$oracle" "$AW" phandle)"
[[ "$(fdtget -t x "$oracle" "$AW" gpio-ranges)" == \
	"$oracle_aw_phandle 0 0 10" ]] || die "oracle AW gpio-ranges is not self-referential"
[[ "$(fdtget -t x "$p_dtb" "$AW" phandle)" == 28 ]] || \
	die "Candidate P AW phandle is not the pinned 0x28"
fdtget -t x "$p_dtb" /pinctrl@10005000/hall-pins phandle | \
	grep -Fxq 29 || die "Candidate P global phandle boundary changed"
! fdtget "$p_dtb" "$I2C5_PINS" phandle >/dev/null 2>&1 || \
	die "Candidate P i2c5 pin group unexpectedly already has a phandle"
! fdtget "$p_dtb" "$KEYBOARD_PINS" phandle >/dev/null 2>&1 || \
	die "Candidate P unexpectedly already has keyboard SoC pins"

install -m 0600 "$p_dtb" "$output"
fdtput -t x "$output" "$I2C5_PINS" phandle "$P_I2C5_PINS_PHANDLE"
fdtput -c "$output" "$KEYBOARD_PINS"
fdtput -t x "$output" "$KEYBOARD_PINS" phandle "$P_KEYBOARD_PINS_PHANDLE"
fdtput -c "$output" "$RESET_PINS"
fdtput -t x "$output" "$RESET_PINS" pinmux 0x3a00
fdtput "$output" "$RESET_PINS" output-high
fdtput -c "$output" "$IRQ_PINS"
fdtput -t x "$output" "$IRQ_PINS" pinmux 0x5701

for node in "$I2C5" "$AW" "$MATRIX"; do
	fdtput -t s "$output" "$node" status okay
done
fdtput -t s "$output" "$I2C5" pinctrl-names default
fdtput -t x "$output" "$I2C5" pinctrl-0 "$P_I2C5_PINS_PHANDLE"
fdtput -t i "$output" "$I2C5" clock-frequency 400000
fdtput -t s "$output" "$AW" pinctrl-names default
fdtput -t x "$output" "$AW" pinctrl-0 "$P_KEYBOARD_PINS_PHANDLE"
fdtput -t x "$output" "$AW" gpio-ranges 0x28 0 0 0x10
for property in interrupt-parent interrupts interrupt-controller '#interrupt-cells'; do
	fdtput -d "$output" "$AW" "$property"
done
fdtput -t i "$output" "$MATRIX" poll-interval 20
fdtput -t i "$output" "$MATRIX" col-scan-delay-us 2

! fdtget "$output" "$WATCHDOG" interrupts >/dev/null 2>&1 || \
	die "Candidate V reintroduced the optional watchdog interrupt"
fdtget "$output" /chosen/framebuffer@7dfb0000 clocks >/dev/null || \
	die "Candidate V lost Candidate P loader simplefb"
printf 'sha256=%s\n' "$(sha256sum "$output" | awk '{print $1}')"
printf 'base=candidate-P-exact\nbase_sha256=%s\n' "$P_DTB_SHA256"
printf 'package_oracle_sha256=%s\n' "$PACKAGE_DTB_SHA256"
printf 'keyboard_nodes=enabled\npoll_interval_ms=20\npolling_debounce=none\n'
printf 'col_scan_delay_us=2\ni2c5_hz=400000\naw_parent_irq=removed\n'
printf 'watchdog_irq=retained-absent-from-P\nsimplefb=retained-from-P\n'
printf 'hardware_write=none\n'
