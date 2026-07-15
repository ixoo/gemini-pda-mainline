#!/usr/bin/env bash

set -euo pipefail

linux_tree="${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}"
vendor_tree="${VENDOR_TREE:-/home/julien.guest/src/reference/planet-mt6797-3.18}"
driver_rel=drivers/i2c/busses/i2c-mt65xx.c
linux_dtsi_rel=arch/arm64/boot/dts/mediatek/mt6797.dtsi
vendor_dtsi_rel=arch/arm64/boot/dts/mt6797.dtsi
binding_rel=Documentation/devicetree/bindings/i2c/i2c-mt65xx.yaml

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

[[ -r "$linux_tree/$driver_rel" ]] || die "missing Linux driver: $linux_tree/$driver_rel"
[[ -r "$linux_tree/$linux_dtsi_rel" ]] || die "missing Linux DTSI: $linux_tree/$linux_dtsi_rel"
[[ -r "$linux_tree/$binding_rel" ]] || die "missing Linux binding: $linux_tree/$binding_rel"
git -C "$vendor_tree" rev-parse --verify HEAD >/dev/null || die "vendor tree is not a Git checkout"
git -C "$vendor_tree" cat-file -e "HEAD:$driver_rel" || die "vendor driver is absent from HEAD"
git -C "$vendor_tree" cat-file -e "HEAD:$vendor_dtsi_rel" 2>/dev/null || {
		vendor_dtsi_rel=arch/arm64/boot/dts/mt6797.dtsi
}
git -C "$vendor_tree" cat-file -e "HEAD:$vendor_dtsi_rel" || die "vendor DTSI is absent from HEAD"

printf 'validation=i2c-mt6797-controller-reuse\n'
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_driver_sha256=%s\n' "$(sha256_file "$linux_tree/$driver_rel")"
printf 'linux_dtsi_sha256=%s\n' "$(sha256_file "$linux_tree/$linux_dtsi_rel")"
printf 'linux_binding_sha256=%s\n' "$(sha256_file "$linux_tree/$binding_rel")"
printf 'vendor_tree=%s\n' "$vendor_tree"
printf 'vendor_commit=%s\n' "$(git -C "$vendor_tree" rev-parse HEAD)"
printf 'vendor_driver_sha256=%s\n' "$(sha256_git_path "$vendor_tree" "$driver_rel")"
printf 'vendor_dtsi_sha256=%s\n' "$(sha256_git_path "$vendor_tree" "$vendor_dtsi_rel")"
printf 'current_mt6797_i2c_nodes=%s\n' "$(grep -c 'compatible = \"mediatek,mt6797-i2c\"' "$linux_tree/$linux_dtsi_rel")"
printf 'current_mt6577_fallbacks=%s\n' "$(grep -c 'mediatek,mt6577-i2c' "$linux_tree/$linux_dtsi_rel")"
printf 'vendor_mt6797_i2c_nodes=%s\n' "$(git -C "$vendor_tree" show "HEAD:$vendor_dtsi_rel" | grep -c 'compatible = \"mediatek,mt6797-i2c\"')"

printf '\n[current_driver_profile]\n'
sed -n '379,391p' "$linux_tree/$driver_rel"
printf '\n[current_match_table]\n'
sed -n '526,539p' "$linux_tree/$driver_rel"
printf '\n[current_binding_mt6797]\n'
grep -n -A3 -B2 'mediatek,mt6797-i2c' "$linux_tree/$binding_rel"
printf '\n[current_optional_clocks]\n'
grep -n -A6 -B2 'devm_clk_get_optional' "$linux_tree/$driver_rel"

printf '\n[vendor_match_table]\n'
git -C "$vendor_tree" show "HEAD:$driver_rel" | sed -n '187,234p'
