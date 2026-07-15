#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Compare the archived Gemini charger/fuel-gauge contract with the prepared
# Linux 7.1.3 tree.  This is a source-only audit: it reads Git objects and
# the prepared source tree, never touches an I2C bus, and never writes device
# registers or power-supply properties.

set -euo pipefail

VENDOR_TREE=${VENDOR_TREE:-"$HOME/src/reference/gemian-linux-kernel-3.18"}
LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}

die() {
	echo "error: $*" >&2
	exit 1
}

command -v git >/dev/null || die "git is required"
command -v rg >/dev/null || die "rg is required"
command -v sha256sum >/dev/null || die "sha256sum is required"

[[ -d "$VENDOR_TREE/.git" ]] || die "vendor tree is not a Git checkout: $VENDOR_TREE"
[[ -d "$LINUX_TREE" ]] || die "Linux tree is missing: $LINUX_TREE"

vendor_exists() {
	git -C "$VENDOR_TREE" cat-file -e "HEAD:$1" 2>/dev/null
}

vendor_blob() {
	if vendor_exists "$1"; then
		git -C "$VENDOR_TREE" rev-parse "HEAD:$1"
	else
		echo missing
	fi
}

vendor_show() {
	vendor_exists "$1" || return 0
	git -C "$VENDOR_TREE" show "HEAD:$1"
}

vendor_anchor() {
	local path=$1
	local pattern=$2
	if vendor_exists "$path"; then
		git -C "$VENDOR_TREE" show "HEAD:$path" | rg -n -m 18 "$pattern" || true
	else
		echo "(missing: $path)"
	fi
}

vendor_count() {
	local path=$1
	local pattern=$2
	if vendor_exists "$path"; then
		vendor_show "$path" | rg -c "$pattern" || true
	else
		echo missing
	fi
}

linux_hash() {
	if [[ -f "$LINUX_TREE/$1" ]]; then
		sha256sum "$LINUX_TREE/$1" | awk '{print $1}'
	else
		echo missing
	fi
}

linux_anchor() {
	local path=$1
	local pattern=$2
	if [[ -f "$LINUX_TREE/$path" ]]; then
		rg -n -m 18 "$pattern" "$LINUX_TREE/$path" || true
	else
		echo "(missing: $path)"
	fi
}

echo "MT6797 charger/fuel-gauge contract audit"
echo "vendor_tree=$VENDOR_TREE"
echo "vendor_commit=$(git -C "$VENDOR_TREE" rev-parse HEAD)"
echo "linux_tree=$LINUX_TREE"
if [[ -f "$LINUX_TREE/Makefile" ]]; then
	printf 'linux_version='
	make -s -C "$LINUX_TREE" kernelversion
fi

echo
echo "[source identities]"
for path in \
	drivers/misc/mediatek/power/mt6797/bq25890.c \
	drivers/misc/mediatek/power/mt6797/bq25890.h \
	drivers/misc/mediatek/power/mt6797/charging_hw_bq25890.c \
	drivers/misc/mediatek/power/mt6797/fan49101.c \
	drivers/misc/mediatek/power/mt6797/fan49101.h \
	drivers/misc/mediatek/power/mt6797/rt9466.c \
	drivers/misc/mediatek/power/mt6797/rt9466.h \
	drivers/misc/mediatek/power/mt6797/battery_meter_hal.c \
	drivers/misc/mediatek/power/mt6797/mtk_charger_intf.c \
	arch/arm64/boot/dts/rt9466.dtsi \
	arch/arm64/boot/dts/mt6797.dts; do
	printf 'vendor_blob %s %s\n' "$path" "$(vendor_blob "$path")"
done
for path in \
	drivers/power/supply/bq25890_charger.c \
	Documentation/devicetree/bindings/power/supply/bq25890.yaml \
	drivers/regulator/fan53555.c \
	drivers/power/supply/rt9467-charger.c \
	drivers/iio/adc/mt6577_auxadc.c \
	drivers/power/supply/mt6351_battery.c \
	drivers/power/supply/mt6370-charger.c; do
	printf 'linux_sha256 %s %s\n' "$path" "$(linux_hash "$path")"
done

echo
echo "[vendor BQ25890 charger]"
vendor_anchor drivers/misc/mediatek/power/mt6797/bq25890.c \
	'bq25890_of_match|I2C_BOARD_INFO|bq25890_hw_component_detect|set_iinlim|set_ichg|set_vreg|dump_register|power_supply'
printf 'vendor_bq25890_helper_call_hits=%s\n' \
	"$(vendor_count drivers/misc/mediatek/power/mt6797/charging_hw_bq25890.c 'bq25890_[a-z0-9_]+\(')"
vendor_anchor drivers/misc/mediatek/power/mt6797/charging_hw_bq25890.c \
	'bq25890_set_(iinlim|ichg|vreg|iterm|sys_min)|bq25890_[a-z0-9_]+\('

echo
echo "[vendor FAN49101 buck-boost]"
vendor_anchor drivers/misc/mediatek/power/mt6797/fan49101.c \
	'FAN49101_ID|fan49101_hw_component_detect|fan49101_hw_init|fan49101_access|fan49101_vosel|#if 0|VSEL|I2C_BOARD_INFO|of_match|regulator|i2c'
printf 'vendor_fan49101_write_path_hits=%s\n' \
	"$(vendor_count drivers/misc/mediatek/power/mt6797/fan49101.c 'fan49101_.*write|config_interface')"

echo
echo "[vendor RT9466 alternative]"
vendor_anchor drivers/misc/mediatek/power/mt6797/rt9466.c \
	'rt9466_driver|rt9466_of_match|I2C_BOARD_INFO|component_detect|set_|power_supply|regmap|charger'
vendor_anchor arch/arm64/boot/dts/rt9466.dtsi \
	'rt9466@53|compatible|interrupt|charger_name|ichg|aicr|mivr|cv|ieoc|status'

echo
echo "[vendor battery meter and charger ABI]"
vendor_anchor drivers/misc/mediatek/power/mt6797/battery_meter_hal.c \
	'battery_meter_hal|read_adc_v_charger|GET_HW_FG|GET_ADC_V_BAT|fgauge_read|columb|battery_profile'
vendor_anchor drivers/misc/mediatek/power/mt6797/mtk_charger_intf.c \
	'wireless_charger|charger_type|CHARGER_UNKNOWN|STANDARD_CHARGER|power_supply|battery_meter'

echo
echo "[vendor DT alternatives]"
vendor_anchor arch/arm64/boot/dts/mt6797.dts \
	'bq24261|sw_charger|bq25890|fan49101|rt9466|battery|batterypseudo|charger_current|status'

echo
echo "[Linux BQ25890 power-supply contract]"
linux_anchor drivers/power/supply/bq25890_charger.c \
	'bq25890_power_supply|bq25890_probe|of_match|POWER_SUPPLY_PROP_(STATUS|ONLINE|CURRENT_NOW|VOLTAGE_NOW|CONSTANT_CHARGE_CURRENT|CONSTANT_CHARGE_VOLTAGE)'
linux_anchor Documentation/devicetree/bindings/power/supply/bq25890.yaml \
	'compatible|ti,battery-regulation-voltage|ti,charge-current|ti,termination-current|ti,precharge-current|ti,minimum-sys-voltage|ti,boost-voltage|interrupts|reg:'

echo
echo "[BQ25890 identity gate]"
echo "vendor_presence_probe=register_0x03_nonzero_only"
vendor_anchor drivers/misc/mediatek/power/mt6797/bq25890.c \
	'bq25890_read_interface\(0x03|Reg\[0x03\]'
echo "linux_identity_probe=register_0x14_PN_bits_3_5_and_DEV_REV_bits_0_1"
linux_anchor drivers/power/supply/bq25890_charger.c \
	'F_PN|F_DEV_REV|Unknown chip ID|Unknown device revision|BQ25890_ID|BQ25895_ID|BQ25896_ID'
echo "identity_result=vendor_register_layout_supports_reuse_but_live_part_number_is_unproven"

echo
echo "[Linux nearest-but-not-equivalent regulator and charger drivers]"
linux_anchor drivers/regulator/fan53555.c \
	'fan53555_dt_ids|FAN53555_VENDOR|regmap|vsel|fcs,fan53555|silergy,syr82'
linux_anchor drivers/power/supply/rt9467-charger.c \
	'rt9467|compatible|regmap|POWER_SUPPLY_PROP|reg_field|regmap_irq'
linux_anchor drivers/iio/adc/mt6577_auxadc.c \
	'mt6765_compat|compatible|iio_chan_spec|mt6577_auxadc_read|reg_base'

echo
echo "[decision]"
echo "Reuse the upstream BQ25890 power-supply core only after the live ID, IRQ,"
echo "battery/system-rail wiring, and safe charge limits are proven. The vendor"
echo "mediatek,sw_charger ABI and stale bq24261 DT node are not Linux bindings."
echo "FAN49101 is a distinct buck-boost protocol: its ID registers, VSEL and"
echo "enable behavior do not establish compatibility with fan53555. Add a new"
echo "regulator driver/binding unless a verified register-level match is found."
echo "Keep the unbound RT9466 node disabled until population and IRQ wiring are"
echo "proven; its DT values are not charge-safety evidence. Replace the vendor"
echo "battery meter/HAL with standard power_supply plus IIO/fuel-gauge pieces,"
echo "and do not copy vendor battery profiles without calibration and provenance."
