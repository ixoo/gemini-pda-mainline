#!/usr/bin/env python3
"""Compare the vendor Gemini config with the prepared Linux config.

This is a configuration inventory, not a support claim.  Vendor options are
often private ABI or policy switches; the report deliberately labels missing
mainline options for contract review instead of turning them into defaults.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path


CONFIG_LINE = re.compile(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$")
UNSET_LINE = re.compile(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$")

# Keep the report about hardware-facing and driver-enabling choices.  Android
# policy and unrelated vendor features are intentionally excluded.
RELEVANT_PREFIXES = (
    "CONFIG_ARCH_",
    "CONFIG_ARM_",
    "CONFIG_BATTERY",
    "CONFIG_BLUETOOTH",
    "CONFIG_COMMON_CLK",
    "CONFIG_CPU_FREQ",
    "CONFIG_DRM",
    "CONFIG_FB",
    "CONFIG_GNSS",
    "CONFIG_I2C",
    "CONFIG_IIO",
    "CONFIG_IKCONFIG",
    "CONFIG_INPUT",
    "CONFIG_IOMMU",
    "CONFIG_KEYBOARD",
    "CONFIG_MAILBOX",
    "CONFIG_MMC",
    "CONFIG_MFD",
    "CONFIG_MTK",
    "CONFIG_MEDIATEK",
    "CONFIG_NET_",
    "CONFIG_PINCTRL",
    "CONFIG_PM",
    "CONFIG_POWER_SUPPLY",
    "CONFIG_PHY",
    "CONFIG_REGULATOR",
    "CONFIG_RESET",
    "CONFIG_RTC",
    "CONFIG_SCSI",
    "CONFIG_SERIAL",
    "CONFIG_SND",
    "CONFIG_SPI",
    "CONFIG_THERMAL",
    "CONFIG_USB",
    "CONFIG_WATCHDOG",
    "CONFIG_WLAN",
    "CONFIG_WIRELESS",
)

KNOWN_REPLACEMENTS = (
    ("CONFIG_MTK_WATCHDOG", "CONFIG_MEDIATEK_WATCHDOG", "generic MediaTek watchdog"),
    ("CONFIG_MTK_WD_KICKER", "CONFIG_MEDIATEK_WATCHDOG", "vendor keepalive policy is not carried over"),
    ("CONFIG_MTK_M4U", "CONFIG_MTK_IOMMU", "generation-two IOMMU framework"),
    ("CONFIG_MTK_SMI_EXT", "CONFIG_MTK_SMI", "generic SMI framework plus SoC data"),
    ("CONFIG_MTK_USBFSH", "CONFIG_USB_MUSB_HDRC", "MUSB core; MT6797 USB11 glue remains separate"),
    ("CONFIG_MTK_PMIC_WRAP", "CONFIG_MTK_PMIC_WRAP", "generic PMIC-wrapper provider"),
    ("CONFIG_MTK_CMDQ", "CONFIG_MTK_CMDQ", "generic CMDQ provider"),
    ("CONFIG_MTK_RTC", "CONFIG_RTC_DRV_MT6397", "standard MT6351/MT6397 RTC driver"),
)


def parse_config(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = CONFIG_LINE.match(line)
        if match:
            values[match.group(1)] = match.group(2)
            continue
        match = UNSET_LINE.match(line)
        if match:
            values[match.group(1)] = "n"
    return values


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relevant(name: str) -> bool:
    return name.startswith(RELEVANT_PREFIXES)


def enabled(value: str | None) -> bool:
    return value in {"y", "m"}


def display(value: str | None) -> str:
    return value if value is not None else "unset"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vendor", type=Path, required=True)
    parser.add_argument("--mainline", type=Path, required=True)
    parser.add_argument("--fragment", type=Path, required=True)
    args = parser.parse_args()

    for path in (args.vendor, args.mainline, args.fragment):
        if not path.is_file():
            parser.error(f"missing config input: {path}")

    vendor = parse_config(args.vendor)
    mainline = parse_config(args.mainline)
    fragment = parse_config(args.fragment)
    names = sorted(
        name
        for name in set(vendor) | set(mainline) | set(fragment)
        if relevant(name) or name in fragment
    )

    print("audit=gemini-kernel-config-gap")
    print("scope=vendor-enabled-vs-prepared-linux-7.1.3-and-local-fragment")
    print("interpretation=inventory_only;missing_vendor_options_require_contract_review")
    print(f"vendor_config={args.vendor}")
    print(f"mainline_config={args.mainline}")
    print(f"fragment={args.fragment}")
    print(f"vendor_sha256={sha256(args.vendor)}")
    print(f"mainline_sha256={sha256(args.mainline)}")
    print(f"fragment_sha256={sha256(args.fragment)}")
    print()

    counts = {
        "vendor_enabled": 0,
        "missing_from_mainline": 0,
        "built_in_module_delta": 0,
        "matched_enabled": 0,
        "fragment_requests": 0,
        "fragment_policy": 0,
    }
    rows: list[tuple[str, str, str, str, str]] = []
    for name in names:
        vendor_value = vendor.get(name)
        mainline_value = mainline.get(name)
        fragment_value = fragment.get(name)
        if enabled(vendor_value):
            counts["vendor_enabled"] += 1
        if enabled(vendor_value) and not enabled(mainline_value):
            relation = "missing-from-mainline"
            counts["missing_from_mainline"] += 1
        elif enabled(vendor_value) and enabled(mainline_value):
            if vendor_value != mainline_value:
                relation = "built-in-module-delta"
                counts["built_in_module_delta"] += 1
            else:
                relation = "matched-enabled"
                counts["matched_enabled"] += 1
        elif fragment_value is not None and fragment_value != mainline_value:
            if fragment_value == "n":
                # An explicit unset entry is a reproducibility/policy choice,
                # not a request to add a driver.  This matters when Kconfig
                # omits a symbol entirely after selecting a different
                # architecture or dependency set.
                relation = "fragment-policy"
                counts["fragment_policy"] += 1
            else:
                relation = "fragment-request"
                counts["fragment_requests"] += 1
        else:
            continue
        rows.append(
            (
                name,
                display(vendor_value),
                display(mainline_value),
                display(fragment_value),
                relation,
            )
        )

    print("[summary]")
    for key, value in counts.items():
        print(f"{key}={value}")
    print(f"reported_rows={len(rows)}")
    print()
    print("[known_replacements]")
    print("vendor_option\tmainline_option\tvendor\tmainline\trationale")
    for vendor_name, mainline_name, rationale in KNOWN_REPLACEMENTS:
        print(
            "\t".join(
                (
                    vendor_name,
                    mainline_name,
                    display(vendor.get(vendor_name)),
                    display(mainline.get(mainline_name)),
                    rationale,
                )
            )
        )
    print()
    print("[rows]")
    print("option\tvendor\tmainline\tfragment\trelation")
    for row in rows:
        print("\t".join(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
