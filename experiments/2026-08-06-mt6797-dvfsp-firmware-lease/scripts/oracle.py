#!/usr/bin/env python3
"""Check the default-off MT6797 firmware-owner lease contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0175-soc-mediatek-define-I2C6-firmware-lease-contract.patch"
SERIES = ROOT / "patches/series"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing {label}: {needle}")


def main() -> None:
    patch = PATCH.read_text()
    source = patch[patch.index("diff --git"):]
    names = [Path(line).name for line in SERIES.read_text().splitlines()
             if line and not line.startswith("#")]

    require(patch, "MT6797_DVFSP_I2C6_FW_ABI", "protocol-abi")
    require(patch, "MT6797_DVFSP_I2C6_FW_PAUSE_SOURCE\t0x2", "pause-source")
    require(patch, "MT6797_DVFSP_I2C6_FW_SW_PAUSE_BIT\tBIT(13)", "sw-pause")
    require(patch, "MT6797_DVFSP_I2C6_FW_DONE_BIT\t\tBIT(15)", "fw-done")
    require(patch, "MT6797_DVFSP_I2C6_FW_TIMEOUT_US\t2000", "timeout")
    require(patch, "!ops->acquire || !ops->release", "paired-registration")
    require(patch, "mt6797_dvfsp_i2c6_fw_refusal_valid", "structured-refusal")
    require(patch, "mt6797_dvfsp_handoff_i2c6_fw_fault", "sticky-fault")
    require(patch, "lockdep_assert_held(&handoff->transfer_lock)", "transfer-owner")
    require(patch, "lease->generation != handoff->transfer_generation", "generation-check")
    require(patch, "lease->cookie != handoff->transfer_cookie", "cookie-check")
    require(patch, "handoff->fw_lease_active", "lease-lifetime")
    require(patch, "ret = -EBUSY", "unregister-while-held")
    require(patch, "No callback is registered by this patch", "default-off-claim")

    if names.index("0174-soc-mediatek-add-I2C6-DVFSP-transfer-lease.patch") >= names.index("0175-soc-mediatek-define-I2C6-firmware-lease-contract.patch"):
        raise AssertionError("firmware lease contract is not after Linux transfer lease")

    for forbidden in ("readl(", "writel(", "i2c_transfer", "regulator_enable(",
                      "regulator_disable(", "psci_ops.cpu_on", "cpu_up("):
        if forbidden in source:
            raise AssertionError(f"unexpected hardware operation: {forbidden}")

    print("claim=PARTIAL_FIRMWARE_LEASE_CALLBACK_CONTRACT")
    print("registered_owner=0")
    print("pause_source=0x2")
    print("sw_pause_bit=13")
    print("fw_done_bit=15")
    print("timeout_us=2000")
    print("acquire_words=3_pause;3_fw_done")
    print("release_requires_same_owner_handle=1")
    print("hardware_writes=0")
    print("device_action=none")
    print("status=PASS_STATIC")


if __name__ == "__main__":
    main()
