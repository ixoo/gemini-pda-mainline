#!/usr/bin/env python3
"""Check the recovered MT6797 DSI host and MIPI-TX PHY contract."""

from __future__ import annotations

import argparse
from pathlib import Path


def read(path: Path) -> str:
    return path.read_text(errors="strict")


def require(text: str, needle: str, source: Path) -> None:
    if needle not in text:
        raise SystemExit(f"FAIL: {source}: missing {needle!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", type=Path, required=True)
    parser.add_argument("--linux", type=Path, required=True)
    args = parser.parse_args()

    vendor_dir = (
        args.vendor / "drivers/misc/mediatek/video/mt6797/dispsys"
    )
    vendor_reg = vendor_dir / "ddp_reg.h"
    vendor_dsi = vendor_dir / "ddp_dsi.c"
    vendor_path = vendor_dir / "ddp_path.c"
    vreg = read(vendor_reg)
    vdsi = read(vendor_dsi)
    vpath = read(vendor_path)

    for needle in (
        "MIPITX_DSI_TOP_CON;\t/* 0040 */",
        "MIPITX_DSI_BG_CON;\t/* 0044 */",
        "MIPITX_DSI_PLL_CON0;\t/* 0050 */",
        "MIPITX_DSI_PLL_CON2;\t/* 0058 */",
        "MIPITX_DSI_PLL_CHG;\t/* 0060 */",
        "MIPITX_DSI_PLL_PWR;\t/* 0068 */",
        "unsigned RG_DSI0_MPPLL_PREDIV:2;",
        "unsigned RG_DSI0_MPPLL_POSDIV:3;",
        "unsigned RG_DSI_MPPLL_S2QDIV:2;",
        "unsigned RG_DSI0_MPPLL_SDM_PCW_CHG:1;",
    ):
        require(vreg, needle, vendor_reg)

    for needle in (
        "pcw_ratio = 1;",
        "pcw_ratio = 16;",
        "S2Qdiv    = 2;",
        "pcw = data_Rate * pcw_ratio / 13;",
        "RG_DSI0_MPPLL_SDM_PCW_CHG, 0",
        "RG_DSI0_MPPLL_SDM_PCW_CHG, 1",
    ):
        require(vdsi, needle, vendor_dsi)

    primary_path = (
        "DISP_MODULE_OVL0, DISP_MODULE_OVL0_2L, DISP_MODULE_OVL1_2L, "
        "DISP_MODULE_OVL0_VIRTUAL,\n\t DISP_MODULE_COLOR0, DISP_MODULE_CCORR, "
        "DISP_MODULE_AAL, DISP_MODULE_GAMMA,\n\t DISP_MODULE_OD, "
        "DISP_MODULE_DITHER, DISP_MODULE_RDMA0, DISP_PATH0,\n\t "
        "DISP_MODULE_UFOE, DISP_MODULE_PWM0, DISP_MODULE_DSI0"
    )
    require(vpath, primary_path, vendor_path)

    drm = args.linux / "drivers/gpu/drm/mediatek"
    master = drm / "mtk_drm_drv.c"
    master_text = read(master)
    master_path = (
        "static const unsigned int mt6797_mtk_ddp_main[] = {\n"
        "\tDDP_COMPONENT_OVL0,\n"
        "\tDDP_COMPONENT_OVL_2L0,\n"
        "\tDDP_COMPONENT_OVL_2L1,\n"
        "\tDDP_COMPONENT_COLOR0,\n"
        "\tDDP_COMPONENT_CCORR,\n"
        "\tDDP_COMPONENT_AAL0,\n"
        "\tDDP_COMPONENT_GAMMA,\n"
        "\tDDP_COMPONENT_OD0,\n"
        "\tDDP_COMPONENT_DITHER0,\n"
        "\tDDP_COMPONENT_RDMA0,\n"
        "\tDDP_COMPONENT_UFOE,\n"
        "\tDDP_COMPONENT_DSI0,\n"
        "};"
    )
    require(master_text, master_path, master)
    require(master_text, 'compatible = "mediatek,mt6797-mmsys"', master)
    require(master_text, ".data = &mt6797_mmsys_driver_data", master)

    host = drm / "mtk_dsi.c"
    host_text = read(host)
    for needle in (
        "static const struct mtk_dsi_driver_data mt6797_dsi_driver_data",
        ".reg_cmdq_off = 0x200",
        ".reg_vm_cmd_off = 0x130",
        '"mediatek,mt6797-dsi", .data = &mt6797_dsi_driver_data',
    ):
        require(host_text, needle, host)

    phy_dir = args.linux / "drivers/phy/mediatek"
    phy = phy_dir / "phy-mtk-mipi-dsi-mt6797.c"
    phy_text = read(phy)
    for needle in (
        "#define RG_DSI_MPPLL_PREDIV\t\tGENMASK(3, 2)",
        "#define RG_DSI_MPPLL_POSDIV\t\tGENMASK(6, 4)",
        "#define RG_DSI_MPPLL_S2QDIV\t\tGENMASK(13, 12)",
        "FIELD_PREP(RG_DSI_MPPLL_S2QDIV, 2)",
        "13000000",
        "RG_DSI_MPPLL_SDM_PCW_CHG",
        "RG_DSI_PAD_TIE_LOW_EN",
        "The MT6797 sequence leaves the reset voltage selectors intact.",
        "const struct mtk_mipitx_data mt6797_mipitx_data",
    ):
        require(phy_text, needle, phy)

    binding_files = (
        args.linux
        / "Documentation/devicetree/bindings/display/mediatek/mediatek,dsi.yaml",
        args.linux
        / "Documentation/devicetree/bindings/phy/mediatek,dsi-phy.yaml",
    )
    for path, compatible in zip(
        binding_files,
        ("mediatek,mt6797-dsi", "mediatek,mt6797-mipi-tx"),
        strict=True,
    ):
        require(read(path), compatible, path)

    dtsi = args.linux / "arch/arm64/boot/dts/mediatek/mt6797.dtsi"
    dtsi_text = read(dtsi)
    for needle in (
        "ovl-2l0 = &ovl0_2l;",
        "ovl-2l1 = &ovl1_2l;",
        "ovl0: ovl@1400b000",
        "interrupts = <GIC_SPI 213 IRQ_TYPE_LEVEL_LOW>;",
        "iommus = <&m4u M4U_PORT_DISP_OVL0>;",
        "ovl0_2l: ovl@1400d000",
        "iommus = <&m4u M4U_PORT_DISP_2L_OVL0_LARB0>;",
        "ovl1_2l: ovl@1400e000",
        "iommus = <&m4u M4U_PORT_DISP_2L_OVL1>;",
        "rdma0: rdma@1400f000",
        "iommus = <&m4u M4U_PORT_DISP_RDMA0>;",
        "color0: color@14013000",
        "ccorr0: ccorr@14014000",
        "aal0: aal@14015000",
        "gamma0: gamma@14016000",
        "od0: od@14017000",
        "dither0: dither@14018000",
        "ufoe: ufoe@14019000",
        "mipi_tx0: dsi-phy@10215000",
        'compatible = "mediatek,mt6797-mipi-tx";',
        "dsi0: dsi@1401c000",
        'compatible = "mediatek,mt6797-dsi";',
        "interrupts = <GIC_SPI 229 IRQ_TYPE_LEVEL_LOW>;",
        "<&mmsys CLK_MM_DSI0_MM_CLOCK>",
        "<&mmsys CLK_MM_DSI0_INTERFACE_CLOCK>",
        "phys = <&mipi_tx0>;",
        "dsi0_in: port@0",
        "dsi0_out: port@1",
    ):
        require(dtsi_text, needle, dtsi)

    print(
        "PASS host=0x200/0x130 phy-fields=mt6797-native "
        "rate=50M..1.25G calibration=preserved pcw-latch=pulsed "
        "compatibles=2 pipeline=12-components nodes=12-disabled"
    )


if __name__ == "__main__":
    main()
