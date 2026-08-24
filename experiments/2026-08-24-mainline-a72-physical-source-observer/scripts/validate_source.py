#!/usr/bin/env python3
"""Validate the generated A72 physical-source observer source."""

from __future__ import annotations

import argparse
import zlib
from pathlib import Path


PHASES = ("ledger", "observer", "binding", "dts", "tests")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def section(text: str, start: str, end: str) -> str:
    first = text.index(start)
    last = text.index(end, first)
    return text[first:last]


def validate_ledger(root: Path) -> None:
    kconfig = (root / "fs/pstore/Kconfig").read_text(encoding="utf-8")
    ledger = (
        root / "fs/pstore/gemini_protected_readback_ledger.c"
    ).read_text(encoding="utf-8")
    mode = section(
        kconfig,
        "config PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER",
        "config PSTORE_GEMINI_PROTECTED_READBACK_LEDGER",
    )
    for token in (
        "depends on PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "depends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y",
        "Require both raw headers to be all ones before the first write",
        "signature-last",
        "no-overwrite, no-clear, and no-retry",
        "at most two short retained-RAM writes",
    ):
        require(token in mode, f"ledger Kconfig token: {token}")
    require(
        "MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y ||"
        in kconfig,
        "base ledger accepts physical observer",
    )

    layout = section(
        ledger, "#define GEMINI_PRB_RESERVE_BASE", "#define GEMINI_PRB_HEADER_SIZE"
    )
    require(
        "defined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER)" in layout,
        "physical ledger selects first-dmesg layout",
    )
    require(
        "GEMINI_PRB_LEDGER_BASE\t\tGEMINI_PRB_RESERVE_BASE" in layout,
        "physical ledger base",
    )
    require("GEMINI_PRB_SLOT_COUNT\t\t2" in layout, "two retained slots")
    require("GEMINI_PRB_FIRST_OWNED_SLOT\t0" in layout, "first slot index")

    records = section(
        ledger,
        "#ifdef CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER",
        "#elif defined(CONFIG_PSTORE_GEMINI_PROTECTED_CLOCK_FIRST_DMESG_CALL_QUALIFICATION)",
    )
    expected = (
        ("before-bigidvfs", 1, "47eaad49"),
        ("after-bigidvfs", 2, "d03ca6dc"),
    )
    require(records.count("GEMINI_A72_PHYSICAL_SOURCE_V1") == 2,
            "two physical-source records")
    require(records.count("token=GPSQ-20260824-A") == 2,
            "two exact physical-source tokens")
    for checkpoint, slot, checksum in expected:
        line = (
            "GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A "
            f"checkpoint={checkpoint} slot={slot}"
        )
        require(f"{line} crc32={checksum}" in records,
                f"record identity: {checkpoint}")
        require(f"{zlib.crc32(line.encode()):08x}" == checksum,
                f"record CRC: {checkpoint}")

    require(
        ledger.count(
            "#if defined(CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER) ||"
        ) == 2,
        "raw all-ones and signature-last conditionals",
    )
    require(ledger.count("memcpy_toio(") == 1, "single retained writer")
    require(
        ledger.count("bool gemini_protected_readback_ledger_checkpoint(") == 1,
        "single checkpoint implementation",
    )
    preflight = section(
        ledger,
        "static bool gemini_prb_prefix_valid",
        "bool gemini_protected_readback_ledger_checkpoint",
    )
    require("i < GEMINI_PRB_SLOT_COUNT" in preflight, "all slots preflighted")
    require("checkpoint == 1 && i == GEMINI_PRB_FIRST_OWNED_SLOT" in preflight,
            "second checkpoint accepts only exact first record")


def validate_observer(root: Path) -> None:
    kconfig = (root / "drivers/soc/mediatek/Kconfig").read_text(encoding="utf-8")
    makefile = (root / "drivers/soc/mediatek/Makefile").read_text(encoding="utf-8")
    observer = (
        root / "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
    ).read_text(encoding="utf-8")
    internal = (
        root
        / "drivers/soc/mediatek/mt6797-a72-physical-source-observer-internal.h"
    ).read_text(encoding="utf-8")
    config = section(
        kconfig,
        "config MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER",
        "config MTK_MT6797_PROTECTED_READBACK_OBSERVER",
    )
    for token in (
        "depends on ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR",
        "depends on MTK_MT6797_A72_PLATFORM_STATE",
        "depends on MTK_MT6797_DVFSP_CLOCK_BACKEND",
        "depends on MTK_MT6797_DVFSP_BIGIDVFS_BACKEND",
        "default n",
        "exactly one two-sample BigiDVFS read",
    ):
        require(token in config, f"observer Kconfig token: {token}")
    require(
        "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER" in makefile,
        "observer Makefile wiring",
    )

    capture = section(
        observer,
        "int mt6797_a72_physical_source_capture(",
        "static const struct mt6797_a72_direct_source_ops",
    )
    order = (
        "readers->platform(",
        "readers->provider(",
        "readers->clock(",
        "readers->checkpoint(0)",
        "readers->bigidvfs(",
        "readers->checkpoint(1)",
    )
    positions = [capture.index(token) for token in order]
    require(positions == sorted(positions), "exact component/checkpoint order")
    for token in order:
        require(capture.count(token) == 1, f"one capture call: {token}")
    require(capture.count("memset(snapshot, 0, sizeof(*snapshot));") == 2,
            "capture clears entry and every error")
    require(
        capture.index("snapshot->abi = MT6797_A72_DIRECT_SOURCE_ABI")
        > positions[-1],
        "source ABI published after final checkpoint",
    )
    require(capture.index("snapshot->valid = 1") > positions[-1],
            "source validity published after final checkpoint")
    require("for (" not in capture and "while (" not in capture,
            "capture has no retry loop")

    run = section(
        observer,
        "int mt6797_a72_physical_source_run(",
        "static const struct mt6797_a72_physical_source_runtime_ops",
    )
    lifecycle = (
        "runtime->register_source(",
        "runtime->snapshot(",
        "runtime->unregister_source(",
    )
    positions = [run.index(token) for token in lifecycle]
    require(positions == sorted(positions), "register/snapshot/unregister order")
    require(all(run.count(token) == 1 for token in lifecycle),
            "one register, snapshot, and unregister")
    require("if (ret)\n\t\tmemset(snapshot, 0" in run,
            "public failure remains all-zero")

    get_device = section(
        observer,
        "mt6797_a72_physical_source_get_device",
        "static void mt6797_a72_physical_source_log",
    )
    for token in (
        "of_find_device_by_node",
        "device_is_bound",
        "put_device(&source->dev)",
    ):
        require(token in get_device, f"bound reference contract: {token}")
    probe = section(
        observer,
        "mt6797_a72_physical_source_probe",
        "static const struct of_device_id",
    )
    get_order = (
        '"mediatek,platform-state"',
        '"mediatek,clock-backend"',
        '"mediatek,bigidvfs-backend"',
    )
    get_positions = [probe.index(token) for token in get_order]
    require(get_positions == sorted(get_positions), "device reference acquisition order")
    put_order = (
        "put_device(context.bigidvfs)",
        "put_device(context.clock)",
        "put_device(context.platform)",
    )
    put_positions = [probe.index(token) for token in put_order]
    require(put_positions == sorted(put_positions), "reverse device release order")
    require(
        probe.index("mt6797_a72_physical_source_run(") < put_positions[0],
        "references retained through public snapshot and unregister",
    )

    for forbidden in (
        "mt6797_a72_provider_acquire(",
        "mt6797_a72_provider_release(",
        "mt6797_a72_a34_evaluate(",
        "mt6797_a72_membership_publish_up(",
        "cpu_up(",
        "cpu_down(",
        "arm_smccc_smc(",
        "writel(",
        "regmap_write(",
    ):
        require(forbidden not in observer, f"forbidden observer operation: {forbidden}")
    for token in (
        "registrations=1 callbacks=1 unregisters=1",
        "platform_calls=1 provider_snapshots=1 clock_calls=1",
        "retained_writes=2 bigidvfs_calls=1 bigidvfs_smc_reads=8",
        "compositor_retries=0 provider_acquires=0 provider_releases=0",
        "publisher_calls=0 owner_mutations=0 cpu_requests=0",
    ):
        require(token in observer, f"terminal receipt: {token}")
    for token in (
        "struct mt6797_a72_physical_source_reader_ops",
        "struct mt6797_a72_physical_source_runtime_ops",
        "mt6797_a72_physical_source_capture",
        "mt6797_a72_physical_source_run",
    ):
        require(token in internal, f"internal injected contract: {token}")


def validate_binding(root: Path) -> None:
    binding = (
        root
        / "Documentation/devicetree/bindings/soc/mediatek/mediatek,mt6797-a72-physical-source-observer.yaml"
    ).read_text(encoding="utf-8")
    for token in (
        "mediatek,mt6797-a72-physical-source-observer",
        "mediatek,platform-state:",
        "mediatek,clock-backend:",
        "mediatek,bigidvfs-backend:",
        "additionalProperties: false",
    ):
        require(token in binding, f"binding token: {token}")
    require(binding.count("$ref: /schemas/types.yaml#/definitions/phandle") == 3,
            "three phandles")


def validate_dts(root: Path) -> None:
    makefile = (
        root / "arch/arm64/boot/dts/mediatek/Makefile"
    ).read_text(encoding="utf-8")
    dts = (
        root
        / "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda-a72-physical-source.dts"
    ).read_text(encoding="utf-8")
    require("mt6797-gemini-pda-a72-physical-source.dtb" in makefile,
            "candidate DTB Makefile entry")
    for token in (
        '#include "mt6797-gemini-pda.dts"',
        'compatible = "mediatek,mt6797-a72-physical-source-observer";',
        "mediatek,platform-state = <&a72_platform_state>;",
        "mediatek,clock-backend = <&dvfsp_clock_backend>;",
        "mediatek,bigidvfs-backend = <&dvfsp_bigidvfs_backend>;",
        "&a72_platform_state",
        "&dvfsp_clock_backend",
        "&dvfsp_bigidvfs_backend",
    ):
        require(token in dts, f"candidate DT token: {token}")
    require(dts.count('status = "okay";') == 4,
            "only observer and three sources enabled")
    require("model =" not in dts, "candidate preserves base model contract")


def validate_tests(root: Path) -> None:
    kconfig = (root / "drivers/soc/mediatek/Kconfig").read_text(encoding="utf-8")
    makefile = (root / "drivers/soc/mediatek/Makefile").read_text(encoding="utf-8")
    tests = (
        root
        / "drivers/soc/mediatek/mt6797-a72-physical-source-observer-test.c"
    ).read_text(encoding="utf-8")
    config = section(
        kconfig,
        "config MTK_MT6797_A72_PHYSICAL_SOURCE_KUNIT_TEST",
        "config MTK_MT6797_PROTECTED_READBACK_OBSERVER",
    )
    for token in (
        "depends on KUNIT=y",
        "depends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER",
        "No MMIO, I2C, retained RAM, SMC, owner mutation",
    ):
        require(token in config, f"test Kconfig token: {token}")
    require("CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_KUNIT_TEST" in makefile,
            "test Makefile wiring")
    require(tests.count("KUNIT_CASE(") == 4, "four focused cases")
    for token in (
        "MT6797_SOURCE_PLATFORM",
        "MT6797_SOURCE_PROVIDER",
        "MT6797_SOURCE_CLOCK",
        "MT6797_SOURCE_CHECKPOINT_0",
        "MT6797_SOURCE_BIGIDVFS",
        "MT6797_SOURCE_CHECKPOINT_1",
        "state.fail_stage = stage",
        "MT6797_SOURCE_UNREGISTER",
        'name = "mt6797-a72-physical-source"',
    ):
        require(token in tests, f"focused test token: {token}")
    for forbidden in (
        "arm_smccc_smc(",
        "readl(",
        "writel(",
        "i2c_transfer(",
        "gemini_protected_readback_ledger_checkpoint(",
        "cpu_up(",
    ):
        require(forbidden not in tests, f"test physical operation: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=PHASES, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    selected = PHASES.index(args.phase)
    validators = (
        validate_ledger,
        validate_observer,
        validate_binding,
        validate_dts,
        validate_tests,
    )
    for validator in validators[: selected + 1]:
        validator(root)
    print(f"validation=a72-physical-source-{args.phase}")
    print("retained_records=1,2")
    print("retained_maximum_writes=2")
    print("clock_calls=1")
    print("bigidvfs_calls=1")
    print("bigidvfs_smc_reads=8")
    print("provider_transactions=0")
    print("publisher_calls=0")
    print("owner_mutations=0")
    print("cpu_requests=0")
    print("result=pass")


if __name__ == "__main__":
    main()
