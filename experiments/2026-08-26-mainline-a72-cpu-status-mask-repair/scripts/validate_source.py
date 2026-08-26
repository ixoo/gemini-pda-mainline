#!/usr/bin/env python3
"""Validate exact CPU-status-mask repair source invariants."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def read(path: Path) -> str:
    require(path.is_file(), f"missing source: {path}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    soc = root / "drivers/soc/mediatek"
    platform = read(soc / "mt6797-a72-platform-state.c")
    public = read(root / "include/linux/soc/mediatek/mt6797-a72-platform-state.h")

    require(platform.count("#define MT6797_A72_CPU_PWR_STATUS_MASK") == 1,
            "one CPU-status mask definition")
    require("MT6797_A72_CPU_PWR_STATUS_MASK\t\tGENMASK(7, 6)" in platform,
            "exact CPU8/CPU9 identity mask")
    require(platform.count("MT6797_A72_CPU_PWR_STATUS_MASK)") == 2,
            "mask applied independently to both CPU-status words")
    require("first->spm_cpu_pwr_status != second->spm_cpu_pwr_status" not in platform,
            "no full first CPU-status comparison")
    require("first->spm_cpu_pwr_status_2nd != second->spm_cpu_pwr_status_2nd" not in platform,
            "no full second CPU-status comparison")
    require(platform.count("ops->read_once(context, &first)") == 1,
            "exact first sample")
    require(platform.count("ops->read_once(context, &second)") == 1,
            "exact second sample")
    require("return -EBUSY;" in platform and "return -EAGAIN;" in platform,
            "distinct busy and movement returns")
    require(platform.index("return -EBUSY;") < platform.index("return -EAGAIN;"),
            "CCI busy precedence")
    require("*snapshot = second;" in platform and "snapshot->valid = true;" in platform,
            "full second raw sample publication")
    for field in ("spm_cpu_pwr_status", "spm_cpu_pwr_status_2nd"):
        require(f"u32 {field};" in public, f"full raw public field: {field}")
    for forbidden in ("while (", "udelay(", "msleep(", "writel(", "cpu_up(",
                      "cpu_down(", "psci_ops", "i2c_transfer("):
        require(forbidden not in platform, f"forbidden production action: {forbidden}")

    if args.phase == "tests":
        test = read(soc / "mt6797-a72-platform-state-test.c")
        require(test.count("KUNIT_CASE(") == 6, "six platform KUnit cases")
        require("mt6797_state_each_a72_identity_bit_test" in test,
                "each A72 identity bit test")
        require("status_bits[] = { BIT(6), BIT(7) }" in test,
                "bits 6 and 7 covered")
        require("word < 2" in test, "both CPU-status words covered")
        for value in ("0x003dcf08", "0x003dc708", "0x003defff", "0x003dc7ff"):
            require(value in test, f"exact live movement fixture: {value}")
        require(test.count("snapshot.spm_cpu_pwr_status") >= 2,
                "full raw publication assertions")
        require("state.samples[1].spm_cpu_pwr_status = BIT(6);" in test,
                "CCI simultaneous A72 movement")
        require("ret, -EBUSY" in test, "CCI busy expected")
        require("ret, -EAGAIN" in test, "A72 movement expected")
        require("ret, 0" in test, "unrelated movement accepted")
    print(f"source_validation={args.phase}:pass")
    print("cpu_status_mask=GENMASK(7,6)")
    print("complete_samples=2")
    print("third_read=none")
    print("device_action=none")


if __name__ == "__main__":
    main()
