#!/usr/bin/env python3
"""Validate the Git-pinned Buildbox third-reader generation tooling."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPERIMENT = "2026-08-25-mainline-a72-platform-provider-protected-clock-third-read"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def read(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"safe regular file: {path}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path)
    args = parser.parse_args()
    root = (
        args.repository_root.resolve()
        if args.repository_root
        else Path(__file__).resolve().parents[3]
    )
    exp = root / "experiments" / EXPERIMENT
    contract = json.loads(read(exp / "contract.json"))
    generator = read(exp / "scripts/generate-on-buildbox")
    edits = read(exp / "scripts/source_edits.py")
    source_validator = read(exp / "scripts/validate_source.py")
    patch_validator = read(exp / "scripts/validate_patch.py")
    buildbox = read(root / "scripts/buildbox")
    buildbox_doc = read(root / "docs/BUILDBOX.md")
    observer = read(exp / "source/mt6797-a72-platform-provider-clock-observer.c")
    internal = read(
        exp / "source/mt6797-a72-platform-provider-clock-observer-internal.h"
    )
    tests = read(
        exp / "source/mt6797-a72-platform-provider-clock-observer-test.c"
    )
    binding = read(
        exp / "source/mediatek,mt6797-a72-platform-provider-clock-observer.yaml"
    )

    for token in (
        contract["generator_parent_source_state"],
        contract["prepared_source_integrity"],
        contract["canonical_parent_sha256"],
        "readonly PARENT_PATCH=0373-soc-mediatek-test-A72-platform-provider-readiness.patch",
        "generated_patch_count=4",
        "retained_token=GAPC-20260825-A",
        "protected_clock_calls=1",
        "protected_clock_caller_retries=0",
        "explicit_mmio_writes_maximum=401",
        "explicit_mmio_reads_maximum=419",
        "hardware_free_tests=8",
        "device_action=none",
        "boot_candidate=false",
    ):
        require(token in generator, f"generator pin: {token}")
    require("--backend vm" not in generator, "no native VM build")
    require("/workspace/gemini-pda/src/linux-7.1.3-series-a72-platform-provider-clock-parent-source" in generator,
            "managed source root")
    for token in (
        "source_parent_profile=a72-platform-provider-clock-generator-parent",
        'KERNEL_PROFILE="${source_parent_profile}"',
        '"${checkout}/scripts/kernel" prepare',
        "linux-7.1.3-series-a72-platform-provider-clock-parent-source",
    ):
        require(token in buildbox, f"pinned parent preparation: {token}")
    for patch in contract["planned_patches"]:
        require(patch in generator and patch in patch_validator,
                f"generated patch gate: {patch}")

    for token in (
        "PSTORE_GEMINI_A72_PLATFORM_PROVIDER_CLOCK_LEDGER",
        "token=GAPC-20260825-A",
        "crc32=7a63713c",
        "crc32=5773d4f6",
        "choices=(\"ledger\", \"binding\", \"observer\", \"tests\")",
        "MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER",
        "MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_KUNIT_TEST",
    ):
        require(token in edits, f"deterministic source edit: {token}")
    require(
        '"\\tdepends on !PSTORE_GEMINI_A72_PLATFORM_PROVIDER_CLOCK_LEDGER\\n"'
        not in edits,
        "no generated reciprocal Kconfig dependency",
    )
    for token in (
        "exact third-reader call order",
        "two-checkpoint sequence ceiling",
        "no reciprocal Kconfig dependency",
        "terminal success return after clock attempt",
        "resolve/hold/release dependency order",
        "one protected-clock source caller",
        "eight exact KUnit cases",
        "hardware-free tests",
    ):
        require(token in source_validator, f"source invariant: {token}")
    for endpoint in (
        "static struct device *mt6797_a72_ppc_get_provider",
        "static struct device *mt6797_a72_ppc_get_clock",
        "static void mt6797_a72_ppc_log",
    ):
        require(endpoint in source_validator,
                f"explicit dependency-helper endpoint: {endpoint}")
    require("exact four-patch series order" in patch_validator,
            "patch order invariant")
    require("exact changed-file boundary" in patch_validator,
            "patch path invariant")
    require("Signed-off-by:" in patch_validator,
            "synthetic sign-off refusal")

    capture = observer[observer.index("int mt6797_a72_ppc_capture("):
                       observer.index("static struct device *mt6797_a72_ppc_get_platform")]
    ordered = (
        "ops->platform(context, platform, &snapshot->platform)",
        "ops->provider(context, &snapshot->provider)",
        "ops->checkpoint(context, 0)",
        "ops->clock(context, clock, &snapshot->clock)",
        "ops->checkpoint(context, 1)",
    )
    positions = [capture.index(token) for token in ordered]
    require(positions == sorted(positions), "source template exact order")
    require(capture.count("ops->clock(") == 1, "source template one clock call")
    require("for (" not in capture and "while (" not in capture,
            "source template no caller loop")
    for token in (
        "clock_returned",
        "after_checkpoint",
        "MT6797_DVFSP_CLOCK_BACKEND_ABI",
        "A returned hardware call is terminal",
        "explicit_mmio_writes_maximum=401",
        "explicit_mmio_reads_maximum=419",
        "bigidvfs_reads=0 secure_calls=0",
        "cpu_requests=0",
    ):
        require(token in observer, f"observer source boundary: {token}")
    for token in (
        "struct mt6797_a72_platform_provider_clock_snapshot",
        "struct mt6797_a72_platform_provider_clock_ops",
        "int mt6797_a72_ppc_capture",
    ):
        require(token in internal, f"injected interface: {token}")
    require(tests.count("KUNIT_CASE(") == 8, "eight source-template cases")
    for token in (
        "mt6797_a72_ppc_not_ready_test",
        "mt6797_a72_ppc_clock_error_terminal_test",
        "mt6797_a72_ppc_after_failure_terminal_test",
        "KUNIT_EXPECT_MEMEQ",
    ):
        require(token in tests, f"test source boundary: {token}")
    for token in (
        "mediatek,platform-state:",
        "mediatek,provider:",
        "mediatek,clock-backend:",
        "additionalProperties: false",
    ):
        require(token in binding, f"binding source boundary: {token}")
    for label, source in (
        ("observer", observer),
        ("internal", internal),
        ("tests", tests),
    ):
        require(
            not any(line.rstrip().endswith("(") for line in source.splitlines()),
            f"no declaration or call line ending at open parenthesis: {label}",
        )

    for token in (
        "generate-a72-platform-provider-clock-patches",
        "fetch-a72-platform-provider-clock-patches",
        "generate_a72_platform_provider_clock_patches",
        "fetch_a72_platform_provider_clock_patches",
        "mainline-a72-platform-provider-clock-patch-generation",
        "generated_patch_count=4",
        "protected_clock_caller_retries=0",
        "explicit_mmio_writes_maximum=401",
    ):
        require(token in buildbox, f"Buildbox integration: {token}")
    require(
        buildbox.count("mainline-a72-platform-provider-clock-patch-generation")
        == 3,
        "Buildbox purpose count",
    )
    require(
        "  generate-a72-platform-provider-clock-patches) "
        "generate_a72_platform_provider_clock_patches ;;" in buildbox,
        "Buildbox generate dispatcher",
    )
    require(
        "  fetch-a72-platform-provider-clock-patches) "
        "fetch_a72_platform_provider_clock_patches ;;" in buildbox,
        "Buildbox fetch dispatcher",
    )
    for token in (
        "A72 protected-clock third-reader generation",
        "generate-a72-platform-provider-clock-patches",
        "eight-case",
        "terminal no-retry behavior",
        "performs no kernel compile",
    ):
        require(token in buildbox_doc, f"Buildbox documentation: {token}")
    require("/Users/" not in "\n".join((generator, edits, observer, tests)),
            "no personal absolute path")

    print("tooling_validation=pass")
    print("generated_patch_count=4")
    print("hardware_free_tests=8")
    print("native_vm_build=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
