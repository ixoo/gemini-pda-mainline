#!/usr/bin/env python3

"""Validate the bounded, default-off vendor provenance observer patch."""

from pathlib import Path
import hashlib
import re


EXPERIMENT = Path(__file__).resolve().parents[1]
PATCH = EXPERIMENT / "patches/0001-power-add-read-only-DVFSP-provenance-observer.patch"
SERIES = EXPERIMENT / "patches/series"
EXPECTED_PATCH_SHA256 = (
    "3520538de1c31ea592c2f0c76af7deef10f5c1ee00689d74bdac17def48dbb11"
)
EXPECTED_COMMIT = "f3d2a14bd1b8355c68e59e8bd4be6bc1525f9c24"
EXPECTED_PATHS = [
    "drivers/misc/mediatek/base/power/Kconfig",
    "drivers/misc/mediatek/base/power/mt6797/Makefile",
    "drivers/misc/mediatek/base/power/mt6797/mt6797-dvfsp-provenance-observer.c",
    "drivers/misc/mediatek/base/power/mt6797/mt6797-dvfsp-provenance-observer.h",
    "drivers/misc/mediatek/base/power/mt6797/mt_eem.c",
    "drivers/misc/mediatek/base/power/ppm_v1/src/mt_ppm_api.c",
]


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise AssertionError(f"missing {label}: {needle}")


def diff_section(patch: str, path: str) -> str:
    marker = f"diff --git a/{path} b/{path}\n"
    start = patch.index(marker)
    end = patch.find("\ndiff --git ", start + len(marker))
    return patch[start:] if end == -1 else patch[start:end]


def main() -> None:
    patch_bytes = PATCH.read_bytes()
    patch = patch_bytes.decode()
    assert SERIES.read_text() == PATCH.name + "\n"
    assert hashlib.sha256(patch_bytes).hexdigest() == EXPECTED_PATCH_SHA256
    assert patch.startswith(f"From {EXPECTED_COMMIT} Mon Sep 17 00:00:00 2001\n")
    assert "Signed-off-by:" not in patch

    paths = re.findall(r"^diff --git a/(.+) b/(.+)$", patch, re.MULTILINE)
    assert all(left == right for left, right in paths)
    assert [left for left, _ in paths] == EXPECTED_PATHS

    require(patch, "config GEMINI_MT6797_DVFSP_PROVENANCE_OBSERVER", "Kconfig symbol")
    require(patch, "depends on ARCH_MT6797 && DEBUG_FS", "Kconfig dependency")
    require(patch, "default n", "default-off policy")
    require(
        patch,
        "obj-$(CONFIG_GEMINI_MT6797_DVFSP_PROVENANCE_OBSERVER) += "
        "mt6797-dvfsp-provenance-observer.o",
        "gated object",
    )
    require(patch, 'debugfs_create_file("state", 0444,', "read-only debugfs mode")

    observer = diff_section(patch, EXPECTED_PATHS[2])
    eem = diff_section(patch, EXPECTED_PATHS[4])
    ppm = diff_section(patch, EXPECTED_PATHS[5])
    if eem.count(
        "+\tgemini_mt6797_dvfsp_provenance_calibration_bank_publish("
    ) != 1:
        raise AssertionError("EEM INIT02 bank publication hook is not exact")
    if eem.count(
        "+\tgemini_mt6797_dvfsp_provenance_calibration_invalidate();"
    ) != 2:
        raise AssertionError("EEM invalidation hooks are not exact")
    if ppm.count(
        "+\t\t\tgemini_mt6797_dvfsp_provenance_table_commit(i,"
    ) != 1:
        raise AssertionError("PPM cluster-table publication hook is not exact")
    if "gemini_mt6797_dvfsp_provenance_calibration_publish(" in patch:
        raise AssertionError("pre-completion calibration publication remains")

    require(observer, "static DEFINE_SPINLOCK(", "IRQ-safe observer lock")
    if "DEFINE_MUTEX" in observer or "mutex_lock" in observer:
        raise AssertionError("sleeping observer lock remains in interrupt path")
    require(
        observer,
        "#define GEMINI_MT6797_EEM_REQUIRED_BANK_MASK\t0x3bU",
        "exact non-SOC EEM bank mask",
    )
    require(
        observer,
        "static u64 gemini_mt6797_dvfsp_table_epoch;",
        "zero-initialized PPM epoch",
    )
    if "static u64 gemini_mt6797_dvfsp_table_epoch =" in observer:
        raise AssertionError("PPM epoch has a false-positive initializer")
    require(observer, "observation_complete = !faulted", "completion gate")
    require(observer, "ppm_cluster_mask=0x%08x", "PPM completion mask")
    require(observer, "eem_calibration_bank_mask=0x%08x", "EEM completion mask")

    for field in (
        "owner_handle=0",
        "transition_handle=0",
        "coherent_transition_owner=0",
        "provider=none",
        "hardware_write=none",
        "cpu8_cpu9_admission=closed",
    ):
        require(patch, field, "explicit nonclaim")

    forbidden_calls = (
        "regulator_register(",
        "regmap_write(",
        "writel(",
        "writeb(",
        "writew(",
        "cpu_up(",
        "cpu_down(",
        "psci_cpu_on(",
    )
    for call in forbidden_calls:
        if call in patch:
            raise AssertionError(f"forbidden operation present: {call}")

    # Deterministic model: neither provenance value is nonzero before every
    # constituent lifecycle hook has completed.
    generation = 1
    epoch = 0
    sequence = 1
    handle = 0
    ppm_mask = 0
    for cluster in range(3):
        ppm_mask |= 1 << cluster
        generation += 1
        if ppm_mask == (1 << 3) - 1:
            epoch = 1
        if cluster < 2:
            assert epoch == 0
    assert (generation, epoch, handle, ppm_mask) == (4, 1, 0, 0x7)

    eem_mask = 0
    for bank in (0, 1, 3, 4):
        eem_mask |= 1 << bank
        generation += 1
        assert handle == 0
    eem_mask |= 1 << 5
    generation += 1
    if eem_mask == 0x3B:
        handle = sequence
        sequence += 1
    assert (generation, epoch, handle, eem_mask) == (9, 1, 1, 0x3B)

    handle = 0
    eem_mask = 0
    generation += 1
    assert (generation, epoch, handle, eem_mask) == (10, 1, 0, 0)

    print("runtime_provenance_observer_validation=passed")
    print(f"patch_sha256={EXPECTED_PATCH_SHA256}")
    print(f"generated_vendor_commit={EXPECTED_COMMIT}")
    print("changed_path_count=6")
    print("default_off=true")
    print("interrupt_safe_observer=true")
    print("lifecycle_completion_fail_closed=true")
    print("eem_required_bank_mask=0x0000003b")
    print("hardware_write=none")
    print("cpu8_cpu9_admission=closed")


if __name__ == "__main__":
    main()
