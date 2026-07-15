#!/usr/bin/env bash

# Emit the MT6797 connectivity transport contract without copying vendor code
# into the repository. The vendor checkout may be sparse, so all vendor files
# are read from Git objects. This report is source-only and never powers radios
# or performs an SDIO/BTIF transaction.

set -euo pipefail
export LC_ALL=C

vendor_tree=${1:-${HOME}/src/reference/planet-mt6797-3.18}
linux_tree=${2:-${HOME}/src/gemini-pda/linux-7.1.3}
vendor_files=(
	drivers/misc/mediatek/connectivity/common/common_main/mt6797/include/mtk_wcn_consys_hw.h
	drivers/misc/mediatek/connectivity/common/common_main/mt6797/mtk_wcn_consys_hw.c
	drivers/misc/mediatek/connectivity/common/common_main/mt6797/wmt_plat_alps.c
	drivers/misc/mediatek/connectivity/common/common_main/core/include/stp_core.h
	drivers/misc/mediatek/connectivity/common/common_main/core/stp_core.c
	drivers/misc/mediatek/connectivity/common/common_main/linux/stp_btif.c
	drivers/misc/mediatek/connectivity/common/common_main/linux/stp_sdio.c
	drivers/misc/mediatek/connectivity/common/common_main/linux/stp_uart.c
	drivers/misc/mediatek/connectivity/common/common_main/linux/wmt_dev.c
	drivers/misc/mediatek/connectivity/common/common_main/linux/hif_sdio.c
	drivers/misc/mediatek/connectivity/common/common_detect/sdio_detect.c
	drivers/misc/mediatek/btif/common/inc/mtk_btif.h
	drivers/misc/mediatek/btif/common/plat_inc/btif_priv.h
	drivers/misc/mediatek/btif/common/btif_plat.c
	drivers/misc/mediatek/btif/common/btif_dma_plat.c
	drivers/misc/mediatek/connectivity/wlan/gen2/os/linux/hif/ahb/include/hif_pdma.h
	drivers/misc/mediatek/connectivity/wlan/gen2/os/linux/hif/ahb/mt6797/ahb_pdma.c
)
linux_files=(
	drivers/bluetooth/btmtkuart.c
	drivers/bluetooth/btmtksdio.c
	drivers/bluetooth/btmtk.c
	drivers/gnss/mtk.c
)

[[ -d "${vendor_tree}/.git" ]] || {
	printf 'vendor tree is not a Git checkout: %s\n' "${vendor_tree}" >&2
	exit 1
}
[[ -r "${linux_tree}/drivers/bluetooth/btmtkuart.c" ]] || {
	printf 'Linux Bluetooth sources are missing below: %s\n' "${linux_tree}" >&2
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

printf '\n[vendor consys power and identity]\n'
vendor_show "${vendor_files[0]}" |
	grep -nE 'CONSYS_(TOP1_PWR_CTRL|PWR_CONN_ACK|CHIP_ID|TOPAXI|AFE_REG|CPU_SW_RST)|CONSYS_(SPM_PWR|SRAM_CONN|PWR_ON_ACK)' |
	head -n 120 || true
vendor_show "${vendor_files[1]}" |
	grep -nE 'of_match|mt6797-consys|regulator_get|vcn18|vcn28|vcn33|conn_power_(on|off)|CHIP_ID|ioremap|request_firmware' |
	head -n 180 || true
vendor_show "${vendor_files[2]}" |
	grep -nE 'mt6797-consys|irq_of_parse|BTIF_WAKEUP|PIN_BGF|pinctrl|GPS_LNA|wmt_plat_eirq_ctrl' |
	head -n 140 || true

printf '\n[vendor STP framing and transports]\n'
vendor_show "${vendor_files[3]}" |
	grep -nE 'MTKSTP_(UART|BTIF|SDIO)|MTKSTP_(CRC|HEADER|SEQ|BUFFER|WINSIZE)|MTKSTP_(SYNC|SEQ|ACK|NAK|TYPE|LENGTH|CHECKSUM|DATA)|stp_send_data' |
	head -n 160 || true
vendor_show "${vendor_files[4]}" |
	grep -nE 'stp_send_data_no_ps|mtkstp_header\[0\]|MTKSTP_(HEADER|CRC)_SIZE|osal_crc16|sys_if_tx|BT_TASK_INDX|WMT_TASK_INDX' |
	head -n 140 || true
vendor_show "${vendor_files[5]}" |
	grep -nE 'stp_btif_(open|tx|rx)|mtk_wcn_btif_(open|write|wakeup)|STP_MAX|retry|register_if_tx' |
	head -n 120 || true
vendor_show "${vendor_files[6]}" |
	grep -nE 'STP_SDIO_(BLK|FIFO|HDR|RETRY)|CCIR|CHLPCR|CHISR|CHIER|sdio_(read|write)|client_reg|FUNC' |
	head -n 180 || true
vendor_show "${vendor_files[7]}" |
	grep -nE 'N_MTKSTP|tty_register_ldisc|HCIUARTSETPROTO|stp_tty|register_if_tx' |
	head -n 100 || true
vendor_show "${vendor_files[8]}" |
	grep -nE 'WMT_DRIVER_NAME|stpwmt|WMT_(read|write|unlocked_ioctl)|WMT_IOCTL|register_chrdev|device_create|wmt_dev_patch' |
	head -n 160 || true

printf '\n[vendor SDIO identity and Wi-Fi HIF]\n'
vendor_show "${vendor_files[10]}" |
	grep -nE 'SDIO_DEVICE|0x037A|0x6628|0x6630|0x6632|sdio_register_driver|sdio_enable_func' |
	head -n 120 || true
vendor_show "${vendor_files[15]}" |
	grep -nE 'AP_DMA_HIF_BASE|AP_DMA_HIF_0_(INT_FLAG|INT_EN|EN|RST|CON|SRC_ADDR|DST_ADDR|LEN)|HIF_PDMA_BURST' |
	head -n 120 || true
vendor_show "${vendor_files[16]}" |
	grep -nE 'HifPdma|AP_DMA_HIF|clk|of_|irq|reset|emi_mpu|DMA' |
	head -n 160 || true

printf '\n[vendor BTIF register/DMA contract]\n'
vendor_show "${vendor_files[11]}" |
	grep -nE 'BTIF_(RX|TX)_BUFFER|ENABLE_BTIF|BTIF_(RX|TX)_MODE|BTIF_(RX|TX)_FIFO|rx_cb|open_counter' |
	head -n 120 || true
vendor_show "${vendor_files[12]}" |
	grep -nE 'BTIF_(RBR|THR|IER|IIR|FIFOCTRL|LSR|DMA_EN|RTOCNT|TRI_LVL|WAK|HANDSHAKE)|BTIF_(TX|RX)_FIFO_SIZE' |
	head -n 140 || true
vendor_show "${vendor_files[13]}" |
	grep -nE 'of_find_compatible_node|mediatek,btif|of_iomap|irq_of_parse|BTIF_BASE|MTK_BTIF_REG_BASE|BTIF_TX_FIFO_SIZE|BTIF_RX_FIFO_SIZE' |
	head -n 140 || true
vendor_show "${vendor_files[14]}" |
	grep -nE 'mediatek,btif_(tx|rx)|of_iomap|irq_of_parse|BTIF_(TX|RX)_DMA|VFF|vfifo|IRQ' |
	head -n 160 || true

printf '\n[Linux reusable layers]\n'
grep -nE 'MTK_STP_(TLR|STP)|prefix|dlen|H4_RECV|mediatek,mt|serdev|fwname|WMT_|BTMTK_WMT|of_device_id' \
	"${linux_tree}/drivers/bluetooth/btmtkuart.c" |
	head -n 220 || true
grep -nE 'SDIO_DEVICE|MT7663|MT7668|MT7921|MT7902|MTK_SDIO_BLOCK_SIZE|struct mtkbtsdio_hdr|request_firmware|FIRMWARE_MT' \
	"${linux_tree}/drivers/bluetooth/btmtksdio.c" |
	head -n 220 || true
grep -nE 'btmtk_setup_firmware|WMT|firmware|hci|mediatek' \
	"${linux_tree}/drivers/bluetooth/btmtk.c" |
	head -n 140 || true
grep -nE 'of_device_id|globaltop|pa6h|serdev|gnss|vcc|vbackup' \
	"${linux_tree}/drivers/gnss/mtk.c" |
	head -n 100 || true

printf '\n[decision]\n'
printf '%s\n' \
	'The vendor STP wire format is a reusable protocol layer: four-byte 0x80-prefixed length/type header, H:4 payload, two-byte trailer, and WMT vendor events align with Linux btmtkuart framing.' \
	'Gemini does not present that transport as a standard serdev UART in the recovered active path; BTIF and SDIO are the concrete transports, with custom DMA, wake, ownership, and IRQ handling.' \
	'Reuse Linux HCI, STP framing, firmware-loader, and cfg80211/GNSS cores where contracts match, but add an MT6797 consys power/firmware owner and a BTIF/SDIO transport driver or targeted extensions.' \
	'The vendor Wi-Fi gen2 code is a complete proprietary MAC/CFG80211 stack over an MT6797 AP-DMA HIF; it is not an mt76-compatible MAC. A new Wi-Fi driver/firmware boundary is required unless a separately documented upstream protocol implementation is found.' \
	'Keep WMT character devices, raw ioctl surfaces, radio power-on, firmware loading, and SDIO transactions out of the mainline default until ownership, licensing, and a non-transmitting bring-up protocol are proven.'
