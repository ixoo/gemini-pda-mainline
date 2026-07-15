#!/usr/bin/env bash

# Static, read-only closure check for the current packaged Gemini kernel.
# This runs in the development VM; it never boots or writes a device.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
config=${CONFIG_FILE:-$package/kernel.config}
system_map=${SYSTEM_MAP:-$package/System.map}
dtb=${DTB_FILE:-$package/dtbs/mediatek/mt6797-gemini-pda.dtb}

for file in "$config" "$system_map" "$dtb"; do
	[[ -r "$file" ]] || { printf 'missing readable input: %s\n' "$file" >&2; exit 1; }
done
command -v dtc >/dev/null || { echo 'dtc is required' >&2; exit 1; }

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
dts=$tmpdir/gemini.dts
dtc -I dtb -O dts "$dtb" 2>/dev/null > "$dts"

assert_config() {
	local setting=$1
	grep -Fxq -- "$setting" "$config" || {
		printf 'missing_config=%s\n' "$setting" >&2
		exit 1
	}
	printf 'config=%s\n' "$setting"
}

assert_symbol() {
	local symbol=$1
	rg -q "[[:space:]]${symbol}$" "$system_map" || {
		printf 'missing_system_map_symbol=%s\n' "$symbol" >&2
		exit 1
	}
	printf 'symbol=%s\n' "$symbol"
}

assert_dts() {
	local label=$1
	local pattern=$2
	rg -q -- "$pattern" "$dts" || {
		printf 'missing_dtb_contract=%s pattern=%s\n' "$label" "$pattern" >&2
		exit 1
	}
	printf 'dtb=%s\n' "$label"
}

assert_node_property() {
	local node=$1
	local property=$2
	awk -v wanted="$node" '
		$0 ~ wanted "[[:space:]]*\\{" { inside = 1 }
		inside { print }
		inside && $0 ~ /^[[:space:]]*};/ { exit }
	' "$dts" | rg -q -- "$property" || {
		printf 'missing_node_property=node:%s pattern:%s\n' "$node" "$property" >&2
		exit 1
	}
	printf 'dtb=%s.%s\n' "$node" "$property"
}

printf 'package=%s\n' "$package"
printf 'package_sha256=%s\n' "$(sha256sum "$package/Image" | awk '{print $1}')"
printf 'config_sha256=%s\n' "$(sha256sum "$config" | awk '{print $1}')"
printf 'dtb_sha256=%s\n' "$(sha256sum "$dtb" | awk '{print $1}')"

for setting in \
	CONFIG_ARM64=y \
	CONFIG_MMU=y \
	CONFIG_OF=y \
	CONFIG_ARM_PSCI_FW=y \
	CONFIG_ARM_ARCH_TIMER=y \
	CONFIG_ARM_GIC_V3=y \
	CONFIG_SERIAL_EARLYCON=y \
	CONFIG_SERIAL_8250=y \
	CONFIG_SERIAL_8250_CONSOLE=y \
	CONFIG_SERIAL_8250_MT6577=y \
	CONFIG_SERIAL_OF_PLATFORM=y \
	CONFIG_DEVTMPFS=y \
	CONFIG_DEVTMPFS_MOUNT=y \
	CONFIG_BLK_DEV_INITRD=y \
	CONFIG_MMC_MTK=y \
	CONFIG_MEDIATEK_WATCHDOG=y \
	'CONFIG_INITRAMFS_SOURCE=""'; do
	assert_config "$setting"
done

for symbol in psci_dt_init arch_timer_starting_cpu mtk8250_probe serial8250_register_8250_port msdc_drv_probe mtk_wdt_probe; do
	assert_symbol "$symbol"
done

assert_dts model 'model = "Planet Computers Gemini PDA";'
assert_dts compatible 'compatible = "planet,gemini-pda\\0mediatek,mt6797";'
assert_dts serial_alias 'serial0 = "/serial@11002000";'
assert_dts psci 'compatible = "arm,psci-0.2";'
assert_dts psci_method 'method = "smc";'
assert_dts stdout 'stdout-path = "serial0:921600n8";'
assert_dts memory 'reg = <0x00 0x40000000 0x01 0x00>;'
assert_dts uart_compatible 'compatible = "mediatek,mt6797-uart\\0mediatek,mt6577-uart";'
assert_dts uart_reg 'reg = <0x00 0x11002000 0x00 0x400>;'
assert_dts uart_irq 'interrupts = <0x00 0x5b 0x08>;'
assert_dts uart_clocks 'clock-names = "baud\\0bus";'
assert_node_property 'serial@11002000' 'status = "okay";'
assert_dts mmc_compatible 'compatible = "mediatek,mt6797-mmc";'
assert_dts mmc_reg 'reg = <0x00 0x11230000 0x00 0x10000>;'
assert_dts mmc_irq 'interrupts = <0x00 0x4f 0x08>;'
assert_node_property 'mmc@11230000' 'status = "okay";'
assert_dts mmc_bus_width 'bus-width = <0x08>;'
assert_dts mmc_max_frequency 'max-frequency = <0x17d7840>;'

for node in \
	reserve-memory-ccci_md1 \
	reserve-memory-ccci_share \
	consys-reserve-memory \
	spm-reserve-memory \
	reserve-memory-scp_share; do
	assert_dts "dynamic_$node" "${node}[[:space:]]*\\{"
done

if rg -q 'framebuffer|atf-log|log-store' "$dts"; then
	echo 'unexpected_post_lk_static_reservation_name' >&2
	exit 1
fi
printf 'dtb=post_lk_static_reservation_names_absent\n'
printf 'validation=static-mainline-handoff-closure\n'
printf 'runtime_mainline_boot=not_attempted\n'
printf 'hardware_write=none\n'
