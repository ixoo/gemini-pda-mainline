#!/usr/bin/env python3
"""Apply deterministic pure A34 eligibility-evaluator source changes."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one edit anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def write_new(path: Path, source: Path) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def apply(root: Path, experiment: Path) -> None:
    arm_kconfig = root / "arch/arm64/Kconfig"
    platform_kconfig = root / "arch/arm64/Kconfig.platforms"
    makefile = root / "arch/arm64/kernel/Makefile"
    header = root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    owner = root / "arch/arm64/kernel/mt6797_a72_membership.c"

    replace_once(
        platform_kconfig,
        "config ARM64_MT6797_A72_P24_ADMISSION_HOOKS\n",
        dedent("""\
        config ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR
        \tbool "Evaluate the exact MT6797 A72 A34 zero-state tuple"
        \tdepends on ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL
        \thelp
        \t  Add a pure, default-off evaluator for the frozen A34 tuple. Its
        \t  immutable input must carry explicit platform/external-reset
        \t  provenance and owner-safe private replay-zero proof.

        \t  This option has no production caller and cannot open the owner,
        \t  initialize an attempt, call a provider, perform a hardware effect,
        \t  arm P30, or issue CPU_ON or CPU_OFF.

        config ARM64_MT6797_A72_P24_ADMISSION_HOOKS
        """),
    )
    replace_once(
        arm_kconfig,
        "config ARM64_MT6797_A72_PROVIDER_OWNER\n",
        dedent("""\
        config ARM64_MT6797_A72_A34_ELIGIBILITY_KUNIT_TEST
        \tbool "KUnit tests for the MT6797 A72 A34 eligibility evaluator"
        \tdepends on KUNIT=y
        \tdepends on HOTPLUG_CPU
        \tdepends on ARM64_MT6797_A72_P30_PROTOCOL_MODEL
        \tselect ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL
        \tselect ARM64_MT6797_A72_P24_ADMISSION_HOOKS
        \tselect ARM64_MT6797_A72_P24_OWNER_TEST_SEED
        \tselect ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR
        \thelp
        \t  Exercise both accepted reset-provenance values, null input, every
        \t  byte mutation, explicit missing provenance, and unchanged CLOSED
        \t  admission without hardware or CPU operations. The suite has no
        \t  production hook.

        config ARM64_MT6797_A72_PROVIDER_OWNER
        """),
    )
    replace_once(
        makefile,
        "obj-$(CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST) += mt6797_a72_membership_test.o\n",
        "obj-$(CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST) += mt6797_a72_membership_test.o\n"
        "obj-$(CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_KUNIT_TEST) += mt6797_a72_a34_evaluator_test.o\n",
    )

    replace_once(
        owner,
        "#include <linux/string.h>\n",
        "#include <linux/stddef.h>\n#include <linux/string.h>\n",
    )

    replace_once(
        header,
        " * callback seam can return a read-only refusal, but it has no bootstrap,\n"
        " * CPUHP effect, P30 handoff, P14/P15, hardware mutation, or CPU_ON operation.\n",
        " * callback seam can return a read-only refusal. A default-off A34 pure\n"
        " * evaluator has no production caller and cannot bootstrap the owner, perform\n"
        " * a CPUHP effect, hand off P30, mutate hardware, or issue CPU_ON.\n",
    )
    replace_once(
        header,
        "#define MT6797_A72_OPERATION_SLOTS 4\n",
        "#define MT6797_A72_OPERATION_SLOTS 4\n"
        "#define MT6797_A72_A34_ELIGIBILITY_ABI 1\n"
        "#define MT6797_A72_A34_FIRST_GENERATION 1ULL\n"
        "#define MT6797_A72_A34_FIRST_COOKIE 0xa7200001ULL\n",
    )
    replace_once(
        header,
        "\tu32 controller_present;\n"
        "};\n\n"
        "#ifdef CONFIG_ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL\n",
        dedent("""\
        \tu32 controller_present;
        };

        enum mt6797_a72_a34_reset_provenance {
        \tMT6797_A72_A34_RESET_UNKNOWN,
        \tMT6797_A72_A34_RESET_PLATFORM,
        \tMT6797_A72_A34_RESET_EXTERNAL,
        \tMT6797_A72_A34_RESET_ORDINARY_LINUX,
        };

        enum mt6797_a72_a34_private_replay_proof {
        \tMT6797_A72_A34_PRIVATE_REPLAY_UNKNOWN,
        \tMT6797_A72_A34_PRIVATE_REPLAY_OWNER_SAFE_ZERO,
        };

        struct mt6797_a72_a34_observation {
        \tu32 abi;
        \tu32 reset_provenance;
        \tu32 private_replay_proof;
        \tu32 private_replay_value;
        \tu32 max_cpus;
        \tu32 nr_cpus;
        \tu32 possible_count;
        \tu32 present_count;
        \tu32 online_count;
        \tu32 possible_mask;
        \tu32 present_mask;
        \tu32 online_mask;
        \tu32 cpu8_method_valid;
        \tu32 cpu9_method_valid;
        \tu32 cpuhp_state_cpu8;
        \tu32 cpuhp_state_cpu9;
        \tu64 cpu8_mpidr;
        \tu64 cpu9_mpidr;
        \tstruct mt6797_a72_owner_snapshot owner;
        \tu64 owner_next_generation;
        \tu64 owner_next_cookie;
        \tu64 first_generation;
        \tu64 first_cookie;
        \tstruct arm64_late_cpu_startup_snapshot p30;
        };

        #ifdef CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR
        int
        mt6797_a72_a34_evaluate(const struct mt6797_a72_a34_observation
        \t\t\t      *observation);
        #else
        static inline int
        mt6797_a72_a34_evaluate(const struct mt6797_a72_a34_observation
        \t\t\t      *observation)
        {
        \t(void)observation;
        \treturn -EOPNOTSUPP;
        }
        #endif

        #ifdef CONFIG_ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL
        """),
    )

    replace_once(
        owner,
        "static bool\nmt6797_a72_p32_target_locked(unsigned int cpu)\n",
        dedent("""\
        #ifdef CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR
        static const struct mt6797_a72_a34_observation a34_expected = {
        \t.abi = MT6797_A72_A34_ELIGIBILITY_ABI,
        \t.private_replay_proof =
        \t\tMT6797_A72_A34_PRIVATE_REPLAY_OWNER_SAFE_ZERO,
        \t.max_cpus = 8,
        \t.nr_cpus = 10,
        \t.possible_count = 10,
        \t.present_count = 10,
        \t.online_count = 8,
        \t.possible_mask = GENMASK(9, 0),
        \t.present_mask = GENMASK(9, 0),
        \t.online_mask = GENMASK(7, 0),
        \t.cpu8_method_valid = 1,
        \t.cpu9_method_valid = 1,
        \t.cpuhp_state_cpu8 = CPUHP_OFFLINE,
        \t.cpuhp_state_cpu9 = CPUHP_OFFLINE,
        \t.cpu8_mpidr = 0x200,
        \t.cpu9_mpidr = 0x201,
        \t.owner = {
        \t\t.diagnostic_blockers = MT6797_A72_BLOCK_MASK,
        \t\t.abi = MT6797_A72_TRANSACTION_ABI,
        \t\t.health = MT6797_A72_OWNER_CLOSED,
        \t\t.phase = MT6797_A72_PHASE_UNINITIALIZED,
        \t\t.provider_state = MT6797_A72_PROVIDER_NONE,
        \t},
        \t.first_generation = MT6797_A72_A34_FIRST_GENERATION,
        \t.first_cookie = MT6797_A72_A34_FIRST_COOKIE,
        };

        int
        mt6797_a72_a34_evaluate(const struct mt6797_a72_a34_observation
        \t\t\t      *observation)
        {
        \tsize_t tail = offsetof(struct mt6797_a72_a34_observation,
        \t\t\t       private_replay_proof);

        \tif (!observation)
        \t\treturn -EINVAL;
        \tif (observation->abi != MT6797_A72_A34_ELIGIBILITY_ABI ||
        \t    (observation->reset_provenance !=
        \t\tMT6797_A72_A34_RESET_PLATFORM &&
        \t     observation->reset_provenance !=
        \t\tMT6797_A72_A34_RESET_EXTERNAL) ||
        \t    memcmp((const u8 *)observation + tail,
        \t\t   (const u8 *)&a34_expected + tail,
        \t\t   sizeof(*observation) - tail))
        \t\treturn -EPERM;
        \treturn 0;
        }
        #endif

        static bool
        mt6797_a72_p32_target_locked(unsigned int cpu)
        """),
    )

    write_new(
        root / "arch/arm64/kernel/mt6797_a72_a34_evaluator_test.c",
        experiment / "source/mt6797-a72-a34-evaluator-test.c",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if not (root / "arch/arm64/kernel/mt6797_a72_membership.c").is_file():
        raise SystemExit("unexpected source root")
    apply(root, Path(__file__).resolve().parents[1])


if __name__ == "__main__":
    main()
