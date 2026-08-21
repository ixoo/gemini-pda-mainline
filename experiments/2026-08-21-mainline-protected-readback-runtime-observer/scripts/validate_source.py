#!/usr/bin/env python3
"""Validate the generated protected-readback runtime observer source."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def body(text: str, start: str, end: str) -> str:
    first = text.index(start)
    last = text.index(end, first)
    return text[first:last]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    observer = (
        root / "drivers/soc/mediatek/mt6797-protected-readback-observer.c"
    ).read_text()
    binding = (
        root
        / "Documentation/devicetree/bindings/soc/mediatek/"
          "mediatek,mt6797-protected-readback-observer.yaml"
    ).read_text()
    kconfig = (root / "drivers/soc/mediatek/Kconfig").read_text()
    makefile = (root / "drivers/soc/mediatek/Makefile").read_text()
    dts_makefile = (root / "arch/arm64/boot/dts/mediatek/Makefile").read_text()
    dts = (
        root
        / "arch/arm64/boot/dts/mediatek/"
          "mt6797-gemini-pda-protected-readback.dts"
    ).read_text()
    base_dts = (
        root / "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts"
    ).read_text()
    soc_dtsi = (root / "arch/arm64/boot/dts/mediatek/mt6797.dtsi").read_text()

    for token in (
        "mt6797_readback_get_backend",
        "device_is_bound(&backend->dev)",
        "GEMINI_PROTECTED_READBACK_V1",
        "mt6797_dvfsp_clock_backend_read(&clock_backend->dev",
        "mt6797_bigidvfs_backend_read(&bigidvfs_backend->dev",
        "state=complete attempts=1 clock_calls=1 bigidvfs_calls=1",
        "cpu_requests=0 owner_registration=0",
        ".suppress_bind_attrs = true",
    ):
        require(token in observer, f"observer token: {token}")
    probe = body(
        observer,
        "static int mt6797_readback_observer_probe",
        "static const struct of_device_id",
    )
    require(probe.count("mt6797_dvfsp_clock_backend_read(") == 1,
            "one clock call")
    require(probe.count("mt6797_bigidvfs_backend_read(") == 1,
            "one BigiDVFS call")
    require(
        probe.index("mt6797_readback_get_backend(")
        < probe.index("mt6797_dvfsp_clock_backend_read(")
        < probe.index("mt6797_bigidvfs_backend_read(")
        < probe.index("state=complete attempts=1")
        < probe.index("ret = 0"),
        "defer-call-log-bind ordering",
    )
    for field in (
        "abi", "sample_generation", "armplldiv_muxsel", "armplldiv_ckdiv",
        "pll_ll[0]", "pll_ll[1]", "pll_ll[2]", "pll_l[0]", "pll_l[1]",
        "pll_l[2]", "pll_cci[0]", "pll_cci[1]", "pll_cci[2]",
        "cspm_swctrl[0]", "cspm_swctrl[1]", "cspm_swctrl[2]",
        "cspm_hwsta[0]", "cspm_hwsta[1]", "cspm_hwsta[2]",
        "cspm_hwsta[3]", "pll_pcw", "pll_enable_posdiv",
        "sram_selector", "control",
    ):
        require(f"record->{field}" in observer, f"logged raw field: {field}")

    require("config MTK_MT6797_PROTECTED_READBACK_OBSERVER" in kconfig,
            "observer Kconfig symbol")
    for dependency in (
        "depends on MTK_MT6797_DVFSP_CLOCK_BACKEND",
        "depends on MTK_MT6797_DVFSP_BIGIDVFS_BACKEND",
    ):
        require(dependency in kconfig, f"observer dependency: {dependency}")
    require("CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER" in makefile,
            "observer Makefile object")

    for token in (
        "mediatek,mt6797-protected-readback-observer",
        "mediatek,clock-backend",
        "mediatek,bigidvfs-backend",
        "additionalProperties: false",
    ):
        require(token in binding, f"binding token: {token}")

    require('#include "mt6797-gemini-pda.dts"' in dts,
            "candidate derives exact Gemini board")
    require(dts.count('status = "okay";') == 3,
            "exact observer and two backend enables")
    require(dts.count("&dvfsp_clock_backend") == 2,
            "clock backend phandle plus override")
    require(dts.count("&dvfsp_bigidvfs_backend") == 2,
            "BigiDVFS backend phandle plus override")
    require("&dvfsp_resource_owner" not in dts, "resource owner remains closed")
    require("cpu8" not in dts and "cpu9" not in dts, "no A72 DT change")
    require(
        "mt6797-gemini-pda-protected-readback.dtb" in dts_makefile,
        "candidate DTB build entry",
    )
    require("planet,gemini-pda" in base_dts, "exact base board identity")
    for label in ("dvfsp_clock_backend:", "dvfsp_bigidvfs_backend:"):
        require(label in soc_dtsi, f"backend label: {label}")
    require(soc_dtsi.count('status = "disabled";') >= 2,
            "base transports remain default-off")

    added = observer + binding + dts
    for forbidden in (
        "MT6797_BIGIDVFS_FID_WRITE",
        "arm_smccc_smc(",
        "writel(",
        "regmap_write(",
        "cpu_up(",
        "cpu_down(",
        "psci_ops",
        "device_create_file(",
        "sysfs_create",
        "msleep(",
        "schedule_work(",
    ):
        require(forbidden not in added, f"forbidden observer effect: {forbidden}")

    print("source_validation=pass")
    print("observer_calls=clock-1,bigidvfs-1")
    print("defer_before_hardware_access=yes")
    print("automatic_retry_after_access=no")
    print("raw_fields=complete")
    print("candidate_dtb_enables=clock,bigidvfs,observer")
    print("base_gemini_dtb_changed=false")
    print("secure_write=none")
    print("cpu_requests=0")
    print("owner_registration=0")


if __name__ == "__main__":
    main()
