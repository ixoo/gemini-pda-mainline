#!/usr/bin/env python3
"""Check MT6797 fixed-function register evidence against the Linux model."""

from __future__ import annotations

import argparse
from pathlib import Path


COMPATIBLES = ("aal", "ccorr", "color", "dither", "gamma", "od", "ufoe")


def require_text(text: str, needle: str, source: Path) -> None:
    if needle not in text:
        raise SystemExit(f"FAIL: {source}: missing {needle!r}")


def require_absent(text: str, needle: str, source: Path) -> None:
    if needle in text:
        raise SystemExit(f"FAIL: {source}: unexpected {needle!r}")


def read(path: Path) -> str:
    return path.read_text(errors="strict")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", type=Path, required=True)
    parser.add_argument("--linux", type=Path, required=True)
    args = parser.parse_args()

    vendor_reg = args.vendor / "drivers/misc/mediatek/video/mt6797/dispsys/ddp_reg.h"
    v = read(vendor_reg)

    vendor_contract = (
        "#define DISP_AAL_SIZE                           (DISPSYS_AAL_BASE + 0x030)",
        "#define DISP_REG_CCORR_CFG                                   (DISPSYS_CCORR_BASE + 0x020)",
        "#define DISP_REG_CCORR_COEF_0                                (DISPSYS_CCORR_BASE + 0x080)",
        "#define CCORR_0_FLD_CCORR_C00\t\t\t\t\tREG_FLD(12, 16)",
        "#define DISP_REG_GAMMA_LUT\t\t\t\t\t\t\t    (DISPSYS_GAMMA_BASE + 0x700)",
        "#define LUT_FLD_GAMMA_LUT_R\t\t\t\t\tREG_FLD(10, 20)",
        "#define DISP_REG_DITHER_CFG                                       (DISPSYS_DITHER_BASE + 0x020)",
        "#define DISP_REG_DITHER_15                                        (DISPSYS_DITHER_BASE + 0x13c)",
        "#define DISP_REG_OD_CFG          (DISPSYS_OD_BASE+0x020)",
        "#define DISP_REG_OD_DITHER_15\t   (DISPSYS_OD_BASE+0x13C)",
        "#define START_FLD_DISP_UFO_BYPASS\t\t\tREG_FLD(1, 2)",
    )
    for needle in vendor_contract:
        require_text(v, needle, vendor_reg)
    require_absent(v, "DISP_AAL_OUTPUT_SIZE", vendor_reg)

    drm = args.linux / "drivers/gpu/drm/mediatek"
    aal = read(drm / "mtk_disp_aal.c")
    ccorr = read(drm / "mtk_disp_ccorr.c")
    color = read(drm / "mtk_disp_color.c")
    gamma = read(drm / "mtk_disp_gamma.c")
    comp = read(drm / "mtk_ddp_comp.c")
    drv = read(drm / "mtk_drm_drv.c")

    for needle in (
        ".skip_output_size = true",
        ".default_relay = true",
        "if (!(aal->data && aal->data->skip_output_size))",
        '"mediatek,mt6797-disp-aal"',
    ):
        require_text(aal, needle, drm / "mtk_disp_aal.c")

    for needle in (
        ".matrix_bits = 10",
        "cfg = CCORR_RELAY_MODE",
        "writel(CCORR_ENGINE_EN",
        '"mediatek,mt6797-disp-ccorr"',
    ):
        require_text(ccorr, needle, drm / "mtk_disp_ccorr.c")

    require_text(color, ".color_offset = DISP_COLOR_START_MT8173", drm / "mtk_disp_color.c")
    require_text(color, '"mediatek,mt6797-disp-color"', drm / "mtk_disp_color.c")

    for needle in (
        ".lut_bank_size = 512",
        ".lut_bits = 10",
        ".lut_size = 512",
        "GAMMA_RELAY_MODE",
        '"mediatek,mt6797-disp-gamma"',
    ):
        require_text(gamma, needle, drm / "mtk_disp_gamma.c")

    for needle in (
        ".no_od_dither = true",
        "if (!priv->data || !priv->data->no_od_dither)",
        "#define DITHER_ENGINE_EN",
        "#define UFO_BYPASS",
    ):
        require_text(comp, needle, drm / "mtk_ddp_comp.c")

    for component in COMPATIBLES:
        compatible = f'"mediatek,mt6797-disp-{component}"'
        require_text(drv, compatible, drm / "mtk_drm_drv.c")
        binding = (
            args.linux
            / "Documentation/devicetree/bindings/display/mediatek"
            / f"mediatek,{component}.yaml"
        )
        require_text(read(binding), compatible.strip('"'), binding)

    print(
        "PASS vendor-registers=11 aal-output-size=absent "
        "ccorr=2.10 gamma=512x10 defaults=relay od-dither=separate "
        f"compatibles={len(COMPATIBLES)}"
    )


if __name__ == "__main__":
    main()
