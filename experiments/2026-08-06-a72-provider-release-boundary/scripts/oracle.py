#!/usr/bin/env python3
"""Check the provider release refusal boundary."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0173-arm64-add-provider-release-refusal-boundary.patch"
SERIES = ROOT / "patches/series"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing {label}: {needle}")


def main() -> None:
    patch = PATCH.read_text()
    series = [line for line in SERIES.read_text().splitlines()
              if line and not line.startswith("#")]

    require(patch, "mt6797_a72_provider_release", "release registry entry point")
    require(patch, "ops->release", "paired callback requirement")
    require(patch, "provider-owner release refused", "structured refusal path")
    require(patch, "return -EOPNOTSUPP;", "refusal result")

    names = [Path(line).name for line in series]
    if names.index("0172-arm64-add-provider-owner-callback-refusal-boundary.patch") >= names.index("0173-arm64-add-provider-release-refusal-boundary.patch"):
        raise AssertionError("release patch is not after the acquire boundary")

    for token in ("i2c_transfer", "__i2c_transfer", "regulator_enable(",
                  "regulator_disable(", "psci_ops.cpu_on"):
        if token in patch:
            raise AssertionError(f"unexpected hardware operation in refusal patch: {token}")

    print("claim=PARTIAL_PROVIDER_RELEASE_REFUSAL")
    print("paired_callbacks=required")
    print("release_result=structured-EOPNOTSUPP")
    print("hardware_writes=0")
    print("device_action=none")
    print("status=PASS_STATIC")


if __name__ == "__main__":
    main()
