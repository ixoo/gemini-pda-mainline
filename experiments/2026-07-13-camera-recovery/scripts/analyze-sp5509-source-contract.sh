#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Recover the SP5509 sensor contract from the pinned Planet source and compare
# it with Linux 7.1.3.  This is source-only: it never copies vendor code,
# accesses an I2C bus, or writes a kernel/device artifact.

set -euo pipefail
export LC_ALL=C

VENDOR_TREE=${VENDOR_TREE:-"$HOME/src/reference/planet-mt6797-3.18"}
LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}

die() {
	echo "error: $*" >&2
	exit 1
}

command -v git >/dev/null || die "git is required"
command -v rg >/dev/null || die "rg is required"
command -v sha256sum >/dev/null || die "sha256sum is required"
command -v find >/dev/null || die "find is required"

[[ -d "$VENDOR_TREE/.git" ]] || die "vendor source tree is not a Git checkout: $VENDOR_TREE"
[[ -d "$LINUX_TREE/.git" ]] || die "Linux source tree is not a Git checkout: $LINUX_TREE"

vendor_show() {
	local path=$1
	git -C "$VENDOR_TREE" show "HEAD:$path"
}

vendor_hash() {
	vendor_show "$1" | sha256sum | awk '{print $1}'
}

linux_file() {
	local path=$1
	[[ -f "$LINUX_TREE/$path" ]] || die "missing Linux source: $path"
	echo "$LINUX_TREE/$path"
}

linux_hash() {
	sha256sum "$(linux_file "$1")" | awk '{print $1}'
}

vendor_contains() {
	local path=$1
	local pattern=$2
	# Avoid rg -q: with pipefail, its early exit can make git show report
	# SIGPIPE and turn a real match into a false negative.
	vendor_show "$path" | rg -F -- "$pattern" >/dev/null
}

vendor_contains_regex() {
	local path=$1
	local pattern=$2
	vendor_show "$path" | rg -- "$pattern" >/dev/null
}

linux_contains() {
	local path=$1
	local pattern=$2
	rg -F -- "$pattern" "$(linux_file "$path")" >/dev/null
}

sls=drivers/misc/mediatek/imgsensor/src/mt6797/sp5509_mipi_raw_sls/sp5509mipiraw_Sensor.c
sls_h=drivers/misc/mediatek/imgsensor/src/mt6797/sp5509_mipi_raw_sls/sp5509mipiraw_Sensor.h
main=drivers/misc/mediatek/imgsensor/src/mt6797/sp5509_main_mipi_raw/sp5509mainmipiraw_Sensor.c
main_h=drivers/misc/mediatek/imgsensor/src/mt6797/sp5509_main_mipi_raw/sp5509mainmipiraw_Sensor.h
ids=drivers/misc/mediatek/imgsensor/inc/kd_imgsensor.h
sensor_list=drivers/misc/mediatek/imgsensor/src/mt6797/kd_sensorlist.h
camera_hw=drivers/misc/mediatek/imgsensor/src/mt6797/camera_hw/kd_camera_hw.c
camera_hw_h=drivers/misc/mediatek/imgsensor/src/mt6797/camera_hw/kd_camera_hw.h
board_dts=arch/arm64/boot/dts/aeon6797_6m_n.dts

for path in "$sls" "$sls_h" "$main" "$main_h" "$ids" "$sensor_list" \
	"$camera_hw" "$camera_hw_h" "$board_dts"; do
	vendor_show "$path" >/dev/null || die "missing vendor source: $path"
done
linux_file drivers/media/i2c/ov5675.c >/dev/null
linux_file Documentation/devicetree/bindings/media/i2c/ovti,ov5675.yaml >/dev/null

echo "SP5509 source contract audit"
echo "vendor_tree=$VENDOR_TREE"
echo "vendor_revision=$(git -C "$VENDOR_TREE" rev-parse --verify HEAD)"
echo "linux_tree=$LINUX_TREE"
echo "linux_revision=$(git -C "$LINUX_TREE" rev-parse --verify HEAD 2>/dev/null || echo unknown)"
echo "linux_version=$(make -s -C "$LINUX_TREE" kernelversion)"
echo

echo "[source hashes]"
for path in "$sls" "$sls_h" "$main" "$main_h" "$ids" "$sensor_list" \
	"$camera_hw" "$camera_hw_h" "$board_dts"; do
	printf 'vendor_sha256 %s %s\n' "$path" "$(vendor_hash "$path")"
done
printf 'linux_sha256 drivers/media/i2c/ov5675.c %s\n' "$(linux_hash drivers/media/i2c/ov5675.c)"
printf 'linux_sha256 Documentation/devicetree/bindings/media/i2c/ovti,ov5675.yaml %s\n' \
	"$(linux_hash Documentation/devicetree/bindings/media/i2c/ovti,ov5675.yaml)"

echo
echo "[vendor implementation presence]"
if vendor_contains "$sls" 'sp5509_MIPI_RAW_SensorInit_sls' &&
	vendor_contains "$main" 'sp5509_MAIN_MIPI_RAW_SensorInit'; then
	echo "vendor_sp5509_implementations=main+sls-present"
else
	echo "vendor_sp5509_implementations=not-confirmed"
fi
if vendor_contains "$sensor_list" 'SP5509_MIPI_RAW_SLS' &&
	vendor_contains "$sensor_list" 'SP5509_MAIN_MIPI_RAW'; then
	echo "vendor_sp5509_registration=conditional-sensor-list-entries"
else
	echo "vendor_sp5509_registration=not-confirmed"
fi
if vendor_contains "$ids" 'SP5509_SENSOR_ID_SLS' &&
	vendor_contains "$ids" '0x556' && vendor_contains "$ids" 'SP5509_MAIN_SENSOR_ID' &&
	vendor_contains "$ids" '0x557'; then
	echo "vendor_sp5509_ids=sls:0x556;main:0x557"
else
	echo "vendor_sp5509_ids=not-confirmed"
fi

echo
echo "[SLS identity and bus contract]"
if vendor_contains "$sls" '.sensor_id = SP5509_SENSOR_ID_SLS' &&
	vendor_contains "$sls" 'read_cmos_sensor(0x0f16)' &&
	vendor_contains "$sls" 'return read_cmos_sensor(0x0f16)'; then
	echo "sls_identity=16bit-register:0x0f16;raw-id:0x0556;no-main-plus-one-adjustment"
else
	echo "sls_identity=not-confirmed"
fi
if vendor_contains "$main" 'return (read_cmos_sensor(0x0f16)+1)' &&
	vendor_contains "$main" '.sensor_id = SP5509_MAIN_SENSOR_ID'; then
	echo "main_identity=16bit-register:0x0f16;raw-id-plus-one:0x0557"
else
	echo "main_identity=not-confirmed"
fi
if vendor_contains "$sls" 'i2c_addr_table = {0x40,0x50,0xff}' &&
	vendor_contains "$main" 'i2c_addr_table = {0x50,0x40,0xff}' &&
	vendor_contains "$sls" 'i2c_speed = 300'; then
	echo "sls_i2c=vendor-write-ids:0x40,0x50;linux-7bit:0x20,0x28;speed:300kHz"
else
	echo "sls_i2c=not-confirmed"
fi
if vendor_contains "$sls" 'char pu_send_cmd[2]' &&
	vendor_contains "$sls" 'iReadRegI2C(pu_send_cmd, 2' &&
	vendor_contains "$sls" 'iWriteRegI2C(pusendcmd , 4'; then
	echo "sls_i2c_format=16bit-register-address;16bit-big-endian-value;read-2+2-bytes;write-4-bytes"
else
	echo "sls_i2c_format=not-confirmed"
fi

echo
echo "[SLS image and mode contract]"
if vendor_contains "$sls" 'mclk = 24' &&
	vendor_contains "$sls" 'mipi_lane_num = SENSOR_MIPI_2_LANE' &&
	vendor_contains "$sls" 'SENSOR_OUTPUT_FORMAT_RAW_Gr' &&
	vendor_contains "$sls" 'mipi_sensor_type = MIPI_OPHY_NCSI2'; then
	echo "sls_link=24MHz-mclk;2-lane-MIPI-NCSI2;RAW_Gr;manual-settle"
else
	echo "sls_link=not-confirmed"
fi
if vendor_contains "$sls" 'pclk = 176000000' &&
	vendor_contains "$sls" 'linelength  = 2816' &&
	vendor_contains "$sls" 'framelength = 2083' &&
	vendor_contains "$sls" 'grabwindow_width  = 2592' &&
	vendor_contains "$sls" 'grabwindow_height = 1944'; then
	echo "sls_timing=preview-capture-video:2592x1944;pclk:176MHz;line:2816;frame:2083;30fps-class"
else
	echo "sls_timing=not-confirmed"
fi
if vendor_contains_regex "$sls" 'grabwindow_width[[:space:]]*=[[:space:]]*640' &&
	vendor_contains "$sls" 'grabwindow_height = 480' &&
	vendor_contains "$sls" 'max_framerate = 1200' &&
	vendor_contains_regex "$sls" 'grabwindow_width[[:space:]]*=[[:space:]]*1296' &&
	vendor_contains "$sls" 'grabwindow_height = 972'; then
	echo "sls_secondary_modes=high-speed:640x480:120fps-class;slim:1296x972:30fps-class"
else
	echo "sls_secondary_modes=not-confirmed"
fi
if vendor_contains "$sls" 'write_cmos_sensor(0x0a12, 0x0a20)' &&
	vendor_contains "$sls" 'write_cmos_sensor(0x0a14, 0x0798)' &&
	vendor_contains "$sls" 'write_cmos_sensor(0x0902, 0x4319)'; then
	echo "sls_mode_registers=output-size:0x0a12/0x0a14;MIPI-op:0x0902;source-table-present"
else
	echo "sls_mode_registers=not-confirmed"
fi

echo
echo "[power and module selection]"
if vendor_contains "$camera_hw" 'SENSOR_DRVNAME_SP5509_RAW_SLS' &&
	vendor_contains "$camera_hw" '{DOVDD, Vol_1800, 10}' &&
	vendor_contains "$camera_hw" '{AVDD, Vol_2800, 10}' &&
	vendor_contains "$camera_hw" '{DVDD, Vol_1200, 10}' &&
	vendor_contains "$camera_hw" '{RST, Vol_High, 10}' &&
	vendor_contains "$camera_hw" '{PDN, Vol_High, 10}'; then
	echo "sls_power_sequence=MCLK;reset-low;PDN-low;DOVDD-1.8V;AVDD-2.8V;DVDD-1.2V;reset-high;PDN-high;10ms-steps"
else
	echo "sls_power_sequence=not-confirmed"
fi
if vendor_contains "$board_dts" 'PINMUX_GPIO32__FUNC_GPIO32' &&
	vendor_contains "$board_dts" 'PINMUX_GPIO28__FUNC_GPIO28' &&
	vendor_contains "$board_dts" 'PINMUX_GPIO33__FUNC_GPIO33' &&
	vendor_contains "$board_dts" 'PINMUX_GPIO29__FUNC_GPIO29' &&
	vendor_contains "$board_dts" 'PINMUX_GPIO73__FUNC_GPIO73' &&
	vendor_contains "$board_dts" 'PINMUX_GPIO254__FUNC_GPIO254'; then
	echo "vendor_camera_pins=cam0-reset:GPIO32;cam0-PDN:GPIO28;cam1-reset:GPIO33;cam1-PDN:GPIO29;vcama-gpio:GPIO73;vcamd-gpio:GPIO254"
else
	echo "vendor_camera_pins=not-confirmed"
fi
if vendor_contains "$sls" 'mainsubcam_flag==0' &&
	vendor_contains "$main" 'mainsubcam_flag==1'; then
	echo "vendor_module_selection=SLS-when-sub-flag-nonzero;main-when-flag-zero"
else
	echo "vendor_module_selection=not-confirmed"
fi

echo
echo "[Linux 7.1.3 comparison]"
if find "$LINUX_TREE/drivers/media" -type f -iname '*sp5509*' | rg -i -- 'sp5509' >/dev/null; then
	echo "linux_sp5509_driver=present"
else
	echo "linux_sp5509_driver=missing"
fi
if linux_contains drivers/media/i2c/ov5675.c 'v4l2_ctrl_new_std' &&
	linux_contains drivers/media/i2c/ov5675.c 'regulator_bulk'; then
	echo "linux_sensor_reuse=v4l2-subdev+controls+regulator-bulk+mode-register-lists"
else
	echo "linux_sensor_reuse=not-confirmed"
fi
if linux_contains Documentation/devicetree/bindings/media/i2c/ovti,ov5675.yaml 'data-lanes' &&
	linux_contains Documentation/devicetree/bindings/media/i2c/ovti,ov5675.yaml 'link-frequencies'; then
	echo "linux_endpoint_model=fwnode-data-lanes+link-frequencies"
else
	echo "linux_endpoint_model=not-confirmed"
fi

echo
echo "[decision]"
echo "reusable=V4L2-subdev+media-controller+fwnode-endpoint+regulator/clock/reset+standard-controls"
echo "new=SP5509-sensor-driver;MT6797-SENINF/ISP-capture-backend;board-specific-module-selection"
echo "source_caveat=vendor-comments-contain-Hi556/0x30c8-stale-text;use-symbols-and-register-code-not-comments"
echo "safe_next_step=add-disabled-sensor-contract-only;do-not-probe-I2C-or-write-mode-registers"
echo "hardware_write=none"
