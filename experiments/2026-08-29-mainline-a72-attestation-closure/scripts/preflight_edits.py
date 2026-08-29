#!/usr/bin/env python3
"""Deterministic source edits for slice 7's late-target preflight."""

from __future__ import annotations

import hashlib
from pathlib import Path


PARENT_HASHES = {
    "arch/arm64/include/asm/late_cpu_profile.h":
        "2c803eb808c7232e329f7f9648915aab8cf2a3729b2a36ab515a81cf6915bf02",
    "arch/arm64/include/asm/mmu_context.h":
        "af1ef82962e0221f36aa4330dfc22b2bebdf62dc2db24986a02b023e6de91952",
    "arch/arm64/kernel/cpufeature.c":
        "12ee7c76dd34c7c016e33c19a11837c4163585e685e5d8d6fa4ec675c3ec0bbe",
    "arch/arm64/kernel/head.S":
        "17dac1b2a499bb21f8a0e160aff9fd9fd24343c0f6d0dc12a4f4cbafb99d0749",
    "arch/arm64/kernel/late_cpu_profile.c":
        "157775edf50fc8cad6aa43e37834dfd0917f6abf58bd60e6ebbed28751663444",
    "arch/arm64/kernel/mt6797_psci.c":
        "ff8e4ce803d0ad4a5fc35989a3d38169a3e7260bd737e861317b22f1ca8f5471",
    "arch/arm64/kernel/smp.c":
        "b0c25f67b5f7957edd2fc04a566789b4cf4fb745704bd6464f1c157c926ded67",
    "arch/arm64/mm/context.c":
        "123d80b2ad9c37b6e9b58296c217744747c87f483cfbc424a1f4695a64cb9728",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"edit anchor count changed for {path}: {old[:80]!r}")
    path.write_text(text.replace(old, new, 1))


def validate_parent(root: Path) -> None:
    for relative, expected in PARENT_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"parent source absent or unsafe: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(
                f"parent source changed: {relative}: {actual} != {expected}")


BOOT_CAP_PREFLIGHT = r'''int arm64_late_cpu_validate_boot_caps(void)
{
	const struct arm64_cpu_capabilities *caps;
	bool cpu_has_cap;
	bool system_has_cap;
	int i;

	for (i = 0; i < ARM64_NCAPS; i++) {
		caps = cpucap_ptrs[i];
		if (!caps || !(caps->type & SCOPE_BOOT_CPU))
			continue;

		/* Match callbacks perform the same CPU-local discovery as verify. */
		cpu_has_cap = caps->matches(caps, SCOPE_LOCAL_CPU);
		system_has_cap = cpus_have_cap(caps->capability);
		if (system_has_cap) {
			if (!cpu_has_cap && !cpucap_late_cpu_optional(caps))
				return -ERANGE;
		} else if (cpu_has_cap && !cpucap_late_cpu_permitted(caps)) {
			return -ERANGE;
		}
	}

	return 0;
}

'''


PREFLIGHT_FACADE = r'''int arm64_validate_late_cpu_preflight(unsigned int cpu)
{
	/* Pairs with READY publication of late_plan and late_receipt. */
	if (smp_load_acquire(&late_receipt.state) !=
	    ARM64_LATE_CPU_PROFILE_READY)
		return 0;
	if (!cpumask_test_cpu(cpu, &late_plan.target_cpus))
		return 0;
	if (cpu != smp_processor_id() ||
	    !arm64_late_cpu_expected_pair_complete(&late_plan))
		return -EINVAL;
	if (!arm64_late_cpu_asid_compatible())
		return -ERANGE;

	return arm64_late_cpu_validate_boot_caps();
}

'''


SMP_PREFLIGHT = r'''	expectation_ret = arm64_validate_late_cpu_preflight(cpu);
	if (expectation_ret) {
		pr_crit("CPU%u: late target preflight mismatch: %d\n",
			cpu, expectation_ret);
		update_cpu_boot_status(CPU_STUCK_IN_KERNEL);
		cpu_park_loop();
	}

'''


def apply(root: Path) -> None:
    validate_parent(root)
    late_header = root / "arch/arm64/include/asm/late_cpu_profile.h"
    mmu_header = root / "arch/arm64/include/asm/mmu_context.h"
    cpufeature = root / "arch/arm64/kernel/cpufeature.c"
    core = root / "arch/arm64/kernel/late_cpu_profile.c"
    smp = root / "arch/arm64/kernel/smp.c"
    context = root / "arch/arm64/mm/context.c"

    replace_once(
        late_header,
        "bool arm64_late_cpu_expected_pair_complete("
        "const struct arm64_late_cpu_plan *plan);\n"
        "int arm64_validate_late_cpu_expected_target(unsigned int cpu);\n",
        "bool arm64_late_cpu_expected_pair_complete("
        "const struct arm64_late_cpu_plan *plan);\n"
        "int arm64_late_cpu_validate_boot_caps(void);\n"
        "int arm64_validate_late_cpu_preflight(unsigned int cpu);\n"
        "int arm64_validate_late_cpu_expected_target(unsigned int cpu);\n",
    )
    replace_once(
        mmu_header,
        "void verify_cpu_asid_bits(void);\n",
        "bool arm64_late_cpu_asid_compatible(void);\n"
        "void verify_cpu_asid_bits(void);\n",
    )
    replace_once(
        context,
        "/* Check if the current cpu's ASIDBits is compatible with asid_bits */\n"
        "void verify_cpu_asid_bits(void)\n",
        "bool arm64_late_cpu_asid_compatible(void)\n"
        "{\n"
        "\tu32 system_asid_bits = READ_ONCE(asid_bits);\n\n"
        "\treturn system_asid_bits &&\n"
        "\t       get_cpu_asid_bits() >= system_asid_bits;\n"
        "}\n\n"
        "/* Check if the current cpu's ASIDBits is compatible with asid_bits */\n"
        "void verify_cpu_asid_bits(void)\n",
    )
    replace_once(
        cpufeature,
        "/*\n * Run through the list of capabilities to check for conflicts.\n",
        BOOT_CAP_PREFLIGHT +
        "/*\n * Run through the list of capabilities to check for conflicts.\n",
    )
    replace_once(
        core,
        "#include <asm/late_cpu_profile.h>\n#include <asm/sysreg.h>\n",
        "#include <asm/late_cpu_profile.h>\n"
        "#include <asm/mmu_context.h>\n"
        "#include <asm/sysreg.h>\n",
    )
    replace_once(
        core,
        "static bool\nlate_expected_target_matches(",
        PREFLIGHT_FACADE + "static bool\nlate_expected_target_matches(",
    )
    replace_once(
        smp,
        "\t/*\n"
        "\t * If the system has established the capabilities, make sure\n",
        SMP_PREFLIGHT +
        "\t/*\n"
        "\t * If the system has established the capabilities, make sure\n",
    )


if __name__ == "__main__":
    raise SystemExit("preflight_edits.py is imported by the generator")
