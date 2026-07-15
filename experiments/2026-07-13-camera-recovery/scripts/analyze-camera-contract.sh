#!/usr/bin/env bash

# Emit a source/binary metadata comparison for the camera boundary. The
# vendor userspace tree is immutable evidence; no proprietary binary is copied
# or modified.

set -eu
export LC_ALL=C

vendor_tree=${VENDOR_TREE:-/home/julien.guest/src/reference/planet-mt6797-3.18}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
userspace=${VENDOR_USERSPACE:-/home/julien.guest/reverse-engineering/gemini-vendor}

[[ -d "$vendor_tree" ]] || { printf 'missing vendor tree: %s\n' "$vendor_tree" >&2; exit 1; }
[[ -d "$linux_tree" ]] || { printf 'missing Linux tree: %s\n' "$linux_tree" >&2; exit 1; }

printf 'vendor_tree=%s\n' "$vendor_tree"
printf 'vendor_commit=%s\n' "$(git -C "$vendor_tree" rev-parse HEAD 2>/dev/null || printf unknown)"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'userspace=%s\n' "$userspace"

printf '\n[vendor camera declarations]\n'
sed -n '1,90p' "$vendor_tree/arch/arm64/boot/dts/cust_i2c.dtsi"
rg -n -C 2 '(camera_pins_cam[012]_(rst|pnd)|camera_pins_cam_ldo|kd_camera_hw[12]|seninf[0-7])' \
	"$vendor_tree/arch/arm64/boot/dts/aeon6797_6m_n.dts" \
	"$vendor_tree/arch/arm64/boot/dts/mt6797.dtsi" | head -n 260

printf '\n[private camera library hashes]\n'
for file in \
	"$userspace/system/vendor/lib64/hw/camera.mt6797.so" \
	"$userspace/system/vendor/lib64/libcameracustom.so" \
	"$userspace/system/vendor/lib64/libSonyIMX230PdafLibrary.so"; do
	[[ -r "$file" ]] || continue
	sha256sum "$file"
done

printf '\n[private HAL sensor registrations]\n'
strings -a "$userspace/system/vendor/lib64/libcameracustom.so" 2>/dev/null | \
	rg -i '(SENSOR_DRVNAME_|SP5509|OV5675|S5K5E2YA|PDAF)' | sort -u | head -n 180 || true

printf '\n[vendor SP5509 source coverage]\n'
if rg -l -i 'sp5509mipiraw|sp5509mainmipiraw' \
	"$vendor_tree/drivers/misc/mediatek/imgsensor/src/mt6797" \
	2>/dev/null | head -n 40; then
	printf 'vendor_sensor_source=present_in_pinned_planet_tree_main_and_sls_implementations\n'
else
	printf 'vendor_sensor_source=not_found_in_expected_mt6797_imgsensor_paths\n'
fi

printf '\n[Linux sensor coverage]\n'
find "$linux_tree/drivers/media/i2c" -maxdepth 1 -type f | \
	rg -i '(ov5675|sp5509|s5k5e2|sensor)' | sort | head -n 160
if rg -n -i '(sp5509|s5k5e2)' "$linux_tree/drivers/media" \
	"$linux_tree/Documentation/devicetree/bindings/media"; then
	printf 'linux_sensor_match=present\n'
else
	printf 'linux_sensor_match=absent_for_sp5509_and_s5k5e2\n'
fi

printf '\n[Linux MT6797 camera resources]\n'
sha256sum "$linux_tree/drivers/clk/mediatek/clk-mt6797-cam.c"
rg -n -C 3 '(camsys|imgsys|larb2|larb6|seninf|status = "disabled")' \
	"$linux_tree/arch/arm64/boot/dts/mediatek/mt6797.dtsi" | head -n 240
find "$linux_tree/drivers/media/platform/mediatek" -maxdepth 3 -type f | \
	rg -i '(cam|csi|seninf|isp)' | sort | head -n 160

printf '\n[decision]\n'
printf '%s\n' \
	'runtime AEON_CAMERA1 identity is sp5509mipirawsls; vendor alternatives are not populated evidence' \
	'Linux 7.1.3 has no SP5509 sensor driver or binding; do not substitute OV5675 by compatible-string change' \
	'reuse MT6797 clock/SMI/IOMMU/power building blocks where register contracts match' \
	'add a new SP5509 V4L2 sensor driver and a separate MT6797 SENINF/ISP media pipeline boundary' \
	'keep sensor, camera wrapper, and ISP consumers disabled until address, lanes, reset, supplies, and DMA ownership are measured'
