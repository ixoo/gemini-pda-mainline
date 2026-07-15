#!/usr/bin/env bash

# Emit the MT6797 SuperSpeed PHY contract without copying vendor code into the
# repository. Run this in the development VM; both source trees are immutable
# evidence.

set -euo pipefail
export LC_ALL=C

vendor_tree=${1:-${HOME}/src/reference/planet-mt6797-3.18}
linux_tree=${2:-${HOME}/src/gemini-pda/linux-7.1.3}
vendor_files=(
	drivers/misc/mediatek/mu3phy/mtk-phy.h
	drivers/misc/mediatek/mu3phy/mtk-phy-a60810.c
	drivers/misc/mediatek/mu3phy/mt6797/mtk-phy-asic.c
	drivers/misc/mediatek/mu3phy/mt6797/mtk-phy-asic.h
	drivers/misc/mediatek/mu3d/hal/mu3d_hal_hw.h
)
usb11_files=(
	drivers/misc/mediatek/usb11/mt6797/musbfsh_mt65xx.c
	drivers/misc/mediatek/usb11/mt6797/musbfsh_mt65xx.h
	drivers/misc/mediatek/usb11/musbfsh_regs.h
)
linux_phy=${linux_tree}/drivers/phy/mediatek/phy-mtk-tphy.c
linux_binding=${linux_tree}/Documentation/devicetree/bindings/phy/mediatek,tphy.yaml

[[ -d "${vendor_tree}/.git" ]] || {
	printf 'vendor tree is not a git checkout: %s\n' "${vendor_tree}" >&2
	exit 1
}
[[ -r "${linux_phy}" && -r "${linux_binding}" ]] || {
	printf 'Linux T-PHY sources are missing below: %s\n' "${linux_tree}" >&2
	exit 1
}

blob_hash() {
	local path=$1
	git -C "${vendor_tree}" show "HEAD:${path}" | sha256sum | awk '{print $1}'
}

printf 'vendor_tree=%s\n' "${vendor_tree}"
printf 'vendor_commit=%s\n' "$(git -C "${vendor_tree}" rev-parse HEAD)"
for path in "${vendor_files[@]}"; do
	printf 'vendor_blob_sha256[%s]=%s\n' "${path}" "$(blob_hash "${path}")"
done
for path in "${usb11_files[@]}"; do
	printf 'vendor_blob_sha256[%s]=%s\n' "${path}" "$(blob_hash "${path}")"
done
printf 'linux_tree=%s\n' "${linux_tree}"
printf 'linux_tphy_sha256=%s\n' "$(sha256sum "${linux_phy}" | awk '{print $1}')"
printf 'linux_tphy_binding_sha256=%s\n' "$(sha256sum "${linux_binding}" | awk '{print $1}')"

printf '\n[vendor physical bank contract]\n'
git -C "${vendor_tree}" show "HEAD:${vendor_files[4]}" |
	grep -nE 'SSUSB_SIFSLV_(IPPC|SPLLC|U2PHY_COM|U3PHYD)|SSUSB_USB30_PHYA|u3_sif(_base|2_base)' || true
git -C "${vendor_tree}" show HEAD:arch/arm64/boot/dts/mt6797.dtsi |
	grep -nE -A14 -B2 'usb3_phy|usb3_sif@11280000|usb3_sif2@11290000|usb3@11270000' || true

printf '\n[vendor init and tuning boundaries]\n'
git -C "${vendor_tree}" show "HEAD:${vendor_files[2]}" |
	grep -nE 'phy_init_soc|u3_sif_base|u3_sif2_base|pmic_set_register_value|U3PhyWrite(Field|Reg)|u2_slew_rate_calibration|of_match|compatible' |
	head -n 180 || true
git -C "${vendor_tree}" show "HEAD:${vendor_files[1]}" |
	grep -nE 'phy_init_a60810|PLL_SSC|PLL_(BC|DIVEN|IC|BR|IR|BP)|HSTX_SRCTRL|change_pipe_phase' |
	head -n 120 || true

printf '\n[vendor USB11 V1/PHY contract]\n'
git -C "${vendor_tree}" show "HEAD:${usb11_files[1]}" |
	grep -nE 'USB11_L1INT|USB11_PHY_ADDR|USB_SIF_BASE|RG_USB11|force_usb11' || true
git -C "${vendor_tree}" show "HEAD:${usb11_files[0]}" |
	grep -nE -A8 -B5 'mt65xx_usb11_phy_poweron_common|usb11_hs_slew_rate_cal|phy_poweron_volt|phy_savecurrent|phy_recover|USB11PHY_(SET|CLR)8' |
	head -n 260 || true
printf '\n[vendor USB11 slew helper exact source anchors]\n'
git -C "${vendor_tree}" show "HEAD:${usb11_files[0]}" |
	sed -n '700,768p' || true
printf '\n[vendor USB11 defconfig symbols]\n'
git -C "${vendor_tree}" show HEAD:arch/arm64/configs/lineage_gemini_defconfig |
	grep -nE 'CONFIG_MTK_(DT_USB|ICUSB|MUSBFSH_QMU|MUSB_QMU)' || true
git -C "${vendor_tree}" show "HEAD:arch/arm64/boot/dts/mt6797.dtsi" |
	grep -nE -A12 -B2 'usb1@11200000|usb1p_sif@11210000' || true

printf '\n[Linux T-PHY generations and matches]\n'
sed -n '20,48p' "${linux_phy}"
grep -nE 'compatible =|mt2701|mt2712|mt8195|generic-tphy|version =|slew_ref_clock|avoid_rx_sen|sw_efuse' \
	"${linux_phy}" "${linux_binding}" | head -n 180 || true
grep -nE -A12 -B5 'U3P_USBPHYACR0|U3P_U2PHYDTM0|U3P_U2PHYDTM1|u2_phy_instance_(init|power_on|set_mode)|hs_slew_rate_calibrate|SSUSB_SIFSLV_V1_U2FREQ' \
	"${linux_phy}" | head -n 260 || true
printf '\n[Linux fixed slew suppression path]\n'
grep -nE -A14 -B4 'if \(instance->eye_src|PA5_RG_U2_HSTX_SRCTRL' \
	"${linux_phy}" | head -n 100 || true

printf '\n[decision]\n'
printf '%s\n' \
	'MT6797 uses the same broad T-PHY U2/U3 register protocol and per-port bank shape as MediaTek T-PHY V1.' \
	'Its shared SPLLC/FM banks live in SIF2 while IPPC reset/power control lives at SIF+0x700; Linux V1/V2 resource parsing cannot express this topology unchanged.' \
	'USB11 is a closer V1 U2 match: its SIF+0x800 child maps to the V1 U2PHY_COM bank and the vendor power-on fields match Linux U2PHYACR/DTM fields.' \
	'USB11 calibration is different: generic V1 FMREG is SIF+0x100, while the vendor USB11 helper writes its meter at SIF+0xf00; with the captured config ICUSB is unset, so poweron_volt_50 enters that helper, whose source unconditionally takes the timeout fallback and programs slew value 4 (MTK_DT_USB_SUPPORT would early-return); alternate ICUSB builds skip it; do not run generic calibration unchanged.' \
	'Linux already provides a safe fixed-slew escape: a nonzero mediatek,eye-src property skips hs_slew_rate_calibrate and u2_phy_props_set programs PA5_RG_U2_HSTX_SRCTRL; a USB11 candidate can use eye-src=4 without touching generic parent+0x100 FMREG.' \
	'Reuse Linux T-PHY helpers and PHY framework with an MT6797-specific resource/bank variant when possible.' \
	'Add explicit USB11 bias, calibration-suppression, and runtime save-current/recover hooks; add a standalone MT6797 PHY driver only if these cannot be represented cleanly.' \
	'Do not copy vendor PLL/eye tuning tables or enable a DT node until register identity, clocks, supplies, and electrical behavior are validated.'
