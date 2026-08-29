#!/usr/bin/env python3
"""Deterministic source edits for the slice-5 architecture commit."""

from __future__ import annotations

import hashlib
from pathlib import Path


PARENT_HASHES = {
    "arch/arm64/include/asm/late_cpu_profile.h":
        "4b1303e364b154268a84769fdfb0d123a44f39407c3537055488b8ae028338ea",
    "arch/arm64/kernel/cpufeature.c":
        "835ce9c8bd92ed4f4163d440a051ba859a08c89bc9f82a402fb64ba4293cb47c",
    "arch/arm64/kernel/late_cpu_profile.c":
        "e6b9ff95c03afc4ad5386e45950e6a1fbcc5b72ef937ece3a6022773f814a760",
    "arch/arm64/kernel/proton-pack.c":
        "638fddfbfebb15f02f8b338c6d4b876d5def8066044953218393e2480fbb6f30",
    "arch/arm64/kernel/mt6797_psci.c":
        "6c2b140c5c4e62d65c56a644946c6468be91aba4a6fc86852648a8aab408be4a",
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


HEADER_DECLARATIONS = """\
void __init arm64_commit_late_cpu_profile(void);
int __init arm64_commit_late_cpu_plan(const struct arm64_late_cpu_plan *plan);
int __init arm64_commit_late_cpu_mitigations(const struct arm64_late_cpu_effect_plan *effects);
"""


CAPABILITY_COMMIT = r'''

static bool __init late_cpu_commit_cap_allowed(unsigned int cap)
{
	switch (cap) {
	case ARM64_MISMATCHED_CACHE_TYPE:
	case ARM64_SPECTRE_V2:
	case ARM64_SPECTRE_V4:
	case ARM64_SPECTRE_BHB:
	case ARM64_WORKAROUND_1742098:
	case ARM64_WORKAROUND_SPECULATIVE_AT:
		return true;
	default:
		return false;
	}
}

int __init arm64_commit_late_cpu_plan(const struct arm64_late_cpu_plan *plan)
{
	DECLARE_BITMAP(expected_caps, ARM64_NCAPS);
	const struct arm64_cpu_capabilities *descriptor;
	unsigned int cap;
	int ret;

	if (!plan || system_capabilities_finalized() ||
	    cpus_have_cap(ARM64_ALWAYS_SYSTEM) ||
	    plan->abi != ARM64_LATE_CPU_PLAN_ABI ||
	    plan->evidence.blocker_mask || !plan->local_caps_planned ||
	    !plan->effects_planned || !plan->hwcaps_planned ||
	    !memchr_inv(plan->identity, 0, sizeof(plan->identity)) ||
	    !bitmap_empty(plan->conflicting_local_caps, ARM64_NCAPS) ||
	    !bitmap_subset(plan->required_local_caps,
			   plan->target_local_caps, ARM64_NCAPS) ||
	    !bitmap_subset(plan->required_local_caps,
			   plan->canonical_caps, ARM64_NCAPS) ||
	    bitmap_intersects(plan->required_local_caps,
			      plan->early_local_caps, ARM64_NCAPS) ||
	    bitmap_intersects(plan->required_local_caps,
			      system_cpucaps, ARM64_NCAPS))
		return -EINVAL;

	for_each_set_bit(cap, plan->required_local_caps, ARM64_NCAPS) {
		descriptor = cpucap_ptrs[cap];
		if (!late_cpu_commit_cap_allowed(cap) || !descriptor ||
		    descriptor->capability != cap ||
		    !(descriptor->type & SCOPE_LOCAL_CPU) ||
		    cpucap_late_cpu_permitted(descriptor))
			return -EINVAL;
	}

	bitmap_copy(expected_caps, system_cpucaps, ARM64_NCAPS);
	bitmap_or(expected_caps, expected_caps, plan->required_local_caps,
		  ARM64_NCAPS);
	ret = arm64_commit_late_cpu_mitigations(&plan->effects);
	if (ret)
		return ret;

	/* No fallible operation may follow the first architecture-state write. */
	bitmap_or(system_cpucaps, system_cpucaps, plan->required_local_caps,
		  ARM64_NCAPS);
	if (!bitmap_equal(system_cpucaps, expected_caps, ARM64_NCAPS))
		panic("late CPU capability commit changed outside its plan");

	return 0;
}
'''


MITIGATION_COMMIT = r'''

static int __init
late_cpu_mitigation_state(u8 planned, enum mitigation_state *state)
{
	switch (planned) {
	case ARM64_LATE_CPU_MITIGATION_UNAFFECTED:
		*state = SPECTRE_UNAFFECTED;
		return 0;
	case ARM64_LATE_CPU_MITIGATION_MITIGATED:
		*state = SPECTRE_MITIGATED;
		return 0;
	case ARM64_LATE_CPU_MITIGATION_VULNERABLE:
		*state = SPECTRE_VULNERABLE;
		return 0;
	default:
		return -EINVAL;
	}
}

int __init arm64_commit_late_cpu_mitigations(const struct arm64_late_cpu_effect_plan *effects)
{
	enum mitigation_state v2 = SPECTRE_UNAFFECTED;
	enum mitigation_state v4 = SPECTRE_UNAFFECTED;
	enum mitigation_state bhb = SPECTRE_UNAFFECTED;
	unsigned long current_bhb_methods;
	u8 current_bhb_loop;
	int ret;

	if (!effects || system_capabilities_finalized())
		return -EINVAL;
	if (effects->spectre_v2.required) {
		ret = late_cpu_mitigation_state(effects->spectre_v2.mitigation_state, &v2);
		if (ret || READ_ONCE(spectre_v2_state) > v2)
			return -EINVAL;
	}
	if (effects->spectre_v4.required) {
		ret = late_cpu_mitigation_state(effects->spectre_v4.mitigation_state, &v4);
		if (ret || READ_ONCE(spectre_v4_state) > v4)
			return -EINVAL;
	}
	if (effects->bhb.required) {
		ret = late_cpu_mitigation_state(effects->bhb.mitigation_state, &bhb);
		current_bhb_methods = READ_ONCE(system_bhb_mitigations);
		current_bhb_loop = READ_ONCE(max_bhb_k);
		if (ret || READ_ONCE(spectre_bhb_state) > bhb ||
		    effects->bhb.system_method & ~GENMASK(BHB_INSN, BHB_LOOP) ||
		    current_bhb_methods & ~effects->bhb.system_method ||
		    current_bhb_loop > effects->bhb.matcher_loop_count)
			return -EINVAL;
	}

	if (effects->spectre_v2.required)
		update_mitigation_state(&spectre_v2_state, v2);
	if (effects->spectre_v4.required)
		update_mitigation_state(&spectre_v4_state, v4);
	if (effects->bhb.required) {
		WRITE_ONCE(max_bhb_k, effects->bhb.matcher_loop_count);
		WRITE_ONCE(system_bhb_mitigations,
			   (unsigned long)effects->bhb.system_method);
		update_mitigation_state(&spectre_bhb_state, bhb);
	}

	return 0;
}
'''


PROFILE_COMMIT = r'''void __init arm64_commit_late_cpu_profile(void)
{
	u32 state = READ_ONCE(late_receipt.state);
	int ret;

	if (state == ARM64_LATE_CPU_PROFILE_NONE ||
	    state == ARM64_LATE_CPU_PROFILE_BLOCKED)
		return;
	if (!late_profile_active)
		return;
	if (state != ARM64_LATE_CPU_PROFILE_PLAN_FROZEN ||
	    !late_plan.local_caps_planned || !late_plan.effects_planned ||
	    !late_plan.hwcaps_planned ||
	    !late_profile_plan_has_identity(&late_plan) ||
	    memcmp(late_receipt.plan_identity, late_plan.identity,
		   sizeof(late_receipt.plan_identity)) ||
	    late_receipt.blocker_mask || late_receipt.commit_complete ||
	    late_receipt.strict_caps_verified ||
	    late_receipt.alternatives_finalized ||
	    late_receipt.user_hwcaps_finalized ||
	    memchr_inv(&late_receipt.committed, 0,
		       sizeof(late_receipt.committed)))
		panic("late CPU profile reached capability commit out of order");

	ret = arm64_commit_late_cpu_plan(&late_plan);
	if (ret)
		panic("late CPU architecture commit failed: %d", ret);
	late_receipt.committed = late_plan.effects;
	late_receipt.commit_complete = 1;
	/* Publish the complete receipt after all architecture state is committed. */
	smp_store_release(&late_receipt.state,
			  ARM64_LATE_CPU_PROFILE_COMMITTED);
	pr_info("%s committed its immutable capability plan\n",
		late_receipt.profile_id);
}'''


OLD_PROFILE_COMMIT = r'''void __init arm64_commit_late_cpu_profile(void)
{
	u32 state = READ_ONCE(late_receipt.state);

	if (state == ARM64_LATE_CPU_PROFILE_NONE ||
	    state == ARM64_LATE_CPU_PROFILE_BLOCKED)
		return;
	if (!late_profile_active)
		return;
	if (state != ARM64_LATE_CPU_PROFILE_PLAN_FROZEN ||
	    !late_plan.local_caps_planned || !late_plan.effects_planned ||
	    !late_plan.hwcaps_planned ||
	    !late_profile_plan_has_identity(&late_plan) ||
	    memcmp(late_receipt.plan_identity, late_plan.identity,
		   sizeof(late_receipt.plan_identity)))
		panic("late CPU profile reached capability commit out of order");

	/*
	 * ABI 7 deliberately publishes no mutation path. The complete canonical
	 * evaluator must add one architecture-owned, callback-free commit before
	 * it can make PLAN_FROZEN reachable for a production profile.
	 */
	panic("late CPU profile commit implementation is unavailable");
}'''


def apply(root: Path) -> None:
    validate_parent(root)
    header = root / "arch/arm64/include/asm/late_cpu_profile.h"
    cpufeature = root / "arch/arm64/kernel/cpufeature.c"
    core = root / "arch/arm64/kernel/late_cpu_profile.c"
    proton = root / "arch/arm64/kernel/proton-pack.c"

    replace_once(
        header,
        "void __init arm64_commit_late_cpu_profile(void);\n",
        HEADER_DECLARATIONS,
    )
    replace_once(
        cpufeature,
        "\tplan->hwcaps_planned = 1;\n"
        "\treturn 0;\n"
        "}\n"
        "#endif\n\n"
        "static void cap_set_elf_hwcap",
        "\tplan->hwcaps_planned = 1;\n"
        "\treturn 0;\n"
        "}\n" + CAPABILITY_COMMIT +
        "#endif\n\n"
        "static void cap_set_elf_hwcap",
    )
    replace_once(
        proton,
        "\tsystem->valid |= ARM64_LATE_CPU_SYSTEM_CAP_EFFECTS_VALID;\n\n"
        "\treturn 0;\n"
        "}\n"
        "#endif\n\n"
        "static void this_cpu_set_vectors",
        "\tsystem->valid |= ARM64_LATE_CPU_SYSTEM_CAP_EFFECTS_VALID;\n\n"
        "\treturn 0;\n"
        "}\n" + MITIGATION_COMMIT +
        "#endif\n\n"
        "static void this_cpu_set_vectors",
    )
    replace_once(
        core,
        "\t/* ABI 7 has no architecture-owned mutation implementation. */\n"
        "\tdraft.evidence.blocker_mask |= ARM64_LATE_CPU_BLOCK_COMMIT_PATH;\n",
        "",
    )
    replace_once(core, OLD_PROFILE_COMMIT, PROFILE_COMMIT)


if __name__ == "__main__":
    raise SystemExit("commit_edits.py is imported by the generator")
