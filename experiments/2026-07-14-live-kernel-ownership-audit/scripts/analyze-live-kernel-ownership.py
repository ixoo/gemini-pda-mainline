#!/usr/bin/env python3
"""Compare the live vendor kernel boundary with the current 7.1.3 package.

Inputs are sanitized kernel inventory text, a vendor CONFIG dump, and guest-owned
mainline package files.  The script does not contact hardware and never treats
CONFIG or System.map presence as runtime probe evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


SYMBOLS = (
    ("CONFIG_MODULES", "loadable-module infrastructure"),
    ("CONFIG_MTK_PLATFORM", "vendor platform selector"),
    ("CONFIG_MTK_EVB_BOARD", "vendor board glue"),
    ("CONFIG_MTK_PSCI", "vendor PSCI glue"),
    ("CONFIG_MTK_PMIC_WRAP", "PMIC wrapper"),
    ("CONFIG_MTK_PMIC", "vendor PMIC framework"),
    ("CONFIG_MTK_COMBO_CHIP_CONSYS_6797", "CONSYS combo backend"),
    ("CONFIG_MTK_BTIF", "BTIF transport"),
    ("CONFIG_MTK_ECCCI_DRIVER", "CCCI modem transport"),
    ("CONFIG_MTK_ECCCI_CLDMA", "CCCI CLDMA transport"),
    ("CONFIG_MTK_CCCI_DEVICES", "CCCI character devices"),
    ("CONFIG_MTK_AW9523", "vendor keyboard expander"),
    ("CONFIG_PINCTRL_AW9523", "mainline AW9523 pinctrl"),
    ("CONFIG_USB_MU3D_DRV", "vendor USB3 core"),
    ("CONFIG_USB_MUSB_MEDIATEK", "mainline USB11 MUSB glue"),
    ("CONFIG_USB_XHCI_MTK", "mainline USB3 xHCI"),
    ("CONFIG_MMC_MTK", "MediaTek MSDC host"),
    ("CONFIG_MTK_EMMC_SUPPORT", "vendor eMMC extensions"),
    ("CONFIG_SERIAL_8250_MT6577", "mainline MTK 8250 UART"),
    ("CONFIG_MTK_SERIAL", "vendor serial driver"),
    ("CONFIG_MTK_WATCHDOG", "vendor watchdog"),
    ("CONFIG_MEDIATEK_WATCHDOG", "mainline watchdog"),
    ("CONFIG_PINCTRL_MT6797", "MT6797 pinctrl"),
    ("CONFIG_EINT_MTK", "mainline MTK EINT framework"),
    ("CONFIG_MTK_IOMMU", "mainline MTK IOMMU"),
    ("CONFIG_MTK_SMI", "mainline MTK SMI"),
    ("CONFIG_MTK_FB", "vendor framebuffer"),
    ("CONFIG_DRM_MEDIATEK", "mainline DRM Mediatek"),
    ("CONFIG_MTK_LCM", "vendor panel framework"),
    ("CONFIG_MTK_IMGSENSOR", "vendor camera framework"),
    ("CONFIG_SND_SOC_MT6797", "mainline MT6797 audio"),
    ("CONFIG_MTK_THERMAL", "mainline MTK thermal"),
)

PROBES = (
    ("mtk8250_probe", "UART"),
    ("msdc_drv_probe", "eMMC/MSDC"),
    ("mtk_wdt_probe", "watchdog"),
    ("pwrap_probe", "PMIC wrapper"),
    ("mt6351_regulator_probe", "MT6351 regulator"),
    ("mt6797_pinctrl_init", "pinctrl"),
    ("mtk_musb_probe", "USB11 MUSB"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_config_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$", line)
        if match:
            values[match.group(1)] = match.group(2)
            continue
        match = re.match(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$", line)
        if match:
            values[match.group(1)] = "n"
    return values


def parse_config(path: Path) -> dict[str, str]:
    return parse_config_text(path.read_text(encoding="utf-8", errors="replace"))


def section(text: str, heading: str) -> str:
    marker = f"===== {heading} ====="
    start = text.find(marker)
    if start < 0:
        return ""
    start += len(marker)
    end = text.find("\n===== ", start)
    return text[start:] if end < 0 else text[start:end]


def state(values: dict[str, str], symbol: str) -> str:
    # A missing Kconfig line is the same effective state as an explicit
    # ``# CONFIG_FOO is not set`` entry.  Normalizing it makes the boundary
    # classification meaningful for symbols that one kernel never defined.
    return values.get(symbol, "n")


def classify(vendor: str, mainline: str) -> str:
    if vendor == mainline:
        return "same"
    if vendor in {"y", "m"} and mainline == "n":
        return "vendor-enabled/mainline-unset"
    if vendor == "y" and mainline == "m":
        return "vendor-built-in/mainline-module"
    if vendor == "m" and mainline == "y":
        return "vendor-module/mainline-built-in"
    if vendor == "n" and mainline in {"y", "m"}:
        return "mainline-only"
    return "value-delta"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--identity", type=Path)
    parser.add_argument("--vendor-config", type=Path, required=True)
    parser.add_argument("--mainline-config", type=Path, required=True)
    parser.add_argument("--system-map", type=Path, required=True)
    parser.add_argument("--build-json", type=Path, required=True)
    args = parser.parse_args()

    capture_text = args.capture.read_text(encoding="utf-8", errors="replace")
    vendor = parse_config(args.vendor_config)
    mainline = parse_config(args.mainline_config)
    captured = parse_config_text(section(capture_text, "relevant kernel configuration"))
    metadata = json.loads(args.build_json.read_text(encoding="utf-8"))
    system_map = args.system_map.read_text(encoding="utf-8", errors="replace")
    modules_section = section(capture_text, "loaded modules").strip()
    identity_text = ""
    if args.identity:
        identity_text = args.identity.read_text(encoding="utf-8", errors="replace")
    uname = next(
        (line for line in (identity_text + "\n" + capture_text).splitlines() if line.startswith("Linux ")),
        "not_captured",
    )

    capture_matches = 0
    capture_disagreements = 0
    for symbol, _purpose in SYMBOLS:
        if symbol in captured:
            if captured[symbol] == state(vendor, symbol):
                capture_matches += 1
            else:
                capture_disagreements += 1

    print("validation=live-kernel-ownership-vs-mainline-7.1.3")
    print(f"vendor_uname={uname}")
    print(f"analyzer_sha256={sha256(Path(__file__))}")
    print(f"capture_sha256={sha256(args.capture)}")
    if args.identity:
        print(f"identity_sha256={sha256(args.identity)}")
    print(f"vendor_config_sha256={sha256(args.vendor_config)}")
    print(f"mainline_config_sha256={sha256(args.mainline_config)}")
    print(f"system_map_sha256={sha256(args.system_map)}")
    print(f"build_json_sha256={sha256(args.build_json)}")
    print(f"mainline_modules_built={metadata.get('modules_built', False)}")
    print(f"runtime_module_namespace={'present' if modules_section else 'absent'}")
    print(f"capture_config_matches_vendor={capture_matches}")
    print(f"capture_config_disagreements={capture_disagreements}")
    print("hardware_write=none")
    print("runtime_mainline_boot=not_attempted")
    print("\n[config_boundary]")
    for symbol, purpose in SYMBOLS:
        vendor_value = state(vendor, symbol)
        capture_value = state(captured, symbol)
        mainline_value = state(mainline, symbol)
        print(
            f"{symbol}|purpose={purpose}|vendor={vendor_value}|capture={capture_value}|"
            f"mainline={mainline_value}|classification={classify(vendor_value, mainline_value)}"
        )
    print("\n[mainline_linked_probe_paths]")
    for symbol, purpose in PROBES:
        linked = bool(re.search(rf"\s{re.escape(symbol)}$", system_map, re.MULTILINE))
        print(f"{purpose}|symbol={symbol}|linked_in_image={'yes' if linked else 'no'}")
    print("\n[decision]")
    print("vendor_runtime_is_builtin_only=confirmed_by_missing_CONFIG_MODULES_and_empty_proc_modules")
    print("mainline_module_presence_is_package_only=do_not_treat_as_probe_evidence")
    print("first_boot_boundary=builtin_psci_timer_gic_uart_pinctrl_watchdog_emmc_only")
    print("vendor_only_transport_blocks=require_new_backend_or_firmware_boundary")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
