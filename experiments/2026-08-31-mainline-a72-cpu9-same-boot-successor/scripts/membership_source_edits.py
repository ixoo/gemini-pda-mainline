#!/usr/bin/env python3
"""Apply the owner-local Gemini CPU9 membership source edit."""

from __future__ import annotations

import hashlib
from pathlib import Path
from textwrap import dedent


SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES = SCRIPT_DIR.parent / "templates"
PARENT_HASHES = {
    "arch/arm64/Kconfig.platforms":
        "6f9f321eecc380c80823fd74e93f4c49ea1cc56c584df0a6acad6a46ba575918",
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "99894841f380bb036c74149eff17df61786e1291daba36c50981fc87b768cf9f",
    "arch/arm64/kernel/mt6797_a72_membership.c":
        "c83e1712cf7f847dfc9c9f61e1eb8206cd33b0387139cec75a8286756338ffbb",
    "arch/arm64/kernel/mt6797_a72_membership_test.c":
        "85f803963f782efe011dd136c0286c70384ee96aedda5f588fae0a3b080f6298",
}
CHANGED_PATHS = tuple(PARENT_HASHES)

KCONFIG = dedent("""\
    config ARM64_MT6797_A72_CPU9_MEMBERSHIP
    \tbool "Derive retained-cluster MT6797 CPU9 membership"
    \tdepends on HOTPLUG_CPU
    \tdepends on ARM64_MT6797_A72_DERIVED_ADMISSION
    \tdepends on MTK_MT6797_A72_DEFAULT_OFF_BINDER
    \tdefault n
    \thelp
    \t  Add a CPU9-specific owner path after an exact retired CPU8 success.
    \t  It requires CPU8 online, CPU9 offline, member bit 0, the original
    \t  provider identity still held, and a fresh CPU9 attempt. The CPU9
    \t  transaction receives only one CPU_ON budget.

    \t  This option adds no caller, CPU request, CPU_OFF, watchdog action,
    \t  provider transaction, cluster-power operation, retry, or boot policy.
    \t  If unsure, say N.

    """)

CPU9_DERIVE_ENUM = dedent("""\
    enum mt6797_a72_cpu9_derive_stage {
    \tMT6797_A72_CPU9_DERIVE_NONE,
    \tMT6797_A72_CPU9_DERIVE_TOPOLOGY,
    \tMT6797_A72_CPU9_DERIVE_READY_TOKEN,
    \tMT6797_A72_CPU9_DERIVE_CPU8_TERMINAL,
    \tMT6797_A72_CPU9_DERIVE_ENTRY_VALIDATE,
    \tMT6797_A72_CPU9_DERIVE_P31_CONSUME,
    \tMT6797_A72_CPU9_DERIVE_TOKEN_MINT,
    \tMT6797_A72_CPU9_DERIVE_PRESTATE_VALIDATE,
    \tMT6797_A72_CPU9_DERIVE_PRESTATE_BIND,
    \tMT6797_A72_CPU9_DERIVE_COMPLETE,
    };

    """)

CPU9_DERIVE_API = dedent("""\
    #if IS_ENABLED(CONFIG_ARM64_MT6797_A72_CPU9_MEMBERSHIP)
    int
    mt6797_a72_membership_derive_cpu9(const struct arm64_late_cpu_ready_token *ready,
    \t\t\t\t  struct mt6797_a72_transaction *transaction);
    int
    mt6797_a72_membership_derive_cpu9_diagnostic(const struct arm64_late_cpu_ready_token *ready,
    \t\t\t\t\t      struct mt6797_a72_transaction *transaction,
    \t\t\t\t\t      u32 *derive_stage);
    #endif

    """)

CPU9_LIFECYCLE_API = dedent("""\
    #if IS_ENABLED(CONFIG_ARM64_MT6797_A72_CPU9_MEMBERSHIP)
    int mt6797_a72_membership_publish_cpu9(struct mt6797_a72_transaction *transaction);
    int mt6797_a72_membership_preflight_cpu9(void);
    int mt6797_a72_membership_claim_cpu9(struct mt6797_a72_transaction *transaction);
    int mt6797_a72_membership_reject_cpu9(struct mt6797_a72_transaction *transaction);
    int mt6797_a72_membership_begin_cpu9_on(struct mt6797_a72_transaction *transaction);
    int mt6797_a72_membership_publish_cpu9_success(struct mt6797_a72_transaction *transaction);
    int mt6797_a72_membership_finalize_cpu9_success(struct mt6797_a72_transaction *transaction);
    #endif
    """)

CPU9_TEST_API = dedent("""\
    #if IS_ENABLED(CONFIG_ARM64_MT6797_A72_CPU9_MEMBERSHIP)
    int
    mt6797_a72_membership_test_derive_cpu9(const struct mt6797_a72_direct_topology *topology,
    \t\t\t\t       const struct arm64_late_cpu_ready_token *ready,
    \t\t\t\t       struct mt6797_a72_transaction *transaction);
    int
    mt6797_a72_membership_test_validate_cpu9_parent(const struct mt6797_a72_owner_snapshot *parent,
    \t\t\t\t\t\t const struct mt6797_a72_direct_topology *topology);
    int mt6797_a72_membership_test_preflight_cpu9(bool cpu8_online,
    \t\t\t\t\t      bool cpu9_online);
    int
    mt6797_a72_membership_test_claim_cpu9(struct mt6797_a72_transaction *transaction,
    \t\t\t\t      bool cpu8_online, bool cpu9_online);
    int
    mt6797_a72_membership_test_reject_cpu9(struct mt6797_a72_transaction *transaction,
    \t\t\t\t       bool cpu8_online, bool cpu9_online);
    int
    mt6797_a72_membership_test_begin_cpu9_on(struct mt6797_a72_transaction *transaction,
    \t\t\t\t\t bool cpu8_online, bool cpu9_online);
    int
    mt6797_a72_membership_test_publish_cpu9_success(struct mt6797_a72_transaction *transaction,
    \t\t\t\t\t\t bool cpu8_online, bool cpu9_online);
    int
    mt6797_a72_membership_test_finalize_cpu9_success(struct mt6797_a72_transaction *transaction,
    \t\t\t\t\t\t  bool cpu8_online, bool cpu9_online);
    #endif
    """)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def template(name: str) -> str:
    path = TEMPLATES / name
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"template is absent or unsafe: {path}")
    return path.read_text(encoding="utf-8")


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"parent source is absent or unsafe: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(f"parent source changed: {relative}: {actual}")


def apply(root: Path) -> None:
    root = root.resolve()
    validate_parent(root)
    kconfig = root / "arch/arm64/Kconfig.platforms"
    header = root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    source = root / "arch/arm64/kernel/mt6797_a72_membership.c"
    tests = root / "arch/arm64/kernel/mt6797_a72_membership_test.c"

    replace_once(
        kconfig,
        "config ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR\n",
        KCONFIG + "config ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR\n",
    )
    replace_once(header, "#define MT6797_A72_TRANSACTION_ABI 3\n",
                 "#define MT6797_A72_TRANSACTION_ABI 4\n")
    replace_once(
        header,
        "enum mt6797_a72_provider_state {\n",
        CPU9_DERIVE_ENUM + "enum mt6797_a72_provider_state {\n",
    )
    replace_once(
        header,
        "\tu32 cpu8_success_published;\n\tu32 p29_valid;\n",
        "\tu32 cpu8_success_published;\n"
        "\tu32 cpu9_success_published;\n"
        "\tu32 p29_valid;\n",
    )
    replace_once(
        header,
        "#ifdef CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION_KUNIT_TEST\n"
        "int\n"
        "mt6797_a72_membership_test_derive_cpu8("
        "const struct mt6797_a72_direct_topology *topology,\n"
        "\t\t\t\t       const struct arm64_late_cpu_ready_token *ready,\n"
        "\t\t\t\t       struct mt6797_a72_transaction *transaction);\n"
        "#endif\n"
        "int\nmt6797_a72_membership_validate_up_prestate(",
        "#ifdef CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION_KUNIT_TEST\n"
        "int\n"
        "mt6797_a72_membership_test_derive_cpu8("
        "const struct mt6797_a72_direct_topology *topology,\n"
        "\t\t\t\t       const struct arm64_late_cpu_ready_token *ready,\n"
        "\t\t\t\t       struct mt6797_a72_transaction *transaction);\n"
        "#endif\n"
        + CPU9_DERIVE_API
        + "int\nmt6797_a72_membership_validate_up_prestate(",
    )
    replace_once(
        header,
        "int mt6797_a72_membership_finalize_cpu8_success("
        "struct mt6797_a72_transaction *transaction);\n",
        "int mt6797_a72_membership_finalize_cpu8_success("
        "struct mt6797_a72_transaction *transaction);\n"
        + CPU9_LIFECYCLE_API,
    )
    replace_once(
        header,
        "int mt6797_a72_membership_test_finalize_cpu8_success("
        "struct mt6797_a72_transaction *transaction,\n"
        "\t\t\t\t\t\t     bool cpu8_online, bool cpu9_online);\n",
        "int mt6797_a72_membership_test_finalize_cpu8_success("
        "struct mt6797_a72_transaction *transaction,\n"
        "\t\t\t\t\t\t     bool cpu8_online, bool cpu9_online);\n"
        + CPU9_TEST_API,
    )

    derive = template("mt6797_a72_cpu9_membership_derive.c.inc")
    replace_once(
        source,
        "#endif\n\n#endif\n\nint\nmt6797_a72_membership_begin_up(",
        "#endif\n\n" + derive + "\n#endif\n\nint\n"
        "mt6797_a72_membership_begin_up(",
    )
    lifecycle = template("mt6797_a72_cpu9_membership_lifecycle.c.inc")
    replace_once(
        source,
        "int mt6797_a72_membership_validate_entry(unsigned int cpu,\n",
        lifecycle + "\nint mt6797_a72_membership_validate_entry(unsigned int cpu,\n",
    )

    test_block = template("mt6797_a72_cpu9_membership_test.c.inc")
    replace_once(
        tests,
        "static void mt6797_a72_owner_forged_token_rejected(struct kunit *test)\n",
        test_block + "\nstatic void "
        "mt6797_a72_owner_forged_token_rejected(struct kunit *test)\n",
    )
    replace_once(
        tests,
        "\tKUNIT_CASE(mt6797_a72_owner_forged_token_rejected),\n",
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_CPU9_MEMBERSHIP)\n"
        "\tKUNIT_CASE(mt6797_a72_owner_cpu9_parent_gate),\n"
        "\tKUNIT_CASE(mt6797_a72_owner_cpu9_parent_mutations),\n"
        "\tKUNIT_CASE(mt6797_a72_owner_cpu9_success_lifecycle),\n"
        "\tKUNIT_CASE(mt6797_a72_owner_cpu9_rejection_one_shot),\n"
        "#endif\n"
        "\tKUNIT_CASE(mt6797_a72_owner_forged_token_rejected),\n",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    apply(args.source_root)
