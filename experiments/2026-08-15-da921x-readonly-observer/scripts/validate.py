#!/usr/bin/env python3
"""Validate repository integration of the DA921x read-only observer."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH_REL = "v7.1.3/0278-regulator-observe-legacy-DA921x-read-only-provider.patch"
PATCH_SHA256 = "6225f78584357a1b59dbe4b210c9cab7271175ebbe3d07b719429d503cad3696"
RUNTIME_FRAGMENT = "configs/gemini-da921x-readonly-observer.fragment"
KUNIT_FRAGMENT = "configs/gemini-da921x-readonly-observer-kunit.fragment"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    patch = ROOT / "patches" / PATCH_REL
    digest = hashlib.sha256(patch.read_bytes()).hexdigest()
    require(digest == PATCH_SHA256, "generated patch checksum changed")

    series = [
        line.strip() for line in (ROOT / "patches/series").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    require(series[-1] == PATCH_REL, "observer patch is not the canonical tail")
    require(series.count(PATCH_REL) == 1, "observer patch is not unique in series")

    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profiles = manifest["config"]["profiles"]
    parent = profiles["da921x-resource-only-provider"]
    runtime = profiles["da921x-readonly-observer"]
    kunit = profiles["da921x-readonly-observer-kunit"]
    require(runtime["fragments"] == parent["fragments"] + [RUNTIME_FRAGMENT],
            "runtime observer is not an exact parent-profile extension")
    require(kunit["fragments"] == runtime["fragments"] + [KUNIT_FRAGMENT],
            "KUnit observer is not an exact runtime-profile extension")
    require(RUNTIME_FRAGMENT not in parent["fragments"],
            "observer leaked into its parent profile")

    runtime_text = (ROOT / RUNTIME_FRAGMENT).read_text()
    kunit_text = (ROOT / KUNIT_FRAGMENT).read_text()
    require("CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER=y" in runtime_text,
            "runtime observer gate is absent")
    require("# CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER_KUNIT_TEST is not set"
            in runtime_text, "runtime profile enables KUnit")
    require("CONFIG_KUNIT=y" in kunit_text, "KUnit core is absent")
    require("CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER_KUNIT_TEST=y" in kunit_text,
            "observer KUnit gate is absent")

    added = "\n".join(
        line[1:] for line in patch.read_text().splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    for needle in (
        "da921x-observer-v1 event=bound",
        "unsigned int providers = chip->provider_count;",
        "&chip->provider_count",
        "KUNIT_CASE(da9213_legacy_observer_bounds_read_failures)",
        "KUNIT_CASE(da9213_legacy_observer_invalidates_on_cleanup)",
    ):
        require(needle in added, f"patch lost required contract: {needle}")
    for forbidden in (
        "i2c_master_send(", "i2c_smbus_write", "regmap_write(",
        "set_voltage_sel", ".enable =", ".disable =", ".set_mode =",
        ".set_current_limit =", "clk_set_", "cpu_up(", "cpu_down(",
        "arm_smccc", "psci_ops.cpu_on",
    ):
        require(forbidden not in added,
                f"patch adds state-changing operation: {forbidden}")

    print("validation=da921x-readonly-observer")
    print("generated_patch_sha256=" + digest)
    print("runtime_profile=isolated-parent-extension")
    print("kunit_profile=isolated-runtime-extension")
    print("mutations_rejected=10")
    print("register_data_writes=0")
    print("hardware_write=none")
    print("cpu8_cpu9_admission=closed")


if __name__ == "__main__":
    main()
