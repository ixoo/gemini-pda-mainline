#!/usr/bin/env python3
"""Validate the runtime-binding and production-observer successor source."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def count(text: str, token: str, expected: int, label: str) -> None:
    actual = text.count(token)
    require(actual == expected, f"{label}: expected {expected}, found {actual}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    psci = (root / "arch/arm64/kernel/mt6797_psci.c").read_text()
    soc = root / "drivers/soc/mediatek"
    admission = (soc / "mt6797-a72-admission-controller.c").read_text()
    observer = (soc / "mt6797-a72-frequency-observer.c").read_text()
    header = (soc / "mt6797-a72-frequency-observer-internal.h").read_text()

    production = (
        "0x18ded825be6993a5, 0xa403f8cd526e3682,\n"
        "\t0x199cc55afce876f3, 0x6b7f194faced0b25,"
    )
    physical = (
        "0x2e50cc09d2241006, 0xd819eeb0ed4151fb,\n"
        "\t0xc6ed927e9e51b41e, 0x27c2dd7ce3cedd39,"
    )
    count(psci, production, 1, "production identity")
    count(psci, physical, 1, "physical identity")
    require(
        psci.index("CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER")
        < psci.index(production)
        < psci.index(physical),
        "production identity is not the observer-specific physical branch",
    )

    for token in (
        "struct mt6797_a72_hotplug_snapshot_source frequency_source;",
        "bool frequency_source_ready;",
        "mt6797_a72_hotplug_snapshot_source_init(\n"
        "\t\t&controller->frequency_source, platform, clock, bigidvfs);",
        "dev, &mt6797_a72_admission_frequency_group",
        "dev, &controller->frequency_source, buf",
        '"frequency observer unavailable\\n"',
    ):
        count(admission, token, 1, f"admission wiring {token[:30]}")
    count(
        admission,
        "if (controller->frequency_source_ready)\n\t\treturn 0;",
        1,
        "single initialization guard",
    )
    count(
        admission,
        "ret = mt6797_a72_admission_prepare(controller);",
        2,
        "probe and trigger preparation",
    )
    count(
        admission,
        "static DEVICE_ATTR_RO(a72_frequency_observation);",
        1,
        "admission observer attribute",
    )

    signature = (
        "ssize_t mt6797_a72_frequency_observer_render(\n"
        "\tstruct device *dev,\n"
        "\tstruct mt6797_a72_hotplug_snapshot_source *source, char *buf)"
    )
    count(header, signature + ";", 1, "render declaration")
    count(observer, signature, 1, "render implementation")
    count(
        observer,
        "dev, dev_get_drvdata(dev), buf",
        1,
        "disconnected adapter compatibility wrapper",
    )
    count(
        observer,
        "static DEVICE_ATTR_RO(a72_frequency_observation);",
        1,
        "snapshot observer attribute",
    )
    for token in (
        "MT6797_A72_FREQUENCY_OBSERVER_MAX_ATTEMPTS 3U",
        "controller->attempts++",
        "mutex_lock(&controller->lock)",
        "mutex_unlock(&controller->lock)",
    ):
        count(header + observer, token, 1, f"bounded observer {token}")

    print("production_config_identity=18ded825be6993a5a403f8cd526e3682199cc55afce876f36b7f194faced0b25")
    print("prior_physical_identity=preserved")
    print("production_observer_owner=a72-admission-controller")
    print("production_snapshot_source=resolved-before-attribute")
    print("observer_attempt_budget=3-unchanged")
    print("disconnected_adapter_wrapper=preserved")
    print("result=pass")


if __name__ == "__main__":
    main()
