#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Recover the MT6797 CAM/SENINF/CAMSV/ISP resource contract from the pinned
# Planet source and compare it with Linux 7.1.3.  This is source-only: it
# never copies vendor code, maps device registers, or writes hardware.

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

isp=drivers/misc/mediatek/cameraisp/src/mt6797/camera_isp.c
isp_h=drivers/misc/mediatek/cameraisp/src/mt6797/inc/camera_isp.h
vendor_dtsi=arch/arm64/boot/dts/mt6797.dtsi
m4u_platform=drivers/misc/mediatek/m4u/mt6797/m4u_platform.h
linux_dtsi=arch/arm64/boot/dts/mediatek/mt6797.dtsi
linux_clk=drivers/clk/mediatek/clk-mt6797-cam.c
linux_clk_h=include/dt-bindings/clock/mt6797-clk.h
linux_larb=include/dt-bindings/memory/mt6797-larb-port.h

for path in "$isp" "$isp_h" "$vendor_dtsi" "$m4u_platform"; do
	vendor_show "$path" >/dev/null || die "missing vendor source: $path"
done
for path in "$linux_dtsi" "$linux_clk" "$linux_clk_h" "$linux_larb"; do
	linux_file "$path" >/dev/null
done

echo "MT6797 camera pipeline contract audit"
echo "vendor_tree=$VENDOR_TREE"
echo "vendor_revision=$(git -C "$VENDOR_TREE" rev-parse --verify HEAD)"
echo "linux_tree=$LINUX_TREE"
echo "linux_revision=$(git -C "$LINUX_TREE" rev-parse --verify HEAD 2>/dev/null || echo unknown)"
echo "linux_version=$(make -s -C "$LINUX_TREE" kernelversion)"
echo

echo "[source hashes]"
for path in "$isp" "$isp_h" "$vendor_dtsi" "$m4u_platform"; do
	printf 'vendor_sha256 %s %s\n' "$path" "$(vendor_hash "$path")"
done
for path in "$linux_dtsi" "$linux_clk" "$linux_clk_h" "$linux_larb"; do
	printf 'linux_sha256 %s %s\n' "$path" "$(linux_hash "$path")"
done

echo
echo "[vendor ISP platform contract]"
if vendor_contains "$isp" '#define ISP_DEV_NAME                "camera-isp"' &&
	vendor_contains "$isp" 'unlocked_ioctl = ISP_ioctl' &&
	vendor_contains "$isp" '.compatible = "mediatek,imgsys_config"' &&
	vendor_contains "$isp" '.compatible = "mediatek,camsv21"'; then
	echo "vendor_isp_abi=private-char-device:camera-isp;ioctl+mmap;12-platform-compatible-nodes"
else
	echo "vendor_isp_abi=not-confirmed"
fi
if vendor_contains "$isp_h" 'ISP_IMGSYS_CONFIG_IDX = 0' &&
	vendor_contains "$isp_h" 'ISP_CAM_A_IDX' &&
	vendor_contains "$isp_h" 'ISP_CAMSV5_IDX'; then
	echo "vendor_node_order=imgsys-config;dip-a;camsys;camtop;cam-a;cam-b;camsv00..camsv21"
else
	echo "vendor_node_order=not-confirmed"
fi
if vendor_contains "$vendor_dtsi" 'reg = <0x15000000  0x1000>' &&
	vendor_contains "$vendor_dtsi" 'reg = <0x1a004000 0x1000>' &&
	vendor_contains "$vendor_dtsi" 'reg = <0x1a005000 0x1000>' &&
	vendor_contains "$vendor_dtsi" 'reg = <0x1a055000 0x1000>'; then
	echo "vendor_isp_windows=imgsys:0x15000000/0x1000;cam-a:0x1a004000/0x1000;cam-b:0x1a005000/0x1000;camsv21:0x1a055000/0x1000"
else
	echo "vendor_isp_windows=not-confirmed"
fi
if vendor_contains "$vendor_dtsi" 'reg = <0x1a000000  0x1000>' &&
	vendor_contains "$vendor_dtsi" 'reg = <0x1a003000 0x1000>' &&
	vendor_contains "$vendor_dtsi" 'reg = <0x1a040000 0x1000>' &&
	vendor_contains "$vendor_dtsi" 'reg = <0x1a047000 0x1000>'; then
	echo "vendor_camera_windows=camsys:0x1a000000/0x1000;camtop:0x1a003000/0x1000;seninf0..7:0x1a040000..0x1a047000/0x1000"
else
	echo "vendor_camera_windows=not-confirmed"
fi
if vendor_contains "$vendor_dtsi" 'reg = <0x1a050000 0x1000>' &&
	vendor_contains "$vendor_dtsi" 'interrupts = <GIC_SPI 252 IRQ_TYPE_LEVEL_LOW>' &&
	vendor_contains "$vendor_dtsi" 'interrupts = <GIC_SPI 257 IRQ_TYPE_LEVEL_LOW>'; then
	echo "vendor_camera_irqs=camtop:SPI247;cama:SPI248;camb:SPI249;camsv00..21:SPI252..257;level-low"
else
	echo "vendor_camera_irqs=not-confirmed"
fi
if vendor_contains "$isp" 'of_find_compatible_node(NULL, NULL, "mediatek,seninf0")' &&
	vendor_contains "$isp" 'of_find_compatible_node(NULL, NULL, "mediatek,seninf3")' &&
	vendor_contains "$isp" 'ISP_IMGSYS_BASE + 0x8000'; then
	echo "vendor_seninf_mapping=explicit-seninf0..3-mapped;inner-imgsys-offsets:0x8000+;seninf4..7-not-mapped-by-legacy-isp-init"
else
	echo "vendor_seninf_mapping=not-confirmed"
fi
if vendor_contains "$isp_h" '#define MIPI_RX_BASE_HW 0x10217000' &&
	vendor_contains "$isp_h" '#define GPIO_BASE_HW    0x10002000'; then
	echo "vendor_aux_windows=mipi-rx-analog:0x10217000;gpio:0x10002000"
else
	echo "vendor_aux_windows=not-confirmed"
fi

echo
echo "[vendor clocks and IRQ semantics]"
if vendor_contains "$isp" 'devm_clk_get(&pDev->dev, "ISP_CAM_LARB2")' &&
	vendor_contains "$isp" 'devm_clk_get(&pDev->dev, "ISP_CAM_SENINF")' &&
	vendor_contains "$isp" 'devm_clk_get(&pDev->dev, "ISP_IMG_FDVT")'; then
	echo "vendor_isp_clocks=ISP_SCP_SYS_DIS;ISP_MM_SMI_COMMON;ISP_SCP_SYS_ISP;ISP_IMG_LARB6;ISP_IMG_DIP;ISP_IMG_DPE;ISP_IMG_FDVT;ISP_CAM_LARB2;ISP_CAM_CAMSYS;ISP_CAM_CAMTG;ISP_CAM_SENINF;ISP_CAM_CAMSV0..2"
else
	echo "vendor_isp_clocks=not-confirmed"
fi
if vendor_contains "$isp" '#define INT_ST_MASK_CAM' &&
	vendor_contains "$isp" '#define DMA_ST_MASK_CAM' &&
	vendor_contains "$isp" '#define INT_ST_MASK_CAMSV'; then
	echo "vendor_irq_contract=CAM:VS/TG/expdon/pass1/SOF/SW-pass1 plus 11 DMA-done bits;CAMSV:VS/TG/expdon/SOF/pass1;separate error masks"
else
	echo "vendor_irq_contract=not-confirmed"
fi
if vendor_contains "$isp" 'ISP_CAM_CAMSV2 = devm_clk_get' &&
	vendor_contains "$isp" 'ISP_CAMSV5_IDX'; then
	echo "vendor_discrepancy=6-CAMSV-register+IRQ-nodes-but-only-CAMSV0..2-clocks-and-3-CAMSV-M4U-ports-in-configured-path"
else
	echo "vendor_discrepancy=not-confirmed"
fi

echo
echo "[vendor DMA and memory ownership]"
if vendor_contains "$m4u_platform" 'M4U0_PORT_INIT("CAM_IMGO", 0, 2, 0)' &&
	vendor_contains "$m4u_platform" 'M4U0_PORT_INIT("CAM_RAWI", 0, 2, 13)' &&
	vendor_contains "$m4u_platform" 'M4U0_PORT_INIT("CAM_IMGI", 0, 6, 0)' &&
	vendor_contains "$m4u_platform" 'M4U0_PORT_INIT("CAM_DPE_WDMA", 0, 6, 9)'; then
	echo "vendor_m4u_ports=larb2:CAM_IMGO..RAWI:ports0..13;larb6:CAM_IMGI..CAM_DPE_WDMA:ports0..9"
else
	echo "vendor_m4u_ports=not-confirmed"
fi
if vendor_contains "$isp" 'm4u_config_port(&port)' &&
	vendor_contains "$isp" 'ION_HEAP_MULTIMEDIA_MASK' &&
	vendor_contains "$isp" 'ion_import_dma_buf'; then
	echo "vendor_memory_abi=M4U-port-configuration;Ion-multimedia-heap;dma-buf-import;private-buffer-queue"
else
	echo "vendor_memory_abi=not-confirmed"
fi

echo
echo "[Linux 7.1.3 comparison]"
if linux_contains "$linux_dtsi" 'compatible = "mediatek,mt6797-camsys", "syscon"' &&
	linux_contains "$linux_dtsi" 'compatible = "mediatek,mt6797-imgsys", "syscon"' &&
	linux_contains "$linux_dtsi" 'compatible = "mediatek,mt6797-smi-larb"'; then
	echo "linux_camera_reuse=camsys+imgsys+larb2/larb6-DT-and-clock-provider-data-present"
else
	echo "linux_camera_reuse=not-confirmed"
fi
if find "$LINUX_TREE/drivers/media" -type f | rg -i 'seninf|cameraisp|camsv|mtk.*camera' >/dev/null; then
	echo "linux_camera_pipeline=matching-driver-present"
else
	echo "linux_camera_pipeline=matching-SENINF/CAM/CAMSV/ISP-V4L2-driver-missing"
fi
if linux_contains "$linux_clk" 'CLK_CAM_SENINF' &&
	linux_contains "$linux_clk" 'CLK_CAM_CAMSV0' &&
	linux_contains "$linux_larb" 'M4U_PORT_CAM_IMGO'; then
	echo "linux_data_reuse=CAM-clock-gates+MT6797-larb-port-identifiers"
else
	echo "linux_data_reuse=not-confirmed"
fi

echo
echo "[decision]"
echo "reusable=standard-V4L2-media-controller+fwnode-endpoints+MediaTek-clocks+SCPSYS+SMI/IOMMU+dma-buf"
echo "new=MT6797-SENINF/CSI2-receiver;CAM/CAMSV-capture;ISP/media-controller;board-DT-graph"
echo "abi_boundary=do-not-port-camera-isp-char-device-or-Android-Ion/ioctl-UAPI"
echo "safe_next_step=add-disabled-resource-only;recover-CAMSV/SENINF-register-programming-and-DMA-buffer-contract-before-streaming"
echo "hardware_write=none"
