#!/usr/bin/env python3
"""Validate the generated MT6797 A72 default-off binder source."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


EXPECTED_NEW_HASHES = {
    "include/linux/soc/mediatek/mt6797-a72-binder.h":
        "2580cb7c1381b89683a7c1b4e4b58057b6b63e30df7520d1b5be15653728622a",
    "drivers/soc/mediatek/mt6797-a72-binder.c":
        "a0d1ca123e6be122b3579898da19e13e5e723457a9457a2873dda627e16552bf",
    "drivers/soc/mediatek/mt6797-a72-binder-internal.h":
        "9f4bbcd403748546622590f6a6c391429477400b01f4c41049db26f66b04728c",
    "drivers/soc/mediatek/mt6797-a72-binder-test.c":
        "d6212559e2389e9a0e1cb94588d4c78761e8b55e64d8c9bb62854eac9d3ed2ee",
    "Documentation/devicetree/bindings/soc/mediatek/mediatek,mt6797-a72-binder.yaml":
        "1843b00a0510fe1ec8d4aefe8b0f870ad3d604b757d13836693863b33a79e248",
}

EXISTING_PATHS = (
    "arch/arm64/include/asm/mt6797_a72_membership.h",
    "arch/arm64/kernel/mt6797_a72_membership.c",
    "include/linux/mt6797-a72-provider.h",
    "arch/arm64/kernel/mt6797_psci.c",
    "drivers/soc/mediatek/Kconfig",
    "drivers/soc/mediatek/Makefile",
    "arch/arm64/kernel/mt6797_a72_membership_test.c",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(text: str, needles: tuple[str, ...], label: str) -> None:
    for needle in needles:
        if needle not in text:
            raise SystemExit(f"{label}: missing {needle!r}")


def reject(text: str, needles: tuple[str, ...], label: str) -> None:
    for needle in needles:
        if needle in text:
            raise SystemExit(f"{label}: forbidden {needle!r}")


def read_exact(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"generated path is not an exact file: {relative}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    texts = {
        relative: read_exact(root, relative)
        for relative in (*EXISTING_PATHS, *EXPECTED_NEW_HASHES)
    }
    for relative, expected in EXPECTED_NEW_HASHES.items():
        actual = sha256(root / relative)
        if actual != expected:
            raise SystemExit(
                f"generated hash changed: {relative}: {actual} != {expected}"
            )

    membership_header = texts[EXISTING_PATHS[0]]
    membership = texts[EXISTING_PATHS[1]]
    provider_header = texts[EXISTING_PATHS[2]]
    psci = texts[EXISTING_PATHS[3]]
    kconfig = texts[EXISTING_PATHS[4]]
    makefile = texts[EXISTING_PATHS[5]]
    membership_tests = texts[EXISTING_PATHS[6]]
    public_header = texts[next(iter(EXPECTED_NEW_HASHES))]
    binder = texts["drivers/soc/mediatek/mt6797-a72-binder.c"]
    internal = texts[
        "drivers/soc/mediatek/mt6797-a72-binder-internal.h"
    ]
    tests = texts["drivers/soc/mediatek/mt6797-a72-binder-test.c"]
    schema = texts[
        "Documentation/devicetree/bindings/soc/mediatek/mediatek,mt6797-a72-binder.yaml"
    ]

    require(membership_header, (
        "#define MT6797_A72_TRANSACTION_ABI 3",
        "enum mt6797_a72_public_admission {",
        "MT6797_A72_PUBLIC_ADMISSION_CLAIMED",
        "u32 cpu8_success_published;",
        "mt6797_a72_membership_claim_cpu8(",
        "mt6797_a72_membership_reject_cpu8(",
        "mt6797_a72_membership_begin_cpu8_on(",
        "mt6797_a72_membership_publish_cpu8_success(",
        "mt6797_a72_membership_finalize_cpu8_success(",
    ), "membership header")
    require(membership, (
        "bool mt6797_a72_provider_available(void)",
        "available = !!a72_provider_ops;",
        "a72_owner.phase != MT6797_A72_PHASE_VERIFYING",
        "MT6797_A72_PUBLIC_ADMISSION_PREFLIGHT",
        "MT6797_A72_PUBLIC_ADMISSION_CLAIMED",
        "a72_owner.active.budgets.cpu_on = MT6797_A72_BUDGET_CONSUMED;",
        "a72_owner.members = BIT(0);",
        "a72_owner.phase = MT6797_A72_PHASE_VERIFYING;",
        "a72_owner.phase = MT6797_A72_PHASE_IDLE;",
    ), "membership owner")
    require(provider_header, (
        "bool mt6797_a72_provider_available(void);",
    ), "provider header")
    require(membership_tests, (
        "mt6797_a72_owner_binder_success_handoff",
        "mt6797_a72_owner_binder_p32_from_verifying",
        "mt6797_a72_owner_binder_clean_rejection",
        "mt6797_a72_owner_binder_p29_without_provider",
        "KUNIT_EXPECT_EQ(test, snapshot.phase,",
        "(u32)MT6797_A72_PHASE_VERIFYING",
        "mt6797_a72_membership_publish_p32(",
        "mt6797_a72_membership_reject_cpu8(&transaction)",
    ), "membership binder KUnit")
    require(psci, (
        "#include <linux/soc/mediatek/mt6797-a72-binder.h>",
        "return mt6797_a72_binder_preflight(cpu, target);",
        "return mt6797_a72_binder_validate(cpu, tasks_frozen, target);",
        "ret = mt6797_a72_binder_failure(cpu, error, &publish_p32);",
        "return mt6797_a72_binder_cpu_boot(cpu, cpu_psci_ops.cpu_boot);",
        ".cpu_up_secondary_complete =",
        ".cpu_up_complete = mt6797_psci_cpu_up_complete,",
    ), "PSCI binder hooks")
    require(kconfig, (
        "config MTK_MT6797_A72_DEFAULT_OFF_BINDER\n",
        "depends on MTK_MT6797_A72_TRANSITION_EXECUTOR",
        "depends on PSTORE_GEMINI_TRANSITION_LEDGER",
        "\tdefault n\n",
        "config MTK_MT6797_A72_DEFAULT_OFF_BINDER_KUNIT_TEST\n",
        "\tselect ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST\n",
        "\tselect MTK_MT6797_A72_TRANSITION_EXECUTOR_KUNIT_TEST\n",
    ), "binder Kconfig")
    require(makefile, (
        "obj-$(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER) += mt6797-a72-binder.o",
        "obj-$(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER_KUNIT_TEST) += mt6797-a72-binder-test.o",
    ), "binder Makefile")
    require(public_header, (
        "typedef int (*mt6797_a72_cpu_boot_fn)(unsigned int cpu);",
        "int mt6797_a72_binder_cpu_boot(unsigned int cpu,",
        "int mt6797_a72_binder_secondary_complete(unsigned int cpu);",
        "int mt6797_a72_binder_failure(unsigned int cpu, int error,",
    ), "public binder header")
    require(internal, (
        "struct mt6797_a72_binder_backend_ops {",
        "int (*ledger_checkpoint)(u64 attempt_id, u32 phase, u32 stage,",
        "int (*membership_finalize_success)(",
        "int (*ipi_call)(unsigned int cpu, smp_call_func_t func, void *info,",
    ), "binder internal header")
    require(binder, (
        ".provider_available = mt6797_a72_provider_available,",
        "&binder->transaction.provider_identity;",
        "&binder->transaction.provider_acquire_proof.held_identity;",
        "response->origin_generation == response->held_handle.generation",
        "timeout_ms != MTK_WDT_RECOVERY_TIMEOUT_MS",
        "ret = binder->backend->membership_begin_cpu_on(&binder->transaction);",
        "return binder->cpu_boot(cpu);",
        "mt6797_a72_binder_transition_secondary(void *context, unsigned int cpu)",
        "mt6797_a72_binder_drive_secondary(",
        "return binder->backend->membership_publish_success(",
        "GEMINI_TRANSITION_LEDGER_TERMINAL, result->last_stage,",
        "return binder->backend->membership_finalize_success(",
        "MT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO;",
        "mediatek,watchdog",
        "mediatek,platform-state",
        "mediatek,bigidvfs",
        "if (!mt6797_a72_provider_available())",
        "device_link_add(dev, &pdev->dev, DL_FLAG_AUTOREMOVE_CONSUMER)",
        "static void mt6797_a72_binder_remove(struct platform_device *pdev)",
        "WRITE_ONCE(mt6797_a72_ready_binder, NULL);",
        ".remove = mt6797_a72_binder_remove,",
        "builtin_platform_driver(mt6797_a72_binder_driver);",
    ), "binder source")
    require(tests, (
        "KUNIT_EXPECT_EQ(test, state->regular_checkpoints, 20U);",
        "KUNIT_EXPECT_EQ(test, state->terminal_checkpoints, 1U);",
        "KUNIT_EXPECT_EQ(test, state->binder.result.cpu_off_requests, 0U);",
        "KUNIT_EXPECT_EQ(test, state->binder.result.retries, 0U);",
        "TEST_EVENT_MEMBERSHIP",
        "TEST_EVENT_TERMINAL",
        "TEST_EVENT_FINALIZE",
        "mt6797_binder_terminal_failure_test",
        "mt6797_binder_preiso_checkpoint_test",
        "mt6797_binder_malformed_owners_test",
        "mt6797_binder_one_shot_test",
        "#define TEST_PROVIDER_GENERATION 17ULL",
        "#define TEST_PROVIDER_COOKIE 19ULL",
    ), "binder KUnit")
    require(schema, (
        "const: mediatek,mt6797-a72-binder",
        "mediatek,watchdog:",
        "mediatek,platform-state:",
        "mediatek,bigidvfs:",
        "additionalProperties: false",
    ), "binder schema")

    if binder.count("return binder->cpu_boot(cpu);") != 1:
        raise SystemExit("production delegated CPU_ON call count changed")
    if binder.count("mutex_lock(&mt6797_a72_binder_publish_lock);") != 8:
        raise SystemExit("binder publication serialization changed")
    if binder.count(
        "device_link_add(dev, &pdev->dev, DL_FLAG_AUTOREMOVE_CONSUMER)"
    ) != 1:
        raise SystemExit("binder supplier-link count changed")
    if tests.count("KUNIT_CASE(") != 5:
        raise SystemExit("focused binder KUnit case count changed")
    if membership_tests.count(
        "KUNIT_CASE(mt6797_a72_owner_binder_"
    ) != 4:
        raise SystemExit("focused membership KUnit case count changed")
    membership_event = tests.index("TEST_EVENT_MEMBERSHIP),")
    terminal_event = tests.index("TEST_EVENT_TERMINAL));", membership_event)
    finalize_event = tests.index("TEST_EVENT_FINALIZE));", terminal_event)
    if not membership_event < terminal_event < finalize_event:
        raise SystemExit("membership/terminal/finalize assertion order changed")

    reject(binder, (
        "cpu_down(", "cpu_off(", "provider_snapshot(",
        "mt6797_a72_provider_snapshot(", "msleep(", "usleep_range(",
        "while (", "for (",
        "held_handle.generation == binder->transaction.identity.generation",
    ), "binder source")
    reject(psci, ("cpu_down(", "cpu_off("), "PSCI binder hooks")
    reject(schema, ("examples:", "status = \"okay\"", "status = 'okay'"),
           "binder schema")

    print("validation=a72-default-off-binder-source")
    print("generated_files=5")
    print("membership_kunit_cases=4")
    print("binder_kunit_cases=5")
    print("production_cpu_on_delegates=1")
    print("production_cpu_off_calls=0")
    print("production_retry_loops=0")
    print("probe_provider_hardware_reads=0")
    print("supplier_device_links=managed-consumer")
    print("binder_publication_serialized=true")
    print("base_dt_enablements=0")
    print("membership_before_terminal=true")
    print("terminal_before_finalize=true")
    print("result=pass")


if __name__ == "__main__":
    main()
