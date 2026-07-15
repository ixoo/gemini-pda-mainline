#!/usr/bin/env bash

# Compare the vendor MT6797 UART contract with Linux 7.1.3 and the local
# Gemini board description. Vendor source is read from immutable Git objects;
# no vendor code is copied into this repository.

set -eu
export LC_ALL=C

vendor_tree=${VENDOR_TREE:-/home/julien.guest/src/reference/planet-mt6797-3.18}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
repo_root=${REPO_ROOT:-/mnt/gemini-pda-mainline}

[[ -d "$vendor_tree/.git" ]] || { printf 'missing vendor Git tree: %s\n' "$vendor_tree" >&2; exit 1; }
[[ -d "$linux_tree" ]] || { printf 'missing Linux tree: %s\n' "$linux_tree" >&2; exit 1; }

vendor_show() {
	git -C "$vendor_tree" show "HEAD:$1"
}

printf 'vendor_tree=%s\n' "$vendor_tree"
printf 'vendor_commit=%s\n' "$(git -C "$vendor_tree" rev-parse HEAD)"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_commit=%s\n' "$(git -C "$linux_tree" rev-parse --verify HEAD 2>/dev/null || printf unknown)"

printf '\n[vendor MT6797 UART DT]\n'
vendor_show arch/arm64/boot/dts/mt6797.dtsi |
	rg -n -A 13 -B 2 'apuart[0-3]:|compatible = "mediatek,mt6797-uart"' |
	head -n 260 || true

printf '\n[vendor UART implementation contract]\n'
vendor_show drivers/misc/mediatek/uart/mt6797/platform_uart.c |
	rg -n -C 3 'of_iomap|irq_of_parse|UART_DMA|UART_NON_DMA|pinctrl|interrupts|phys_base' |
	head -n 260 || true
vendor_show drivers/misc/mediatek/uart/uart.c |
	rg -n -C 2 'console|VFIFO|P_DMA_UART|UART_NON_DMA|mtk_uart_vfifo' |
	head -n 260 || true

printf '\n[vendor binding]\n'
vendor_show Documentation/devicetree/bindings/serial/mtk-uart.txt |
	sed -n '1,100p'

printf '\n[Linux 7.1.3 binding and driver]\n'
rg -n -C 3 'mt6797-uart|reg:|clocks:|dmas:|interrupts:|clock-names:|of_match|early_mtk8250_setup|disable DMA for console' \
	"$linux_tree/Documentation/devicetree/bindings/serial/mediatek,uart.yaml" \
	"$linux_tree/drivers/tty/serial/8250/8250_mtk.c" |
	head -n 360 || true

printf '\n[Linux MT6797 UART DTS]\n'
rg -n -A 12 -B 2 'uart[0-3]: serial@1100|compatible = "mediatek,mt6797-uart"' \
	"$linux_tree/arch/arm64/boot/dts/mediatek/mt6797.dtsi" |
	head -n 220 || true

printf '\n[Linux MT6797 UART pin group]\n'
rg -n -A 10 -B 2 'uart0_pins_a' \
	"$linux_tree/arch/arm64/boot/dts/mediatek/mt6797.dtsi" |
	head -n 80 || true

printf '\n[local Gemini UART/console declarations]\n'
if [ -r "$repo_root/patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch" ]; then
	rg -n -C 5 'serial0|stdout-path|&uart0|pinctrl-0.*uart0|status = "okay"' \
		"$repo_root/patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch" || true
else
	echo 'local_patch=not_visible_from_guest'
fi
rg -n 'SERIAL_8250|SERIAL_8250_CONSOLE|SERIAL_8250_MT6577|SERIAL_8250_DMA' \
	"$repo_root/configs/gemini.fragment" || true

printf '\n[decision]\n'
printf '%s\n' \
	'live_ttyMT0_console_and_ttyMT1_to_ttyMT3_are_bound_to_vendor_mtk-uart' \
	'live_MT6797_UART0_has_optional_vendor_DMA_windows_and_three_IRQs' \
	'Linux_8250_mtk_reuses_the_16550_UART_and_PIO_console_contract' \
	'Linux_8250_mtk_disables_DMA_when_the_port_is_a_console' \
	'Linux_MT6797_uart0_pins_a_is_pinmux_only_and_avoids_unimplemented_MT6797_pinconf_maps' \
	'local_Gemini_UART0_PIO_console_is_a_reuse_candidate_but_vendor_ttyMT0_cmdline_is_not_mainline_device_naming' \
	'use_standard_serial0_stdout_path_and_mainline_ttyS_console_after_LK_commandline_review'
