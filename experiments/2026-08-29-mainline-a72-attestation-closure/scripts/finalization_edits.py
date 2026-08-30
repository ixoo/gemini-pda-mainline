#!/usr/bin/env python3
"""Deterministic architecture-owned late-CPU finalization edits."""

from __future__ import annotations

import hashlib
from pathlib import Path


HEADER = "arch/arm64/include/asm/late_cpu_profile.h"
CPUFEATURE = "arch/arm64/kernel/cpufeature.c"
MITIGATIONS = "arch/arm64/kernel/proton-pack.c"
PROFILE = "arch/arm64/kernel/mt6797_psci.c"
PARENT_HASHES = {
    HEADER: "7daa9a6112dfcb4599447c1f218b604d1325d97078aaf911c70bbc8e4a16d4bb",
    CPUFEATURE: "487f03828918f31e9b1117084948b76148558e3ed3516f7c0aedd46a51ec8c44",
    MITIGATIONS: "4105a92e75765f4d59b4d857d03200aadce1eb43d8dcf685e3b245a2a0f5a27a",
    PROFILE: "9f2fd9e83b85f862b1f8865384d262d863ff29c3a9d980f3ce9095fe569e4a8c",
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


HEADER_ANCHOR = r'''int __init arm64_commit_late_cpu_plan(const struct arm64_late_cpu_plan *plan);
int __init arm64_commit_late_cpu_mitigations(const struct arm64_late_cpu_effect_plan *effects);
int __init arm64_plan_late_cpu_capabilities(struct arm64_late_cpu_plan *draft,
'''

HEADER_FINAL = r'''int __init arm64_commit_late_cpu_plan(const struct arm64_late_cpu_plan *plan);
int __init arm64_commit_late_cpu_mitigations(const struct arm64_late_cpu_effect_plan *effects);
int __init
arm64_verify_late_cpu_mitigations(const struct arm64_late_cpu_effect_plan *effects);
int __init
arm64_verify_late_cpu_system(const struct arm64_late_cpu_plan *plan,
			     const struct arm64_late_cpu_receipt *receipt);
int __init
arm64_finalize_late_cpu_hwcaps(const struct arm64_late_cpu_plan *plan,
			       const struct arm64_late_cpu_receipt *receipt);
int __init arm64_plan_late_cpu_capabilities(struct arm64_late_cpu_plan *draft,
'''


CPUFEATURE_ANCHOR = r'''	return 0;
}
#endif

static void cap_set_elf_hwcap(const struct arm64_cpu_capabilities *cap)
'''

CPUFEATURE_FINAL = r'''	return 0;
}

int __init
arm64_verify_late_cpu_system(const struct arm64_late_cpu_plan *plan,
			     const struct arm64_late_cpu_receipt *receipt)
{
	DECLARE_BITMAP(expected_caps, ARM64_NCAPS);
	DECLARE_BITMAP(live_caps, ARM64_NCAPS);
	unsigned int cap;

	if (!plan || !receipt || !system_capabilities_finalized() ||
	    receipt->state != ARM64_LATE_CPU_PROFILE_COMMITTED ||
	    receipt->blocker_mask || !receipt->commit_complete ||
	    receipt->strict_caps_verified || receipt->alternatives_finalized ||
	    receipt->user_hwcaps_finalized ||
	    !plan->local_caps_planned || !plan->effects_planned ||
	    !plan->hwcaps_planned ||
	    !bitmap_empty(plan->conflicting_local_caps, ARM64_NCAPS))
		return -EINVAL;

	bitmap_or(expected_caps, plan->early_local_caps,
		  plan->required_local_caps, ARM64_NCAPS);
	if (!bitmap_subset(expected_caps, plan->compiled_local_caps,
			   ARM64_NCAPS))
		return -EINVAL;
	bitmap_and(live_caps, system_cpucaps, plan->compiled_local_caps,
		   ARM64_NCAPS);
	if (!bitmap_equal(live_caps, expected_caps, ARM64_NCAPS))
		return -EINVAL;

	for_each_set_bit(cap, plan->compiled_local_caps, ARM64_NCAPS)
		if (alternative_is_applied(cap) !=
		    test_bit(cap, expected_caps))
			return -EINVAL;

	return arm64_verify_late_cpu_mitigations(&plan->effects);
}

int __init
arm64_finalize_late_cpu_hwcaps(const struct arm64_late_cpu_plan *plan,
			       const struct arm64_late_cpu_receipt *receipt)
{
	const unsigned long *expected;

	if (!plan || !receipt || !system_capabilities_finalized() ||
	    receipt->state != ARM64_LATE_CPU_PROFILE_SYSTEM_VERIFIED ||
	    receipt->blocker_mask || !receipt->commit_complete ||
	    !receipt->strict_caps_verified ||
	    !receipt->alternatives_finalized ||
	    receipt->user_hwcaps_finalized || !plan->hwcaps_planned)
		return -EINVAL;

	BUILD_BUG_ON(sizeof(plan->expected_elf_hwcap) != sizeof(elf_hwcap));
	BUILD_BUG_ON(sizeof(unsigned long) != sizeof(u64));
	expected = (const unsigned long *)plan->expected_elf_hwcap;
	if (!bitmap_subset(expected, elf_hwcap, MAX_CPU_FEATURES))
		return -EINVAL;
#ifdef CONFIG_COMPAT
	if (plan->expected_compat_hwcap & ~compat_elf_hwcap ||
	    plan->expected_compat_hwcap2 & ~compat_elf_hwcap2 ||
	    compat_elf_hwcap3)
		return -EINVAL;
#else
	if (plan->expected_compat_hwcap || plan->expected_compat_hwcap2)
		return -EINVAL;
#endif

	/* All fallible checks precede this one-way userspace-visible reduction. */
	bitmap_copy(elf_hwcap, expected, MAX_CPU_FEATURES);
#ifdef CONFIG_COMPAT
	compat_elf_hwcap = plan->expected_compat_hwcap;
	compat_elf_hwcap2 = plan->expected_compat_hwcap2;
#endif
	if (!bitmap_equal(elf_hwcap, expected, MAX_CPU_FEATURES))
		panic("late CPU HWCAP finalization changed outside its plan");
#ifdef CONFIG_COMPAT
	if (compat_elf_hwcap != plan->expected_compat_hwcap ||
	    compat_elf_hwcap2 != plan->expected_compat_hwcap2 ||
	    compat_elf_hwcap3)
		panic("late CPU compat HWCAP finalization changed outside its plan");
#endif

	return 0;
}
#endif

static void cap_set_elf_hwcap(const struct arm64_cpu_capabilities *cap)
'''


MITIGATION_ANCHOR = r'''	return 0;
}
#endif

static void this_cpu_set_vectors(enum arm64_bp_harden_el1_vectors slot)
'''

MITIGATION_FINAL = r'''	return 0;
}

int __init
arm64_verify_late_cpu_mitigations(const struct arm64_late_cpu_effect_plan *effects)
{
	enum mitigation_state v2;
	enum mitigation_state v4;
	enum mitigation_state bhb;
	int ret;

	if (!effects || !system_capabilities_finalized())
		return -EINVAL;
	if (effects->spectre_v2.required) {
		ret = late_cpu_mitigation_state(effects->spectre_v2.mitigation_state, &v2);
		if (ret || READ_ONCE(spectre_v2_state) != v2)
			return -EINVAL;
	}
	if (effects->spectre_v4.required) {
		ret = late_cpu_mitigation_state(effects->spectre_v4.mitigation_state, &v4);
		if (ret || READ_ONCE(spectre_v4_state) != v4)
			return -EINVAL;
	}
	if (effects->bhb.required) {
		ret = late_cpu_mitigation_state(effects->bhb.mitigation_state, &bhb);
		if (ret || READ_ONCE(spectre_bhb_state) != bhb ||
		    READ_ONCE(system_bhb_mitigations) !=
			    effects->bhb.system_method ||
		    READ_ONCE(max_bhb_k) != effects->bhb.matcher_loop_count)
			return -EINVAL;
	}

	return 0;
}
#endif

static void this_cpu_set_vectors(enum arm64_bp_harden_el1_vectors slot)
'''


BLOCKERS_OLD = r'''/* Slices 1-8 own every gate except final verification and READY. */
#define MT6797_A72_PROFILE_BLOCKERS					\
	(ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS |			\
	 ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING)
'''

BLOCKERS_FINAL = r'''/* Runtime identity is the last core-owned prepare-time gate. */
#define MT6797_A72_PROFILE_BLOCKERS					\
	(ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING)
'''


PREPARE_RETURN_OLD = r'''	/* No live system capability, alternative, vector, or HWCAP is changed. */
	return -EAGAIN;
}

static const struct arm64_late_cpu_profile mt6797_a72_profile __initconst = {
'''

PREPARE_RETURN_FINAL = r'''	/* Fixture evidence remains historical and cannot publish READY. */
#ifdef CONFIG_ARM64_MT6797_A72_FIXTURE_EVIDENCE
	return -EAGAIN;
#else
	return 0;
#endif
}

static int __init
mt6797_a72_verify_system(const struct arm64_late_cpu_plan *plan,
			 const struct arm64_late_cpu_receipt *receipt)
{
	return arm64_verify_late_cpu_system(plan, receipt);
}

static int __init
mt6797_a72_finalize_user(const struct arm64_late_cpu_plan *plan,
			 const struct arm64_late_cpu_receipt *receipt)
{
	return arm64_finalize_late_cpu_hwcaps(plan, receipt);
}

static const struct arm64_late_cpu_profile mt6797_a72_profile __initconst = {
'''


PROFILE_WIRE_OLD = r'''	.derive_effects = mt6797_a72_derive_effects,
	.prepare = mt6797_a72_profile_prepare,
};
'''

PROFILE_WIRE_FINAL = r'''	.derive_effects = mt6797_a72_derive_effects,
	.prepare = mt6797_a72_profile_prepare,
	.verify_system = mt6797_a72_verify_system,
	.finalize_user = mt6797_a72_finalize_user,
};
'''


def apply(root: Path) -> None:
    validate_parent(root)
    replace_once(root / HEADER, HEADER_ANCHOR, HEADER_FINAL)
    replace_once(root / CPUFEATURE, CPUFEATURE_ANCHOR, CPUFEATURE_FINAL)
    replace_once(root / MITIGATIONS, MITIGATION_ANCHOR, MITIGATION_FINAL)
    replace_once(root / PROFILE, BLOCKERS_OLD, BLOCKERS_FINAL)
    replace_once(root / PROFILE, PREPARE_RETURN_OLD, PREPARE_RETURN_FINAL)
    replace_once(root / PROFILE, PROFILE_WIRE_OLD, PROFILE_WIRE_FINAL)
