#!/usr/bin/env bash

# Recover the vendor SII9022/Sil9024A bridge contract without executing the
# vendor kernel or copying its private HDMI ABI.  The ELF and source tree are
# immutable evidence in the development VM.

set -eu
export LC_ALL=C

VMLINUX=${VMLINUX:-/home/julien.guest/reverse-engineering/work/gemini-kernel/vmlinux.elf}
VENDOR_TREE=${VENDOR_TREE:-/home/julien.guest/src/reference/planet-mt6797-3.18}
LINUX_TREE=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}

[[ -r "$VMLINUX" ]] || { printf 'missing vendor ELF: %s\n' "$VMLINUX" >&2; exit 1; }
[[ -d "$VENDOR_TREE/.git" ]] || { printf 'missing vendor tree: %s\n' "$VENDOR_TREE" >&2; exit 1; }
[[ -d "$LINUX_TREE" ]] || { printf 'missing Linux tree: %s\n' "$LINUX_TREE" >&2; exit 1; }

printf 'vmlinux=%s\n' "$VMLINUX"
printf 'vmlinux_sha256=%s\n' "$(sha256sum "$VMLINUX" | awk '{print $1}')"
printf 'vendor_tree=%s\n' "$VENDOR_TREE"
printf 'vendor_commit=%s\n' "$(git -C "$VENDOR_TREE" rev-parse HEAD)"
printf 'linux_tree=%s\n' "$LINUX_TREE"

printf '\n[vendor source hashes]\n'
for file in \
	arch/arm64/boot/dts/sil9024a.dtsi \
	arch/arm64/boot/dts/mt6797.dtsi \
	drivers/misc/mediatek/hdmi/sil9024/hdmi_drv.c \
	drivers/misc/mediatek/hdmi/sil9024/siHdmiTx_902x_TPI.c \
	drivers/misc/mediatek/hdmi/sil9024/siHdmiTx_902x_TPI.h; do
	printf '%s ' "$file"
	git -C "$VENDOR_TREE" cat-file blob "HEAD:$file" | sha256sum | awk '{print $1}'
done

printf '\n[vendor source identity and transport]\n'
git -C "$VENDOR_TREE" show HEAD:drivers/misc/mediatek/hdmi/sil9024/siHdmiTx_902x_TPI.h |
	rg -n -C 2 'TPI Firmware|SII902XA_DEVICE_ID|TX_HW_RESET_PERIOD|INDEXED_PAGE_0' || true
git -C "$VENDOR_TREE" show HEAD:drivers/misc/mediatek/hdmi/sil9024/siHdmiTx_902x_TPI.c |
	rg -n -C 3 'StartTPI|ReadIndexedRegister\(INDEXED_PAGE_0|ReadByteTPI\(0x1B\)|wID == 0x9022|HDMI_reset|DoEdidRead|siiReadSegmentBlockEDID|i2c_smbus_read_byte_data' |
	head -n 220 || true

printf '\n[ELF symbols]\n'
nm -an "$VMLINUX" |
	rg -i ' (sil902|sii902|HDMI_I2C|DoEdid|CheckEDID|ParseEDID)' || true

printf '\n[ELF pinctrl strings]\n'
strings -tx "$VMLINUX" |
	rg -i 'sil9022_(rst|1v2|eint|dpi|i2s)|hdmi_hotplug_det' || true

printf '\n[ELF reset/power helper calls]\n'
objdump -d --no-show-raw-insn \
	--start-address=0xffffffc00056ba90 \
	--stop-address=0xffffffc00056bb18 "$VMLINUX" |
	rg -e '<HDMI_reset>' -e 'sil9022_set_reset' -e '__const_udelay' -e 'mov[[:space:]]+x19, #0x(14|32|50)' || true
objdump -d --no-show-raw-insn \
	--start-address=0xffffffc00056c680 \
	--stop-address=0xffffffc00056c860 "$VMLINUX" |
	rg -e '^[[:xdigit:]]+ <' -e 'pinctrl_select_state' -e 'mov[[:space:]]+w19' -e '#0x(14|32|50)' || true

printf '\n[ELF bridge I2C transaction shape]\n'
objdump -d --no-show-raw-insn \
	--start-address=0xffffffc00056f110 \
	--stop-address=0xffffffc00056f200 "$VMLINUX" |
	rg -e 'HDMI_I2C_' -e 'strh' -e 'str[[:space:]]+x2' -e 'i2c_transfer' -e 'mov[[:space:]]+w[234]' -e 'subs' -e '#0x[125]' || true

printf '\n[ELF identity checks]\n'
objdump -d --no-show-raw-insn \
	--start-address=0xffffffc00056e868 \
	--stop-address=0xffffffc00056e8e0 "$VMLINUX" |
	rg -e '<StartTPI>' -e 'ReadIndexedRegister' -e 'i2c_smbus_read_byte_data' -e '#0x9022' -e '#0xb0' -e '#0x1b' || true

printf '\n[ELF probe and EDID calls]\n'
objdump -d --no-show-raw-insn \
	--start-address=0xffffffc00056bfd0 \
	--stop-address=0xffffffc00056c290 "$VMLINUX" |
	rg -e 'strcmp' -e 'HDMI_reset' -e 'pinctrl_select_state' -e 'of_find_compatible_node' -e 'of_property_read_u32_array' -e 'irq_of_parse_and_map' -e 'request_threaded_irq' -e 'sil9024_irq_handler' -e 'mov[[:space:]]+w[0-9]+, #0x' |
	head -n 180 || true
objdump -d --no-show-raw-insn \
	--start-address=0xffffffc00056d1e0 \
	--stop-address=0xffffffc00056d364 "$VMLINUX" |
	rg -e 'GetDDC_Access' -e 'i2c_smbus_read_byte_data' -e 'ParseEDID' -e 'Parse861Extensions' -e 'ReleaseDDC' -e '#0x(80|b|c)' || true

printf '\n[mainline comparison]\n'
sha256sum "$LINUX_TREE/drivers/gpu/drm/bridge/sii902x.c"
sha256sum "$LINUX_TREE/Documentation/devicetree/bindings/display/bridge/sil,sii9022.yaml"
rg -n -C 3 'SII902X_REG_CHIPID|chipid\[0\]|sii902x_reset|reset-gpios|iovcc-supply|cvcc12-supply|bus-width|compatible.*sil,sii9022' \
	"$LINUX_TREE/drivers/gpu/drm/bridge/sii902x.c" \
	"$LINUX_TREE/Documentation/devicetree/bindings/display/bridge/sil,sii9022.yaml" |
	head -n 220 || true

printf '\n[decision]\n'
printf '%s\n' \
	'vendor_source_and_elf_identify_sii902x_family: indexed_id_0x9022_and_tpi_id_0xb0' \
	'vendor_bridge_uses_i2c_smbus_byte_data_and_separate_edid_client_at_0x50' \
	'vendor_reset_sequence_is_high_20ms_low_50ms_high_20ms_and_1v2_gpio247_is_enabled_before_probe' \
	'vendor_dpi_bus_is_16_lines_gpio39_to_gpio54_and_i2s_gpio135_to_gpio141' \
	'linux_sii902x_is_protocol_compatible_but_requires_standard_supplies_reset_and_drm_graph' \
	'live_clients_remain_unbound_and_no_chip_id_or_edid_bytes_were_read' \
	'keep_external_display_disabled_until_population_and_graph_are_verified;do_not_port_vendor_hdmitx_abi'
