#!/usr/bin/env python3
"""Apply deterministic one-shot CPU8 admission-controller source edits."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil


PARENT_HASHES = {
    "include/linux/soc/mediatek/mt6797-a72-binder.h":
        "46ff82bd82176dfbb79388ce2085bba1ebe745b7b295d07ccc853f58b62f38f8",
    "drivers/soc/mediatek/mt6797-a72-binder.c":
        "7d40050e22686f68bcad9dfe06ef8b1c3ebf8934abdb6311c78c1b9ef6283c1a",
    "drivers/soc/mediatek/mt6797-a72-physical-source-observer-internal.h":
        "db0209cf2287107dcba6d3933dc5010f32b074afe0ad0d24847c1f4e9ed3a2d0",
    "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c":
        "71f57d0bc5a708b0729104c9c562c480f6c27f112677fdad0e2c4ead8aea19e8",
    "drivers/soc/mediatek/Kconfig":
        "e27e6e0c24cb5cca5e1ea33e892a5752389bb6d54ad64ca559a81c94895f9420",
    "drivers/soc/mediatek/Makefile":
        "c7dc93db73d9d57a49588eb17ee6b66e45f5c612f4880dea2ddcad060668eeec",
    "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts":
        "08f8b007379e52daa441d8b48731f8cd4a0549a3c1d887791762db68320fdbd8",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"source path is not an exact file: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(
                f"source hash changed: {relative}: {actual} != {expected}"
            )


def replace_once(path: Path, old: str, new: str) -> None:
    source = path.read_text(encoding="utf-8")
    if source.count(old) != 1:
        raise SystemExit(
            f"{path}: expected one anchor: {old.splitlines()[0]}"
        )
    path.write_text(source.replace(old, new, 1), encoding="utf-8")


def apply_binder_header(path: Path) -> None:
    replace_once(
        path,
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER)\n"
        "int mt6797_a72_binder_preflight(unsigned int cpu, enum cpuhp_state target);\n",
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER)\n"
        "bool mt6797_a72_binder_available(void);\n"
        "int mt6797_a72_binder_preflight(unsigned int cpu, enum cpuhp_state target);\n",
    )
    replace_once(
        path,
        "#else\n"
        "static inline int\n"
        "mt6797_a72_binder_preflight(unsigned int cpu, enum cpuhp_state target)\n",
        "#else\n"
        "static inline bool mt6797_a72_binder_available(void)\n"
        "{\n"
        "\treturn false;\n"
        "}\n\n"
        "static inline int\n"
        "mt6797_a72_binder_preflight(unsigned int cpu, enum cpuhp_state target)\n",
    )


def apply_binder_source(path: Path) -> None:
    anchor = (
        "static struct mt6797_a72_binder *mt6797_a72_binder_ready(void)\n"
        "{\n"
        "\treturn READ_ONCE(mt6797_a72_ready_binder);\n"
        "}\n\n"
    )
    addition = (
        "bool mt6797_a72_binder_available(void)\n"
        "{\n"
        "\tbool available;\n\n"
        "\tmutex_lock(&mt6797_a72_binder_publish_lock);\n"
        "\tavailable = !!mt6797_a72_binder_ready();\n"
        "\tmutex_unlock(&mt6797_a72_binder_publish_lock);\n"
        "\treturn available;\n"
        "}\n\n"
    )
    replace_once(path, anchor, anchor + addition)


def apply_source_header(path: Path) -> None:
    anchor = (
        "int\n"
        "mt6797_a72_physical_source_capture(void *context,\n"
        "\t\t\t\t   struct mt6797_a72_direct_source_snapshot *snapshot);\n"
    )
    addition = (
        "void\n"
        "mt6797_a72_source_context_init(struct mt6797_a72_physical_source_context *context,\n"
        "\t\t\t       struct device *platform, struct device *clock,\n"
        "\t\t\t       struct device *bigidvfs);\n"
        "int\n"
        "mt6797_a72_source_register(struct mt6797_a72_physical_source_context *context);\n"
        "void\n"
        "mt6797_a72_source_unregister(struct mt6797_a72_physical_source_context *context);\n"
    )
    replace_once(path, anchor, addition + anchor)


def apply_source_body(path: Path) -> None:
    readers = (
        "static const struct mt6797_a72_physical_source_reader_ops\n"
        "mt6797_a72_physical_source_readers = {\n"
        "\t.platform = mt6797_a72_platform_state_snapshot,\n"
        "\t.provider = mt6797_a72_provider_snapshot,\n"
        "\t.clock = mt6797_dvfsp_clock_backend_read,\n"
        "\t.checkpoint = gemini_protected_readback_ledger_checkpoint,\n"
        "\t.bigidvfs = mt6797_bigidvfs_backend_read,\n"
        "};\n\n"
    )
    init = (
        "void\n"
        "mt6797_a72_source_context_init(struct mt6797_a72_physical_source_context *context,\n"
        "\t\t\t       struct device *platform, struct device *clock,\n"
        "\t\t\t       struct device *bigidvfs)\n"
        "{\n"
        "\tmemset(context, 0, sizeof(*context));\n"
        "\tcontext->platform = platform;\n"
        "\tcontext->clock = clock;\n"
        "\tcontext->bigidvfs = bigidvfs;\n"
        "\tcontext->readers = &mt6797_a72_physical_source_readers;\n"
        "}\n\n"
    )
    replace_once(path, readers, readers + init)
    source_ops = (
        "static const struct mt6797_a72_direct_source_ops\n"
        "mt6797_a72_physical_source_ops = {\n"
        "\t.snapshot = mt6797_a72_physical_source_capture,\n"
        "};\n\n"
    )
    lifecycle = (
        "int\n"
        "mt6797_a72_source_register(struct mt6797_a72_physical_source_context *context)\n"
        "{\n"
        "\tconst struct mt6797_a72_direct_source_ops *ops =\n"
        "\t\t&mt6797_a72_physical_source_ops;\n\n"
        "\treturn mt6797_a72_direct_source_register(ops, context);\n"
        "}\n\n"
        "void\n"
        "mt6797_a72_source_unregister(struct mt6797_a72_physical_source_context *context)\n"
        "{\n"
        "\tconst struct mt6797_a72_direct_source_ops *ops =\n"
        "\t\t&mt6797_a72_physical_source_ops;\n\n"
        "\tmt6797_a72_direct_source_unregister(ops, context);\n"
        "}\n\n"
    )
    replace_once(path, source_ops, source_ops + lifecycle)


def apply_production_kconfig(path: Path) -> None:
    anchor = "config MTK_MT6797_A72_PHYSICAL_SOURCE_KUNIT_TEST\n"
    addition = (
        "config MTK_MT6797_A72_ADMISSION_CONTROLLER\n"
        "\tbool \"MediaTek MT6797 one-shot CPU8 admission controller\"\n"
        "\tdepends on ARM64 && ARCH_MEDIATEK && OF && HOTPLUG_CPU\n"
        "\tdepends on ARM64_MT6797_A72_DERIVED_ADMISSION\n"
        "\tdepends on MTK_MT6797_A72_DEFAULT_OFF_BINDER\n"
        "\tdepends on MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER\n"
        "\tdefault n\n"
        "\thelp\n"
        "\t  Build the candidate-only controller that consumes one boot-local\n"
        "\t  attempt before owner mutation, derives the CPU8 transaction from\n"
        "\t  the registered physical source, publishes P17/P18, and makes one\n"
        "\t  synchronous add_cpu(8) request from the same task.\n\n"
        "\t  Supplier absence and READY-token refusal happen before consumption.\n"
        "\t  Every later result is terminal and cannot cause driver-core retry.\n"
        "\t  The base Gemini Device Tree has no controller or binder node.\n"
        "\t  If unsure, say N.\n\n"
    )
    replace_once(path, anchor, addition + anchor)


def apply_test_kconfig(path: Path) -> None:
    anchor = "config MTK_MT6797_PROTECTED_READBACK_OBSERVER\n"
    addition = (
        "config MTK_MT6797_A72_ADMISSION_CONTROLLER_KUNIT_TEST\n"
        "\tbool \"KUnit tests for MT6797 one-shot CPU8 admission controller\"\n"
        "\tdepends on KUNIT=y\n"
        "\tdepends on MTK_MT6797_A72_ADMISSION_CONTROLLER\n"
        "\tdefault n\n"
        "\thelp\n"
        "\t  Exercise exact same-task order, pre-consumption deferral, every\n"
        "\t  terminal failure, one request, and repeat closure through injected\n"
        "\t  operations only. No physical source, CPU, watchdog, retained-RAM,\n"
        "\t  regulator, secure call, CPU_OFF, or device action is performed.\n\n"
    )
    replace_once(path, anchor, addition + anchor)


def apply_production_makefile(path: Path) -> None:
    anchor = (
        "obj-$(CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER) += "
        "mt6797-a72-physical-source-observer.o\n"
    )
    addition = (
        "obj-$(CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER) += "
        "mt6797-a72-admission-controller.o\n"
    )
    replace_once(path, anchor, anchor + addition)


def apply_test_makefile(path: Path) -> None:
    anchor = (
        "obj-$(CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_KUNIT_TEST) += "
        "mt6797-a72-physical-source-observer-test.o\n"
    )
    addition = (
        "obj-$(CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER_KUNIT_TEST) += "
        "mt6797-a72-admission-controller-test.o\n"
    )
    replace_once(path, anchor, anchor + addition)


def copy_exact(source: Path, target: Path) -> None:
    if not source.is_file() or source.is_symlink():
        raise SystemExit(f"template is unavailable: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("production", "tests"), required=True)
    parser.add_argument("--template-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    templates = args.template_root.resolve()
    if args.stage == "production":
        validate_parent(root)
        apply_binder_header(
            root / "include/linux/soc/mediatek/mt6797-a72-binder.h"
        )
        apply_binder_source(root / "drivers/soc/mediatek/mt6797-a72-binder.c")
        apply_source_header(
            root / "drivers/soc/mediatek/mt6797-a72-physical-source-observer-internal.h"
        )
        apply_source_body(
            root / "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
        )
        apply_production_kconfig(root / "drivers/soc/mediatek/Kconfig")
        apply_production_makefile(root / "drivers/soc/mediatek/Makefile")
        copy_exact(
            templates / "mt6797-a72-admission-controller.c",
            root / "drivers/soc/mediatek/mt6797-a72-admission-controller.c",
        )
        copy_exact(
            templates / "mt6797-a72-admission-controller-internal.h",
            root / "drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h",
        )
    else:
        apply_test_kconfig(root / "drivers/soc/mediatek/Kconfig")
        apply_test_makefile(root / "drivers/soc/mediatek/Makefile")
        copy_exact(
            templates / "mt6797-a72-admission-controller-test.c",
            root / "drivers/soc/mediatek/mt6797-a72-admission-controller-test.c",
        )


if __name__ == "__main__":
    main()
