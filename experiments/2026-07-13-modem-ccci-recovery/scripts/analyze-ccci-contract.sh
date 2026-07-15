#!/usr/bin/env bash

# Compare the vendor CCCI/CLDMA contract with Linux 7.1.3. The vendor tree is
# read from Git objects; no vendor source is copied into this repository.

set -eu
export LC_ALL=C

vendor_tree=${VENDOR_TREE:-/home/julien.guest/src/reference/planet-mt6797-3.18}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
repo_root=${REPO_ROOT:-/mnt/gemini-pda-mainline}
linux_files=(
  drivers/net/wwan/Kconfig
  drivers/net/wwan/wwan_core.c
  include/linux/wwan.h
  drivers/net/wwan/t7xx/t7xx_hif_cldma.c
  drivers/net/wwan/t7xx/t7xx_port_proxy.c
  drivers/net/wwan/t7xx/t7xx_netdev.c
  drivers/net/wwan/t7xx/t7xx_port_proxy.h
  drivers/net/wwan/rpmsg_wwan_ctrl.c
  drivers/net/wwan/mhi_wwan_ctrl.c
  drivers/net/wwan/mhi_wwan_mbim.c
  drivers/net/usb/qmi_wwan.c
  drivers/net/usb/cdc_mbim.c
)

[[ -d "$vendor_tree/.git" ]] || { printf 'missing vendor Git tree: %s\n' "$vendor_tree" >&2; exit 1; }
[[ -d "$linux_tree" ]] || { printf 'missing Linux tree: %s\n' "$linux_tree" >&2; exit 1; }

vendor_show() {
  git -C "$vendor_tree" show "HEAD:$1"
}

vendor_contains() {
  local path=$1
  local pattern=$2
  vendor_show "$path" | rg -F -- "$pattern" >/dev/null
}

vendor_hash() {
  vendor_show "$1" | sha256sum | awk '{print $1}'
}

linux_contains() {
  local path=$1
  local pattern=$2
  rg -F -- "$pattern" "$linux_tree/$path" >/dev/null
}

printf 'vendor_tree=%s\n' "$vendor_tree"
printf 'vendor_commit=%s\n' "$(git -C "$vendor_tree" rev-parse HEAD)"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_commit=%s\n' "$(git -C "$linux_tree" rev-parse --verify HEAD 2>/dev/null || printf unknown)"
for path in "${linux_files[@]}"; do
  printf 'linux_blob_sha256[%s]=%s\n' "$path" "$(sha256sum "$linux_tree/$path" | awk '{print $1}')"
done

printf '\n[vendor CCCI configuration]\n'
vendor_show drivers/misc/mediatek/eccci/mt6797/ccci_config.h \
  | rg -n 'FEATURE_|CCCI_(MTU|NET_MTU|SMEM|DRIVER_VER)|MD_HEADER|MEM_LAY_OUT|AP_MD_HS' \
  | head -n 220 || true

printf '\n[vendor CCCI memory and port layout]\n'
vendor_show drivers/misc/mediatek/eccci/ccci_modem.c \
  | rg -n -C 2 'get_md_resv_mem_info|get_md1_md3_resv_smem_info|md_region_phy|smem_region_phy|CCCI_SMEM_OFFSET|ccci_set_mem_remap|runtime_feature' \
  | head -n 260 || true
vendor_show drivers/misc/mediatek/eccci/mt6797/ccci_config.h \
  | rg -n 'CCCI_SMEM_OFFSET|CCCI_SMEM_SIZE|CCCI_SMEM_(CCISM|CCIF)|CCCI_MTU|CCCI_NET_MTU' \
  | head -n 220 || true
vendor_show drivers/misc/mediatek/eccci/port_cfg.c \
  | rg -n 'ccmni[0-9]+|cc3mni[0-9]+|ttyC|ccci_(im|raw|fs|rpc|aud|monitor)|get_md_port_cfg' \
  | head -n 260 || true

printf '\n[vendor MT6797 CLDMA/CCIF resources]\n'
vendor_show drivers/misc/mediatek/eccci/mt6797/cldma_platform.c \
  | rg -n -C 2 'of_iomap|irq_of_parse|devm_clk_get|md_id|cldma_capability|sram_size|md_rgu_base|md_boot_slave|md_cldma_hw_reset' \
  | head -n 300 || true
vendor_show drivers/misc/mediatek/eccci/mt6797/cldma_reg.h \
  | rg -n 'CLDMA_AP_(TQ|RQ|UL|SO|L2|L3|BUS|CHNL)|CLDMA_BM|cldma_(read|write)' \
  | head -n 220 || true
vendor_show drivers/misc/mediatek/eccci/mt6797/ccci_platform.c \
  | rg -n -C 2 'MPU_REGION_ID_MD|MPU_ACCESS_PERMISSON|set_md_(smem|rom_rw)_mem_remap|ccci_set_mem_remap|PCCIF|CCIF_SRAM' \
  | head -n 320 || true

printf '\n[vendor DT declarations]\n'
vendor_show arch/arm64/boot/dts/mt6797.dtsi \
  | rg -n -C 2 'reserve-memory-ccci|ccci_util_cfg|mdcldma|ap_cldma|md_cldma|ap_ccif|md_ccif|md_smem_size|cldma_capability' \
  | head -n 340 || true

printf '\n[Linux 7.1.3 WWAN scope]\n'
rg -n -C 2 'config MTK_T7XX|depends on PCI|DPMAIF|CLDMA|wwan_register_ops|struct ccci_header' \
  "$linux_tree/drivers/net/wwan/Kconfig" \
  "$linux_tree/drivers/net/wwan/t7xx" \
  | head -n 320 || true

printf '\n[local Gemini modem declarations]\n'
if [ -r "$repo_root/patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch" ]; then
  rg -n -i 'ccci|cldma|ccif|modem|md_smem' \
    "$repo_root/patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch" || true
else
  echo 'local_patch=not_visible_from_guest'
fi

printf '\n[normalized MT6797 CCCI contract]\n'
printf 'vendor_source_hashes='
for path in \
  drivers/misc/mediatek/eccci/mt6797/ccci_config.h \
  drivers/misc/mediatek/eccci/mt6797/cldma_reg.h \
  drivers/misc/mediatek/eccci/mt6797/modem_reg_base.h \
  drivers/misc/mediatek/eccci/modem_cldma.h \
  drivers/misc/mediatek/eccci/modem_ccif.h \
  drivers/misc/mediatek/eccci/ccci_ringbuf.h \
  drivers/misc/mediatek/eccci/ccci_core.h \
  drivers/misc/mediatek/eccci/port_proxy.h \
  drivers/misc/mediatek/include/mt-plat/mt_ccci_common.h \
  drivers/misc/mediatek/eccci/mt6797/cldma_platform.c \
  drivers/misc/mediatek/eccci/mt6797/ccci_platform.c \
  drivers/misc/mediatek/eccci/port_cfg.c \
  arch/arm64/boot/dts/mt6797.dtsi; do
  printf '%s:%s;' "$path" "$(vendor_hash "$path")"
done
printf '\n'

if vendor_contains drivers/misc/mediatek/eccci/mt6797/ccci_config.h '#define CCCI_MTU            (3584-128)' &&
  vendor_contains drivers/misc/mediatek/eccci/mt6797/ccci_config.h '#define CCCI_NET_MTU        (1500)' &&
  vendor_contains drivers/misc/mediatek/eccci/mt6797/ccci_config.h '#define MD_HEADER_VER_NO    (3)' &&
  vendor_contains drivers/misc/mediatek/eccci/mt6797/ccci_config.h '#define MEM_LAY_OUT_VER     (1)'; then
  echo 'wire_header=ccci_header:16-byte;data0/data1:u32;channel:u16;seq:u15;assert:u1;reserved:u32;mtu:3456;net_mtu:1500;header_version:3;memory_layout_version:1'
else
  echo 'wire_header=not-confirmed'
fi

if vendor_contains drivers/misc/mediatek/eccci/modem_cldma.h '#define CLDMA_TXQ_NUM 8' &&
  vendor_contains drivers/misc/mediatek/eccci/modem_cldma.h '#define CLDMA_RXQ_NUM 8' &&
  vendor_contains drivers/misc/mediatek/eccci/modem_cldma.h '#define NET_TXQ_NUM 3' &&
  vendor_contains drivers/misc/mediatek/eccci/modem_cldma.h '#define NORMAL_TXQ_NUM 6' &&
  vendor_contains drivers/misc/mediatek/eccci/modem_cldma.h 'struct cldma_tgpd {' &&
  vendor_contains drivers/misc/mediatek/eccci/modem_cldma.h 'struct cldma_rgpd {' &&
  vendor_contains drivers/misc/mediatek/eccci/modem_cldma.h 'struct cldma_tbd {' &&
  vendor_contains drivers/misc/mediatek/eccci/modem_cldma.h 'struct cldma_rbd {'; then
  echo 'cldma_queues=8-tx+8-rx;3-network-tx+3-network-rx;6-normal-tx+6-normal-rx;descriptor=TGPD/RGPD/TBD/RBD;36-bit-address-high-nibble-in-debug_or_reserved'
else
  echo 'cldma_queues=not-confirmed'
fi

if vendor_contains drivers/misc/mediatek/eccci/modem_ccif.h '#define QUEUE_NUM   8' &&
  vendor_contains drivers/misc/mediatek/eccci/modem_ccif.h '#define FLOW_CTRL_HEAD' &&
  vendor_contains drivers/misc/mediatek/eccci/modem_ccif.h 'struct ccif_sram_layout {' &&
  vendor_contains drivers/misc/mediatek/eccci/ccci_ringbuf.h 'struct ccci_ringbuf {'; then
  echo 'ccif=8-tx+8-rx-queues;flow_magic=FLOW/CTRL;SRAM=down_header+MD_runtime+up_header+AP_runtime;ring=shared-rx_write_tx_read-controls'
else
  echo 'ccif=not-confirmed'
fi

if vendor_contains drivers/misc/mediatek/eccci/mt6797/cldma_platform.c 'hw_info->cldma_ap_ao_base = (unsigned long)of_iomap' &&
  vendor_contains drivers/misc/mediatek/eccci/mt6797/cldma_platform.c 'hw_info->md_ccif_base = (unsigned long)of_iomap' &&
  vendor_contains arch/arm64/boot/dts/mt6797.dtsi 'mediatek,cldma_capability = <6>;' &&
  vendor_contains arch/arm64/boot/dts/mt6797.dtsi 'mediatek,md_smem_size = <0x100000>'; then
  echo 'platform_resources=6-DT-reg-windows;CLDMA-capability:6;MD1-smem:0x100000;IRQs:CLDMA265+CCIF147+MDWDT266'
else
  echo 'platform_resources=not-confirmed'
fi

if vendor_contains arch/arm64/boot/dts/mt6797.dtsi '<0x10014000 0x1e00>' &&
  vendor_contains arch/arm64/boot/dts/mt6797.dtsi '<0x10219000 0x1e00>' &&
  vendor_contains arch/arm64/boot/dts/mt6797.dtsi '<0x10209000 0x1000>' &&
  vendor_contains arch/arm64/boot/dts/mt6797.dtsi '<0x1020a000 0x1000>'; then
  echo 'windows=AP_CLDMA_AO:0x10014000/0x1e00;MD_CLDMA_AO:0x10015000/0x1e00;AP_CLDMA_PDN:0x10219000/0x1e00;MD_CLDMA_PDN:0x1021a000/0x1e00;AP_CCIF:0x10209000/0x1000;MD_CCIF:0x1020a000/0x1000'
else
  echo 'windows=not-confirmed'
fi

if vendor_contains drivers/misc/mediatek/eccci/mt6797/cldma_platform.c 'scp-sys-md1-main' &&
  vendor_contains drivers/misc/mediatek/eccci/mt6797/cldma_platform.c 'infra-md2md-ccif-5'; then
  echo 'clock_contract=scp-sys-md1-main;infra-ccif-ap/md;infra-ap-c2k-ccif-0/1;infra-md2md-ccif-0..5'
else
  echo 'clock_contract=not-confirmed'
fi

if vendor_contains drivers/misc/mediatek/eccci/mt6797/ccci_platform.c '#define MPU_REGION_ID_MD1_ROM           11' &&
  vendor_contains drivers/misc/mediatek/eccci/mt6797/ccci_platform.c '#define MPU_REGION_ID_MD1_RW            14' &&
  vendor_contains drivers/misc/mediatek/eccci/mt6797/ccci_platform.c '#define MPU_REGION_ID_MD3_ROM           16' &&
  vendor_contains drivers/misc/mediatek/eccci/mt6797/ccci_platform.c '#define MPU_REGION_ID_MD3_RW            17'; then
  echo 'emi_mpu=MD1-ROM:11;MD1-RW:14;MD3-ROM:16;MD3-RW:17;clear/protect-staged-by-boot-environment'
else
  echo 'emi_mpu=not-confirmed'
fi

if vendor_contains drivers/misc/mediatek/eccci/port_cfg.c '"ccmni17"' &&
  vendor_contains drivers/misc/mediatek/eccci/port_cfg.c '"cc3mni7"'; then
  echo 'port_map=MD1-ccmni0..17;MD3-cc3mni0..7;channel/queue mapping is private port_proxy ABI'
else
  echo 'port_map=not-confirmed'
fi

if linux_contains drivers/net/wwan/Kconfig 'config MTK_T7XX' &&
  linux_contains drivers/net/wwan/Kconfig 'depends on PCI'; then
  echo 'linux_reuse=WWAN/TTY/netdev-interfaces;linux_t7xx=PCIe-DPMAIF-only-not-transport-match'
else
  echo 'linux_reuse=not-confirmed'
fi

echo 'new_backend=MT6797-platform-CCCI/CLDMA/CCIF;shared-memory-layout;firmware-handshake;reset;EMI-MPU-owner'
echo 'abi_boundary=do-not-port-vendor-ccci-char-ioctl-or-Android-EEMCS-UAPI'
echo 'safe_next_step=disabled-resource-only;recover-bootloader-reservations-and-non-transmitting-state-machine-before-rings'
echo 'hardware_write=none'

printf '\n[decision]\n'
printf '%s\n' \
  'live_CCCI_MD1_and_C2K_MD3_ports_are_active_but_are_private_vendor_ABI' \
  'MT6797_CLDMA_uses_APB_memory_mapped_windows_CCIF_and_vendor_clock_domain' \
  'Linux_t7xx_CLDMA_is_PCIe_DPMAIF_specific_and_is_not_a_Gemini_transport_match' \
  'reuse_WWAN_netdev_and_tty_subsystems_only_after_a_new_MT6797_CCCI_transport' \
  'preserve_CCCI_reserved_memory_and_EMI_MPU_ownership_before_any_modem_probe'
