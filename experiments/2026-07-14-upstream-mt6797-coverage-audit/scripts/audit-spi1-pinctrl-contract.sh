#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only extraction of the SPI1 pinctrl contract from the private, sanitized
# vendor device-tree capture. It deliberately does not enable a controller or
# infer a safe transfer policy from the vendor's manual GPIO/SPI switching.

set -euo pipefail
export LC_ALL=C

capture=${DT_CAPTURE:-artifacts/device-inventory/20260711-live/device-tree-v5.txt}
pinfunc=${PINFUNC_HEADER:-}

[[ -r "$capture" ]] || { printf 'missing_capture=%s\n' "$capture" >&2; exit 1; }

printf 'validation=mt6797-spi1-pinctrl-contract\n'
printf 'capture=%s\n' "$capture"
printf 'capture_sha256=%s\n' "$(sha256sum "$capture" | awk '{print $1}')"

printf '\n[controller]\n'
rg -m1 '^/soc/spi@11012000\|compatible=' "$capture"
rg -m1 '^/soc/spi@11012000\|reg=' "$capture"
rg -m1 '^/soc/spi@11012000\|interrupts=' "$capture"
rg -m1 '^/soc/spi@11012000\|clocks=' "$capture"
rg -m1 '^/soc/spi@11012000\|pinctrl-names=' "$capture"
rg -m1 '^/soc/spi@11012000/fpc1145@0\|compatible=' "$capture"
rg -m1 '^/soc/spi@11012000/fpc1145@0\|spi-max-frequency=' "$capture"

printf '\n[pins]\n'
for pin in clk cs miso mosi; do
	case "$pin" in
		clk) gpio=234; signal=SPI1_CLK_B; set_state=spi1_clk_set; clear_state=spi1_clk_clear ;;
		cs) gpio=237; signal=SPI1_CS_B; set_state=spi1_cs_set; clear_state=spi1_cs_clear ;;
		miso) gpio=235; signal=SPI1_MI_B; set_state=spi1_miso_set; clear_state=spi1_miso_clear ;;
		mosi) gpio=236; signal=SPI1_MO_B; set_state=spi1_mosi_set; clear_state=spi1_mosi_clear ;;
	esac
	set_value=$(rg -m1 "^/soc/pinctrl@10005000/${set_state}@gpio${gpio}/pins_cmd_dat\\|pins=" "$capture" | sed 's/.*|pins=//')
	clear_value=$(rg -m1 "^/soc/pinctrl@10005000/${clear_state}@gpio${gpio}/pins_cmd_dat\\|pins=" "$capture" | sed 's/.*|pins=//')
	printf 'signal=%s gpio=%s mainline_function=1 vendor_set=%s vendor_clear=%s\n' \
		"$signal" "$gpio" "$set_value" "$clear_value"
done

if [[ -n "$pinfunc" ]]; then
	[[ -r "$pinfunc" ]] || { printf 'missing_pinf_file='; exit 1; }
	printf '\n[mainline_pinfunc]\n'
	for symbol in \
		MT6797_GPIO234__FUNC_SPI1_CLK_B \
		MT6797_GPIO235__FUNC_SPI1_MI_B \
		MT6797_GPIO236__FUNC_SPI1_MO_B \
		MT6797_GPIO237__FUNC_SPI1_CS_B; do
		rg -m1 "^#define ${symbol} " "$pinfunc"
	done
fi

printf '\n[interpretation]\n'
printf '%s\n' \
	'vendor_default_state=spi1_gpio_default is an empty state in the capture' \
	'vendor_transfer_model=vendor states switch each signal between GPIO function 0 and SPI function 1' \
	'mainline_reuse=spi-mt65xx normally expects a stable pinctrl default and owns hardware chip-select/timing' \
	'not_proven=the capture does not prove that a static function-1 group is electrically safe for a mainline transfer' \
	'next_gate=validate one controlled SPI1 probe/loopback only after a recovery-backed mainline boot; do not add fpc1020 or vendor pinctrl state-machine ABI'
