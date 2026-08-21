#!/usr/bin/env python3
"""Validate the exact protected-readback firmware audit inputs and decision."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    contract = json.loads((HERE / "contract.json").read_text())
    require(contract["repository_parent"] ==
            "741e1052f143b624b9a1200ead426887a921aa7a",
            "repository parent")

    texts = {}
    for name, record in contract["inputs"].items():
        path = ROOT / record["path"]
        require(path.is_file() and not path.is_symlink(),
                f"regular input: {name}")
        require(sha256(path) == record["sha256"], f"input identity: {name}")
        texts[name] = path.read_text()

    clock = texts["clock_patch"]
    for token in (
        "#define MT6797_DVFSP_SEMAPHORE\t\t\t0x440",
        "#define MT6797_DVFSP_SEMAPHORE_POLL_US\t\t10",
        "#define MT6797_DVFSP_SEMAPHORE_RETRIES\t\t200",
        "local_irq_save(flags);",
        "spin_lock(&backend->semaphore_lock);",
        "backend->cspm + MT6797_DVFSP_CSPM_POWERON_EN",
        "readback->armplldiv_muxsel = readl(backend->mcumixed +",
    ):
        require(token in clock, f"clock transport token: {token}")
    require("ndelay(" not in clock, "clock transport still omits 200 ns settle")

    big = texts["bigidvfs_patch"]
    for token in (
        "#define MT6797_BIGIDVFS_FID_READ\t\t\t0xc200035fUL",
        "#define MT6797_BIGIDVFS_PLL_PCW\t\t\t0x102224a4U",
        "#define MT6797_BIGIDVFS_PLL_ENABLE_POSDIV\t0x102224a0U",
        "#define MT6797_BIGIDVFS_SRAM_SELECTOR\t\t0x102222b0U",
        "#define MT6797_BIGIDVFS_CONTROL\t\t\t0x10222470U",
        "arm_smccc_smc(MT6797_BIGIDVFS_FID_READ",
        "if (result.a0 >> 32)",
    ):
        require(token in big, f"BigiDVFS transport token: {token}")
    require("0xc200035e" not in big, "secure write FID absent")
    require(big.count("mt6797_bigidvfs_secure_read(") == 5,
            "four calls plus function definition")
    require("memset(readback" not in big, "caller buffer not precleared")

    firmware = texts["named_firmware_contract"]
    for token in (
        "`2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3`",
        "`0xc200035f` (`REG_READ`)",
        "Zero-extended register value, or `-3` outside the whitelist.",
        "(address & 0xffffc000) == 0x10220000",
        "Header-declared services `0xc20003b2` through `0xc20003b7`",
    ):
        require(token in firmware, f"named firmware token: {token}")

    live = texts["live_tee_identity"]
    for token in (
        "tee1_sha256=2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3",
        "tee2_sha256=2cd154f332ee72edb6dee431a68eb5f8b98b4dc05ee14e56591cfbffcf81a9b3",
        "both_live_tee_slots_match_analyzed_payload=yes",
        "partition_writes=none",
    ):
        require(token in live, f"live TEE identity token: {token}")

    protocol = texts["public_protocol"]
    for token in (
        "semaphore_register=cspm_base_plus_0x440;hardware_semaphore=3_M0",
        "acquire=write_1;read_bit0;retry_every_10us;200_iterations;timeout=2000us",
        "read_write_ordering=200ns_delay_before_first_read_or_after_sequential_write",
        "bigi_fid_read=0xc200035f;args=secure_register_address",
    ):
        require(token in protocol, f"public protocol token: {token}")

    tee = texts["tee_owner"]
    require("secure_semaphore_target=0x11015448" in tee,
            "secure competing master port")
    require("keyed_cspm_plus_0_value=0x0b160001" in tee,
            "secure keyed CSPM access")

    decision = contract["decision"]
    require(decision == {
        "combined_runtime_enablement": "rejected",
        "bigidvfs_named_firmware_abi": "confirmed",
        "bigidvfs_stable_all_or_zero_snapshot": "unproven",
        "clock_resource_and_semaphore_identity": "confirmed",
        "clock_successful_acquire_ordering":
            "rejected-missing-200ns-settle",
        "next_device_boot":
            "blocked-pending-remediation-and-hardware-free-tests",
        "cpu8_cpu9_admission": "closed",
    }, "audit decision")
    require(contract["scope"] == {
        "hardware_write": False,
        "device_action": False,
        "secure_call": False,
        "semaphore_access": False,
        "boot_candidate": False,
        "cpu_on": False,
        "cpu_off": False,
    }, "offline scope")

    result = (HERE / "results/audit-20260821.txt").read_text()
    for token in (
        "bigidvfs_named_firmware_abi=confirmed",
        "clock_successful_acquire_ordering=rejected-missing-200ns-settle",
        "combined_runtime_enablement=rejected",
        "device_action=none",
        "cpu8_cpu9_admission=closed",
    ):
        require(token in result, f"result token: {token}")

    print("validation=protected-readback-firmware-audit")
    print("bigidvfs_named_firmware_abi=confirmed")
    print("clock_successful_acquire_ordering=rejected-missing-200ns-settle")
    print("combined_runtime_enablement=rejected")
    print("device_action=none")


if __name__ == "__main__":
    main()
