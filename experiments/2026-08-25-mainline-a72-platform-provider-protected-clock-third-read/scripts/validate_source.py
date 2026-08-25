#!/usr/bin/env python3
"""Validate generated MT6797 platform/provider/clock observer source."""

from __future__ import annotations

import argparse
import zlib
from pathlib import Path


PHASES = ("ledger", "binding", "observer", "tests")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def read(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"safe regular file: {path}")
    return path.read_text(encoding="utf-8")


def section(text: str, start: str, end: str) -> str:
    first = text.index(start)
    last = text.index(end, first)
    return text[first:last]


def validate_ledger(root: Path) -> None:
    kconfig = read(root / "fs/pstore/Kconfig")
    ledger = read(root / "fs/pstore/gemini_protected_readback_ledger.c")
    mode = section(
        kconfig,
        "config PSTORE_GEMINI_A72_PLATFORM_PROVIDER_CLOCK_LEDGER",
        "config PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER",
    )
    for token in (
        "depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "depends on MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER=y",
        "depends on !PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER",
        "immediately before its sole",
        "one record only after that call returns",
        "signature-last",
        "bounded clock",
        "no BigiDVFS",
    ):
        require(token in mode, f"ledger Kconfig token: {token}")
    old_mode = section(
        kconfig,
        "config PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER",
        "config PSTORE_GEMINI_A72_PLATFORM_SNAPSHOT_LEDGER",
    )
    require(
        "depends on !PSTORE_GEMINI_A72_PLATFORM_PROVIDER_CLOCK_LEDGER"
        in old_mode,
        "mutual exclusion with predecessor ledger",
    )
    require(
        "MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER=y ||" in kconfig,
        "base ledger accepts three-reader observer",
    )

    layout = section(
        ledger, "#define GEMINI_PRB_RESERVE_BASE", "#define GEMINI_PRB_HEADER_SIZE"
    )
    require(
        "defined(CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_CLOCK_LEDGER)"
        in layout,
        "new mode selects first-dmesg layout",
    )
    require("GEMINI_PRB_SLOT_COUNT\t\t2" in layout, "two retained slots")
    require("GEMINI_PRB_FIRST_OWNED_SLOT\t0" in layout, "first slot index")
    records = section(
        ledger,
        "#ifdef CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_CLOCK_LEDGER",
        "#elif defined(CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_LEDGER)",
    )
    expected = (
        ("before-clock", 1, "7a63713c"),
        ("after-clock", 2, "5773d4f6"),
    )
    require(
        records.count("GEMINI_A72_PLATFORM_PROVIDER_CLOCK_SNAPSHOT_V1") == 2,
        "two three-reader retained records",
    )
    require(records.count("token=GAPC-20260825-A") == 2, "two exact tokens")
    for checkpoint, slot, checksum in expected:
        line = (
            "GEMINI_A72_PLATFORM_PROVIDER_CLOCK_SNAPSHOT_V1 "
            f"token=GAPC-20260825-A checkpoint={checkpoint} slot={slot}"
        )
        require(
            f'"checkpoint={checkpoint} slot={slot} crc32={checksum}\\n"'
            in records,
            f"record identity: {checkpoint}",
        )
        require(
            f"{zlib.crc32(line.encode()):08x}" == checksum,
            f"record CRC: {checkpoint}",
        )
    require(
        ledger.count(
            "#if defined(CONFIG_PSTORE_GEMINI_A72_PLATFORM_PROVIDER_CLOCK_LEDGER) ||"
        ) == 2,
        "raw all-ones and signature-last conditionals",
    )
    require(ledger.count("memcpy_toio(") == 1, "single retained writer")
    checkpoint = section(
        ledger,
        "bool gemini_protected_readback_ledger_checkpoint",
        "#ifdef CONFIG_PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER",
    )
    require("checkpoint > 1" in checkpoint, "two-checkpoint sequence ceiling")
    require("checkpoint == 1 && !gemini_prb_armed" in checkpoint,
            "ordered second checkpoint")


def validate_binding(root: Path) -> None:
    binding = read(
        root / "Documentation/devicetree/bindings/soc/mediatek/"
        "mediatek,mt6797-a72-platform-provider-clock-observer.yaml"
    )
    for token in (
        "mediatek,mt6797-a72-platform-provider-clock-observer",
        "mediatek,platform-state:",
        "mediatek,provider:",
        "mediatek,clock-backend:",
        "existing handoff-owned CSPM protocol",
        "additionalProperties: false",
    ):
        require(token in binding, f"binding token: {token}")
    for prop in (
        "mediatek,platform-state",
        "mediatek,provider",
        "mediatek,clock-backend",
    ):
        require(binding.count(prop) == 3, f"property/required/example: {prop}")


def validate_observer(root: Path) -> None:
    kconfig = read(root / "drivers/soc/mediatek/Kconfig")
    makefile = read(root / "drivers/soc/mediatek/Makefile")
    observer = read(
        root / "drivers/soc/mediatek/"
        "mt6797-a72-platform-provider-clock-observer.c"
    )
    internal = read(
        root / "drivers/soc/mediatek/"
        "mt6797-a72-platform-provider-clock-observer-internal.h"
    )
    config = section(
        kconfig,
        "config MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER",
        "config MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER",
    )
    for token in (
        "depends on ARM64_MT6797_A72_PROVIDER_OWNER",
        "depends on MTK_MT6797_A72_PLATFORM_STATE",
        "depends on MTK_MT6797_DVFSP_CLOCK_BACKEND",
        "exactly one bounded protected-clock snapshot",
        "one balanced clock-gate pair",
        "no DA921x register-data write",
        "no caller retry",
    ):
        require(token in config, f"observer Kconfig token: {token}")
    require(
        "CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER" in makefile,
        "observer Makefile wiring",
    )

    capture = section(
        observer,
        "int mt6797_a72_ppc_capture(",
        "static struct device *mt6797_a72_ppc_get_platform",
    )
    order = (
        "ops->platform(context, platform, &snapshot->platform)",
        "snapshot->platform.valid",
        "ops->provider(context, &snapshot->provider)",
        "snapshot->provider.valid",
        "ops->checkpoint(context, 0)",
        "ops->clock(context, clock, &snapshot->clock)",
        "snapshot->clock_returned = true",
        "ops->checkpoint(context, 1)",
        "snapshot->valid =",
    )
    positions = [capture.index(token) for token in order]
    require(positions == sorted(positions), "exact third-reader call order")
    require(capture.count("ops->platform(") == 1, "one platform call")
    require(capture.count("ops->provider(") == 1, "one provider call")
    require(capture.count("ops->clock(") == 1, "one protected-clock call")
    require(capture.count("ops->checkpoint(") == 2, "two checkpoint calls")
    require(
        capture.count("memset(snapshot, 0, sizeof(*snapshot));") == 2,
        "zero entry and every pre-clock error",
    )
    require("for (" not in capture and "while (" not in capture,
            "no caller retry loop")
    require(
        "A returned hardware call is terminal" in capture and
        capture.rfind("return 0;") < capture.index("out_clear:"),
        "terminal success return after clock attempt",
    )

    for helper, prop, lookup, compatible in (
        ("get_platform", "mediatek,platform-state", "of_find_device_by_node", None),
        ("get_provider", "mediatek,provider", "of_find_i2c_device_by_node",
         "dlg,da9214-legacy"),
        ("get_clock", "mediatek,clock-backend", "of_find_device_by_node",
         "mediatek,mt6797-dvfsp-clock-backend"),
    ):
        start = f"static struct device *mt6797_a72_ppc_{helper}"
        next_start = "static struct device *" if helper != "get_clock" else "static void"
        body = section(observer, start, next_start)
        require(prop in body, f"dependency property: {prop}")
        require(lookup in body, f"dependency lookup: {lookup}")
        require("device_is_bound" in body, f"dependency bound gate: {prop}")
        require("ERR_PTR(-EPROBE_DEFER)" in body, f"dependency defer: {prop}")
        if compatible:
            require(compatible in body, f"dependency compatible: {compatible}")

    probe = section(
        observer,
        "static int mt6797_a72_ppc_probe",
        "static const struct of_device_id",
    )
    probe_order = (
        "mt6797_a72_ppc_get_platform(dev)",
        "mt6797_a72_ppc_get_provider(dev)",
        "mt6797_a72_ppc_get_clock(dev)",
        "mt6797_a72_ppc_capture(platform, provider, clock",
        "mt6797_a72_ppc_log(dev, &snapshot)",
        "put_device(clock)",
        "put_device(provider)",
        "put_device(platform)",
    )
    probe_positions = [probe.index(token) for token in probe_order]
    require(probe_positions == sorted(probe_positions),
            "resolve/hold/release dependency order")
    require(probe.count("mt6797_a72_ppc_capture(") == 1, "one capture call")
    require(observer.count("mt6797_a72_platform_state_snapshot(") == 1,
            "one platform source caller")
    require(observer.count("mt6797_a72_provider_snapshot(") == 1,
            "one provider source caller")
    require(observer.count("mt6797_dvfsp_clock_backend_read(") == 1,
            "one protected-clock source caller")
    for forbidden in (
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_smc(",
        "mt6797_a72_provider_acquire(",
        "mt6797_a72_provider_release(",
        "regmap_write(",
        "i2c_transfer(",
        "readl(",
        "writel(",
        "cpu_up(",
        "cpu_down(",
    ):
        require(forbidden not in observer, f"forbidden observer operation: {forbidden}")
    for token in (
        "provider_ready_gate=passed clock_ready_gate=passed",
        "platform_calls=1 platform_samples=2",
        "platform_register_observations=26 provider_snapshots=1",
        "provider_samples=2 provider_i2c_reads=10 provider_i2c_writes=0",
        "retained_write_attempts=2 protected_clock_calls=1",
        "clock_gate_pairs=1",
        "explicit_mmio_writes_maximum=401",
        "explicit_mmio_reads_maximum=419 observer_retries=0",
        "bigidvfs_reads=0 secure_calls=0 provider_acquires=0",
        "provider_releases=0 publisher_calls=0 owner_mutations=0",
        "cpu_requests=0",
    ):
        require(token in observer, f"terminal receipt: {token}")
    for field in (
        "armplldiv_muxsel", "armplldiv_ckdiv", "pll_ll", "pll_l", "pll_cci",
        "cspm_swctrl", "cspm_hwsta",
    ):
        require(field in observer, f"raw clock field logged: {field}")
    for token in (
        "struct mt6797_a72_platform_provider_clock_snapshot",
        "struct mt6797_a72_platform_provider_clock_ops",
        "int mt6797_a72_ppc_capture",
        "bool clock_returned",
        "bool after_checkpoint",
    ):
        require(token in internal, f"injected interface: {token}")


def validate_tests(root: Path) -> None:
    kconfig = read(root / "drivers/soc/mediatek/Kconfig")
    makefile = read(root / "drivers/soc/mediatek/Makefile")
    tests = read(
        root / "drivers/soc/mediatek/"
        "mt6797-a72-platform-provider-clock-observer-test.c"
    )
    config = section(
        kconfig,
        "config MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_KUNIT_TEST",
        "config MTK_MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER",
    )
    for token in (
        "depends on KUNIT=y",
        "depends on MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_OBSERVER",
        "terminal clock errors",
        "No MMIO, retained RAM, I2C, clock, SMC",
    ):
        require(token in config, f"test Kconfig token: {token}")
    require(
        "CONFIG_MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_KUNIT_TEST" in makefile,
        "test Makefile wiring",
    )
    require(tests.count("KUNIT_CASE(") == 8, "eight exact KUnit cases")
    for token in (
        "mt6797_a72_ppc_success_test",
        "mt6797_a72_ppc_not_ready_test",
        "mt6797_a72_ppc_platform_failure_test",
        "mt6797_a72_ppc_provider_failure_test",
        "mt6797_a72_ppc_before_failure_test",
        "mt6797_a72_ppc_clock_error_terminal_test",
        "mt6797_a72_ppc_after_failure_terminal_test",
        "mt6797_a72_ppc_clock_identity_terminal_test",
        "KUNIT_EXPECT_MEMEQ",
        "-EPROBE_DEFER",
        "-ETIMEDOUT",
    ):
        require(token in tests, f"KUnit boundary: {token}")
    require(tests.count("mt6797_a72_ppc_capture(") == 2,
            "one run helper and one not-ready direct call")
    for forbidden in (
        "readl(", "writel(", "i2c_transfer(", "arm_smccc_smc(",
        "mt6797_dvfsp_clock_backend_read(", "cpu_up(", "cpu_down(",
    ):
        require(forbidden not in tests, f"hardware-free tests: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=PHASES, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    validate_ledger(root)
    if PHASES.index(args.phase) >= PHASES.index("binding"):
        validate_binding(root)
    if PHASES.index(args.phase) >= PHASES.index("observer"):
        validate_observer(root)
    if args.phase == "tests":
        validate_tests(root)
    print(f"source_validation={args.phase}-pass")


if __name__ == "__main__":
    main()
