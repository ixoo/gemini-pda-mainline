#!/usr/bin/env bash

set -euo pipefail

linux_tree="${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}"
vendor_tree="${VENDOR_TREE:-/home/julien.guest/src/reference/planet-mt6797-3.18}"
linux_driver_rel=drivers/spi/spi-mt65xx.c
linux_binding_rel=Documentation/devicetree/bindings/spi/mediatek,spi-mt65xx.yaml
linux_clock_rel=drivers/clk/mediatek/clk-mt6797.c
vendor_driver_rel=drivers/spi/mediatek/mt6797/spi.c
vendor_hal_rel=drivers/spi/mediatek/mt6797/mt_spi_hal.h
vendor_dtsi_rel=arch/arm64/boot/dts/mt6797.dtsi

die() {
	printf 'error: %s\n' "$*" >&2
	exit 1
}

sha256_file() {
	sha256sum "$1" | awk '{ print $1 }'
}

sha256_git_path() {
	git -C "$1" show "HEAD:$2" | sha256sum | awk '{ print $1 }'
}

[[ -r "$linux_tree/$linux_driver_rel" ]] || die "missing Linux SPI driver"
[[ -r "$linux_tree/$linux_binding_rel" ]] || die "missing Linux SPI binding"
[[ -r "$linux_tree/$linux_clock_rel" ]] || die "missing MT6797 clock driver"
git -C "$vendor_tree" rev-parse --verify HEAD >/dev/null || die "vendor tree is not a Git checkout"
for path in "$vendor_driver_rel" "$vendor_hal_rel" "$vendor_dtsi_rel"; do
	git -C "$vendor_tree" cat-file -e "HEAD:$path" || die "vendor path absent: $path"
done

printf 'validation=spi-mt6797-controller-reuse\n'
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_spi_driver_sha256=%s\n' "$(sha256_file "$linux_tree/$linux_driver_rel")"
printf 'linux_spi_binding_sha256=%s\n' "$(sha256_file "$linux_tree/$linux_binding_rel")"
printf 'linux_mt6797_clock_driver_sha256=%s\n' "$(sha256_file "$linux_tree/$linux_clock_rel")"
printf 'vendor_tree=%s\n' "$vendor_tree"
printf 'vendor_commit=%s\n' "$(git -C "$vendor_tree" rev-parse HEAD)"
printf 'vendor_spi_driver_sha256=%s\n' "$(sha256_git_path "$vendor_tree" "$vendor_driver_rel")"
printf 'vendor_spi_hal_sha256=%s\n' "$(sha256_git_path "$vendor_tree" "$vendor_hal_rel")"
printf 'vendor_spi_dtsi_sha256=%s\n' "$(sha256_git_path "$vendor_tree" "$vendor_dtsi_rel")"

printf '\n[current_mt6765_profile]\n'
grep -n -A8 -B2 'static const struct mtk_spi_compatible mt6765_compat' \
	"$linux_tree/$linux_driver_rel"
printf '\n[current_match_and_binding]\n'
grep -n -A4 -B2 -E 'mt6765-spi|mt6797-spi' "$linux_tree/$linux_driver_rel" \
	"$linux_tree/$linux_binding_rel" || true
printf '\n[current_spi_clock_tree]\n'
grep -n -A5 -B2 -E 'spi_parents|CLK_TOP_MUX_SPI|CLK_INFRA_SPI([0-5]?)' \
	"$linux_tree/$linux_clock_rel" | head -120
printf '\n[vendor_register_layout]\n'
git -C "$vendor_tree" show "HEAD:$vendor_hal_rel" | grep -n -E \
	'SPI_(CFG0|CFG1|CFG2|CMD|PAD_SEL|STATUS|TX_SRC|RX_DST)_REG|SPI_CFG[012]_(SCK|CS|GET)' | head -100
printf '\n[vendor_spi_nodes]\n'
git -C "$vendor_tree" show "HEAD:$vendor_dtsi_rel" | grep -n -A14 -E \
	'^[[:space:]]*spi[0-5]:spi@' | head -180
