#!/usr/bin/env python3
"""Source-pin and derive the independent provider-control candidate validator."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


SOURCE_SHA256 = "2b9dba8d12f1254984705f84b1c7e27173436adbcb57c94f781624668091293e"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
SOURCE = (
    REPO_ROOT
    / "experiments/2026-08-15-da921x-readonly-observer/scripts/test_candidate.py"
)


def replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    actual = text.count(old)
    if actual != count:
        raise AssertionError(
            f"unsafe validator derivation: expected {count}, found {actual}: {old}"
        )
    return text.replace(old, new)


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: test-candidate.py --candidate DIR --package DIR --ramdisk FILE"
        )
    source = SOURCE.read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise AssertionError("source validator identity changed")
    text = source.decode("utf-8")
    replacements = (
        ("DA921x read-only observer container", "matched DA921x provider-only control"),
        ("KERNEL_FIELD_SIZE = 5_684_030", "KERNEL_FIELD_SIZE = 5_684_044"),
        ("RAW_SHA256 = \"1a55a25b7d6bff448802db3259ba65371c34657b341f0e621dc134bd700e7b14\"",
         "RAW_SHA256 = \"76d32c74a8ffb714bd10ee7b2e6d1483e4c87e5fa62f0f1ec47d121ea8b95fa9\""),
        ("PADDED_SHA256 = \"7a3ce120de99d7c5ad26dce618f81d50bfeb1ca95b5f2a0bdb9fbf4acba1f564\"",
         "PADDED_SHA256 = \"3188d474f5d6989a0eb0782cdfac781efaf43dd42a0bd11481277050e735f8a2\""),
        ("IMAGE_SHA256 = \"3483fb980c8c59ea0a10bf356737391aaa6b49969e39b4a3cee3831774f5fbf9\"",
         "IMAGE_SHA256 = \"7c32d659dd9eabef33800e2e5aa16e3f609d3cddf0c7efb8e7dc22159ad8cab5\""),
        ("IMAGE_GZIP_SHA256 = \"5609a9a30b2959fd93144900461e4a07ba274adda04454ef534a2961d6a8c1b1\"",
         "IMAGE_GZIP_SHA256 = \"e9ad785fc00d96584ad7c29abc671864c8f03d1c7272610f8b64768b171b27c7\""),
        ("CONFIG_SHA256 = \"0d707f8483ce7a5599625bb2a09889c642b3ee945d2ad3fa6cf6f7289363581a\"",
         "CONFIG_SHA256 = \"56a08dd0f2f4400044f15c2b597e23bbaeb1bd806658670c2d5facf3152d6ac6\""),
        ("SYSTEM_MAP_SHA256 = \"665d70c58f771abc43d39b2b9b7244a28df9ae7ad4eb8856e4fbf678dd7e88dc\"",
         "SYSTEM_MAP_SHA256 = \"4dedb128f7a7e25d627b0f7191486e67b4cbde6f1df2e3692e9b971991e8a298\""),
        ("BUILD_JSON_SHA256 = \"1643441936f8f88d8a7dc221007c4d5fc0616a9c697cda8fcb0b4eb380e61b4e\"",
         "BUILD_JSON_SHA256 = \"a614f5f8368758e6c24c9a497c5feb3c9243f362aa574aaf4cdd0135660c5e7d\""),
        ("gemini-mt6797-da921x-readonly-observer.boot.img",
         "gemini-mt6797-da921x-resource-control.boot.img", 2),
        ("b\"gemini-daobs\"", "b\"gemini-dactl\""),
        ("d0d511e60af343bdcc880b41b50acd2be877fa2b",
         "1ab09cd9ef39a9c99c82e639dcbc15cb6040c74c"),
        ('provenance["build_profile"] == "da921x-readonly-observer"',
         'provenance["build_profile"] == "da921x-resource-only-provider"'),
        ("7.1.3-gemini-da921x-observer", "7.1.3-gemini-da921x-resource"),
        ("require(b\"CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER=y\\n\" in config, \"observer absent\")\n    require(b\"# CONFIG_KUNIT is not set\\n\" in config, \"KUnit leaked into runtime\")\n    require(b\" da9213_legacy_observer_collect\\n\" in system_map, \"observer symbol absent\")\n    require(b\"da9213_legacy_observer_test_suite\" not in system_map, \"test symbol leaked\")\n    require(b\"da921x-observer-v1 event=bound\" in image, \"runtime marker absent\")",
         "require(b\"CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER=y\\n\" in config, \"provider absent\")\n    require(b\"# CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER is not set\\n\" in config, \"observer enabled\")\n    require(b\"# CONFIG_KUNIT is not set\\n\" in config, \"KUnit leaked into runtime\")\n    require(b\" da9213_legacy_probe\\n\" in system_map, \"provider probe symbol absent\")\n    require(b\" da9213_legacy_observer_collect\\n\" not in system_map, \"observer symbol leaked\")\n    require(b\"da921x-observer-v1 event=bound\" not in image, \"observer marker leaked\")"),
        ("validation=da921x-readonly-observer-candidate",
         "validation=da921x-provider-control-candidate"),
        ("runtime_marker=present", "runtime_marker=absent"),
    )
    for replacement in replacements:
        text = replace_exact(text, *replacement)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="da921x-provider-control-", suffix=".py"
    ) as derived:
        derived.write(text)
        derived.flush()
        return subprocess.run([sys.executable, derived.name, *sys.argv[1:]], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
