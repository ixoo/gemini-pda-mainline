#!/usr/bin/env python3
"""Validate the generated protected-readback remediation source."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def body(text: str, start: str, end: str) -> str:
    first = text.index(start)
    last = text.index(end, first)
    return text[first:last]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    clock = (root / "drivers/soc/mediatek/mt6797-dvfsp-clock-backend.c").read_text()
    big = (root / "drivers/soc/mediatek/mt6797-bigidvfs-backend.c").read_text()
    internal = (
        root / "drivers/soc/mediatek/mt6797-protected-readback-internal.h"
    ).read_text()
    test = (
        root / "drivers/soc/mediatek/mt6797-protected-readback-test.c"
    ).read_text()
    kconfig = (root / "drivers/soc/mediatek/Kconfig").read_text()
    makefile = (root / "drivers/soc/mediatek/Makefile").read_text()

    for token in (
        "MT6797_DVFSP_SEMAPHORE_SETTLE_NS\t200",
        "int mt6797_dvfsp_clock_transport_snapshot",
        "memset(readback, 0, sizeof(*readback))",
        "ops->settle_ns(context, MT6797_DVFSP_SEMAPHORE_SETTLE_NS)",
        "*readback = observed",
    ):
        require(token in clock, f"clock token: {token}")
    clock_snapshot = body(
        clock,
        "int mt6797_dvfsp_clock_transport_snapshot",
        "static void\nmt6797_dvfsp_clock_mark_fault",
    )
    require(
        clock_snapshot.index("mt6797_dvfsp_clock_semaphore_acquire")
        < clock_snapshot.index("ops->settle_ns")
        < clock_snapshot.index("observed.armplldiv_muxsel")
        < clock_snapshot.index("mt6797_dvfsp_clock_semaphore_release")
        < clock_snapshot.index("*readback = observed"),
        "clock acquire-settle-read-release-publish order",
    )
    require(clock_snapshot.count("ops->settle_ns(") == 1, "one exact settle")
    wrapper = body(
        clock,
        "int mt6797_dvfsp_clock_backend_read",
        "EXPORT_SYMBOL_GPL(mt6797_dvfsp_clock_backend_read)",
    )
    require(
        wrapper.index("memset(readback, 0, sizeof(*readback))")
        < wrapper.index("if (!dev)"),
        "clock caller record cleared before device validation",
    )
    require(
        wrapper.index("mt6797_dvfsp_clock_transport_snapshot")
        < wrapper.index("++backend->sample_generation")
        < wrapper.index("*readback = observed"),
        "clock generation and publication after complete transport",
    )

    for token in (
        "int mt6797_bigidvfs_transport_snapshot",
        "mt6797_bigidvfs_read_sample(ops, context, &first)",
        "mt6797_bigidvfs_read_sample(ops, context, &second)",
        "memcmp(&first, &second, sizeof(first))",
        "return -EAGAIN",
        "*readback = observed",
    ):
        require(token in big, f"BigiDVFS token: {token}")
    big_snapshot = body(
        big,
        "int mt6797_bigidvfs_transport_snapshot",
        "static void mt6797_bigidvfs_mark_fault",
    )
    require(big_snapshot.count("mt6797_bigidvfs_read_sample(") == 2,
            "two complete BigiDVFS samples")
    require(
        big_snapshot.index("memset(readback, 0, sizeof(*readback))")
        < big_snapshot.index("mt6797_bigidvfs_read_sample")
        < big_snapshot.index("memcmp(&first, &second")
        < big_snapshot.index("*readback = observed"),
        "BigiDVFS clear-sample-compare-publish order",
    )
    big_wrapper = body(
        big,
        "int mt6797_bigidvfs_backend_read",
        "EXPORT_SYMBOL_GPL(mt6797_bigidvfs_backend_read)",
    )
    require(
        "if (ret != -EAGAIN)\n\t\t\tmt6797_bigidvfs_mark_fault" in big_wrapper,
        "unstable snapshot remains retryable",
    )
    require(
        big_wrapper.index("memset(readback, 0, sizeof(*readback))")
        < big_wrapper.index("if (!dev)"),
        "BigiDVFS caller record cleared before device validation",
    )
    require(
        big_wrapper.index("mt6797_bigidvfs_transport_snapshot")
        < big_wrapper.index("++backend->sample_generation")
        < big_wrapper.index("*readback = observed"),
        "BigiDVFS generation and publication after stable transport",
    )
    require(big.count("arm_smccc_smc(") == 1, "one exact secure read primitive")
    require("MT6797_BIGIDVFS_FID_READ" in big, "read-only secure FID")

    for token in (
        "struct mt6797_dvfsp_clock_transport_ops",
        "struct mt6797_bigidvfs_transport_ops",
        "mt6797_dvfsp_clock_transport_snapshot",
        "mt6797_bigidvfs_transport_snapshot",
    ):
        require(token in internal, f"internal test seam: {token}")

    for token in (
        "mt6797_clock_snapshot_order_test",
        "mt6797_clock_acquire_timeout_test",
        "mt6797_clock_release_timeout_test",
        "mt6797_bigidvfs_snapshot_order_test",
        "mt6797_bigidvfs_faults_test",
        "mt6797_bigidvfs_unstable_test",
        "state->event_count, 25U",
        "state->event_count, 602U",
        "state->event_count, 623U",
        "fault <= 8",
        'name = "mt6797-protected-readback"',
    ):
        require(token in test, f"KUnit token: {token}")
    require(test.count("KUNIT_CASE(mt6797_") == 6, "six focused KUnit cases")

    require(
        "config MTK_MT6797_PROTECTED_READBACK_KUNIT_TEST" in kconfig,
        "focused KUnit Kconfig",
    )
    require(
        "CONFIG_MTK_MT6797_PROTECTED_READBACK_KUNIT_TEST" in makefile,
        "focused KUnit object",
    )

    added = clock + big + internal + test
    for forbidden in (
        "MT6797_BIGIDVFS_FID_WRITE",
        "arm_smccc_hvc(",
        "cpu_up(",
        "cpu_down(",
        "psci_ops",
        "status = \"okay\"",
    ):
        require(forbidden not in added, f"forbidden effect: {forbidden}")

    print("source_validation=pass")
    print("clock_settle_ns=200-once-after-acquire")
    print("clock_publish=after-successful-release")
    print("bigidvfs_samples=2-fixed")
    print("bigidvfs_success_reads=8")
    print("caller_failure_record=all-zero")
    print("kunit_cases=6")
    print("secure_write=none")
    print("cpu_admission=closed")
    print("device_action=none")


if __name__ == "__main__":
    main()
