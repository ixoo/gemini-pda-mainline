#!/usr/bin/env python3
"""Check the bounded provider-owner callback/refusal source contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0172-arm64-add-provider-owner-callback-refusal-boundary.patch"
DRIVER = ROOT / "patches/v7.1.3/0172-arm64-add-provider-owner-callback-refusal-boundary.patch"
SERIES = ROOT / "patches/series"
FRAGMENT = ROOT / "configs/gemini-da921x-provider-owner-refusal.fragment"


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing {label}: {needle}")


def main() -> None:
    patch = PATCH.read_text()
    series = SERIES.read_text().splitlines()
    fragment = FRAGMENT.read_text()

    require(patch, "include/linux/mt6797-a72-provider.h", "provider API")
    require(patch, "mt6797_a72_provider_register", "provider registration")
    require(patch, "mt6797_a72_membership_run_provider_acquire", "owner call")
    require(patch, "return -EOPNOTSUPP;", "structured read-only refusal")
    require(patch, "mt6797_a72_provider_unregister", "managed lifetime")
    require(fragment, "CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER=y", "opt-in config")

    selected = [line for line in series if line and not line.startswith("#")]
    positions = {Path(line).name[:4]: index for index, line in enumerate(selected)}
    if not positions["0170"] < positions["0171"] < positions["0172"]:
        raise AssertionError("provider-owner series order is not 0170 < 0171 < 0172")

    forbidden = ("regulator_enable(", "regulator_disable(", "regulator_set_voltage", "psci_ops.cpu_on")
    for token in forbidden:
        if token in patch:
            raise AssertionError(f"forbidden hardware operation appears in patch: {token}")

    print("claim=PARTIAL_R01_R02_PROVIDER_CALLBACK_REFUSAL")
    print("provider_registration=explicit-opt-in")
    print("callback_result=structured-EOPNOTSUPP-before-vote")
    print("regulator_writes=0")
    print("cpu_on_calls=0")
    print("device_action=none")
    print("status=PASS_STATIC")


if __name__ == "__main__":
    main()
