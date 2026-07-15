#!/usr/bin/env bash

# Emit the MT6797 USB controller contract without copying vendor code into the
# repository. Run this in the development VM; both source trees are immutable
# evidence. The vendor checkout may be sparse, so vendor files are read from
# Git objects rather than the working tree.

set -euo pipefail
export LC_ALL=C

vendor_tree=${1:-${HOME}/src/reference/planet-mt6797-3.18}
linux_tree=${2:-${HOME}/src/gemini-pda/linux-7.1.3}
vendor_files=(
	drivers/misc/mediatek/mu3d/drv/musb_init.c
	drivers/misc/mediatek/mu3d/hal/mu3d_hal_hw.h
	drivers/misc/mediatek/mu3d/hal/ssusb_sifslv_ippc_c_header.h
	drivers/misc/mediatek/mu3d/hal/ssusb_dev_c_header.h
	drivers/misc/mediatek/mu3d/hal/ssusb_epctl_csr_c_header.h
	drivers/misc/mediatek/mu3d/hal/ssusb_usb2_csr_c_header.h
	drivers/misc/mediatek/mu3d/hal/ssusb_usb3_mac_csr_c_header.h
	drivers/misc/mediatek/usb11/mt6797/musbfsh_core.c
	drivers/misc/mediatek/usb11/mt6797/musbfsh_mt65xx.c
	drivers/misc/mediatek/usb11/mt6797/musbfsh_mt65xx.h
	drivers/misc/mediatek/usb11/musbfsh_regs.h
)
linux_files=(
	drivers/usb/mtu3/mtu3_hw_regs.h
	drivers/usb/mtu3/mtu3_plat.c
	drivers/usb/mtu3/mtu3_core.c
	drivers/usb/host/xhci-mtk.c
	drivers/usb/musb/mediatek.c
	"Documentation/devicetree/bindings/usb/mediatek,mtu3.yaml"
	"Documentation/devicetree/bindings/usb/mediatek,mtk-xhci.yaml"
)

[[ -d "${vendor_tree}/.git" ]] || {
	printf 'vendor tree is not a Git checkout: %s\n' "${vendor_tree}" >&2
	exit 1
}
[[ -r "${linux_tree}/drivers/usb/mtu3/mtu3_hw_regs.h" ]] || {
	printf 'Linux MTU3 sources are missing below: %s\n' "${linux_tree}" >&2
	exit 1
}

vendor_show() {
	git -C "${vendor_tree}" show "HEAD:$1"
}

blob_hash() {
	local path=$1
	vendor_show "${path}" | sha256sum | awk '{print $1}'
}

printf 'vendor_tree=%s\n' "${vendor_tree}"
printf 'vendor_commit=%s\n' "$(git -C "${vendor_tree}" rev-parse HEAD)"
for path in "${vendor_files[@]}"; do
	printf 'vendor_blob_sha256[%s]=%s\n' "${path}" "$(blob_hash "${path}")"
done
printf 'linux_tree=%s\n' "${linux_tree}"
printf 'linux_revision=7.1.3 (prepared source; no Git metadata required)\n'
for path in "${linux_files[@]}"; do
	printf 'linux_blob_sha256[%s]=%s\n' "${path}" "$(sha256sum "${linux_tree}/${path}" | awk '{print $1}')"
done

printf '\n[vendor USB3 register windows]\n'
vendor_show "${vendor_files[1]}" |
	grep -nE 'SSUSB_(DEV_BASE|EPCTL_CSR_BASE|USB3_MAC_CSR_BASE|USB3_SYS_CSR_BASE|USB2_CSR_BASE|SIFSLV_IPPC_BASE)' || true
vendor_show "${vendor_files[2]}" |
	grep -nE 'PW_CTRL[0-3]|PW_STS[12]|U3_CTRL_[0-9]P|U2_CTRL_[0-9]P' | head -n 80 || true
vendor_show "${vendor_files[0]}" |
	grep -nE 'mtu3d_data|mtu3d_probe|musb-hdrc|platform_device_add_resources|generic_interrupt|u3phy_ops|u3_base|u3_sif_base|u3_sif2_base' |
	head -n 100 || true
vendor_show arch/arm64/boot/dts/mt6797.dtsi |
	grep -nE -A18 -B2 'usb3@11270000|usb3_xhci@11270000|usb3_phy|usb3_sif@11280000|usb3_sif2@11290000' |
	head -n 180 || true

printf '\n[vendor USB1 contract]\n'
vendor_show "${vendor_files[7]}" |
	grep -nE 'of_match|mt6797-usb11|of_iomap|irq_of_parse|num_eps|\.mode|infra_icusb|sssub_ref_clk' |
	head -n 120 || true
vendor_show "${vendor_files[9]}" |
	grep -nE 'USB11_L1INT|USB11_PHY_ADDR|USB_SIF_BASE' || true

printf '\n[Linux MTU3 register/resource model]\n'
grep -nE 'SSUSB_(DEV_BASE|EPCTL_CSR_BASE|USB3_MAC_CSR_BASE|USB3_SYS_CSR_BASE|USB2_CSR_BASE|SIFSLV_IPPC_BASE)' \
	"${linux_tree}/drivers/usb/mtu3/mtu3_hw_regs.h"
grep -nE 'sys_ck|ref_ck|mcu_ck|dma_ck|xhci_ck|frmcnt_ck|ippc|mt8173-mtu3|mediatek,mtu3' \
	"${linux_tree}/drivers/usb/mtu3/mtu3_plat.c" \
	"${linux_tree}/Documentation/devicetree/bindings/usb/mediatek,mtu3.yaml" |
	head -n 140 || true

printf '\n[Linux xHCI/MUSB model]\n'
grep -nE 'mt8173-xhci|mt8195-xhci|mtk-xhci|reg-names|ippc|sys_ck|ref_ck|mcu_ck|dma_ck|xhci_ck|frmcnt_ck' \
	"${linux_tree}/drivers/usb/host/xhci-mtk.c" \
	"${linux_tree}/Documentation/devicetree/bindings/usb/mediatek,mtk-xhci.yaml" |
	head -n 140 || true
grep -nE 'USB_L1INT|main|mcu|univpll|num_eps|ram_bits|mtk-musb' \
	"${linux_tree}/drivers/usb/musb/mediatek.c" |
	head -n 100 || true

printf '\n[decision]\n'
printf '%s\n' \
	'USB3 controller register offsets are physically compatible with Linux MTU3 when the vendor windows are split: xHCI mac=0x11270000+0x1000, MTU3 mac=0x11271000+0x3000, and MTU3 ippc=0x11280700+0x100.' \
	'Reuse the Linux MTU3/xHCI MAC and IPPC code; add MT6797-compatible/binding and clock, rail, PHY, and role data only after those contracts are verified.' \
	'No new USB3 MAC driver is indicated by this source comparison. The vendor old MUSB wrapper and Type-C glue are separate integration boundaries.' \
	'USB1 uses the standard MUSB/Inventra register protocol but a distinct MT6797 USB11 SIF/PHY, level-1 interrupt map, six-endpoint host configuration, and clock contract.' \
	'Reuse the Linux MUSB core and common T-PHY V1 fields; add explicit MT6797 USB11 glue/data plus calibration, bias, and runtime-PM hooks, with a standalone driver only if those hooks cannot model the contract cleanly.' \
	'Keep all USB/PHY/role nodes disabled until read-only identity, clocks, supplies, port mapping, and a bounded device-only test are complete.'
