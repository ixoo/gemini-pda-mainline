#!/usr/bin/env python3
"""Pure source edits for the expectation-only READY-token contract repair."""

from __future__ import annotations

from pathlib import Path


MEMBERSHIP = Path("arch/arm64/kernel/mt6797_a72_membership.c")
MEMBERSHIP_TEST = Path("arch/arm64/kernel/mt6797_a72_membership_test.c")
DERIVED_TEST = Path("arch/arm64/kernel/mt6797_a72_derived_admission_test.c")
REGULATOR_TEST = Path("drivers/regulator/da9213-legacy-membership-test.c")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one source match, found {count}")
    return text.replace(old, new, 1)


def apply(root: Path) -> None:
    membership_path = root / MEMBERSHIP
    membership = membership_path.read_text(encoding="utf-8")
    old = r'''static int
mt6797_a72_ready_token_validate(unsigned int cpu,
				const struct arm64_late_cpu_ready_token *ready)
{
	unsigned int slot;
	u64 expected_mpidr;

	if (!ready)
		return -EAGAIN;
	if (ready->abi != ARM64_LATE_CPU_PLAN_ABI ||
	    strcmp(ready->profile_id, "mt6797-a53-a72-a41-v7") ||
	    !mt6797_a72_identity_nonzero(ready->plan_identity) ||
	    !mt6797_a72_identity_nonzero(ready->source_parent_identity) ||
	    !mt6797_a72_identity_nonzero(ready->config_input_identity) ||
	    !mt6797_a72_identity_nonzero(ready->evidence_identity))
		return -EPERM;

	if (!cpumask_test_cpu(8, &ready->target_cpus) ||
	    !cpumask_test_cpu(9, &ready->target_cpus) ||
	    ready->target_cpu[0] != 8 || ready->target_cpu[1] != 9 ||
	    ready->expected_target_mpidr[0] != 0x200 ||
	    ready->expected_target_mpidr[1] != 0x201 ||
	    ready->observed_target_mpidr[0] != 0x200 ||
	    ready->observed_target_mpidr[1] != 0x201)
		return -EPERM;

	slot = cpu == 8 ? 0 : 1;
	expected_mpidr = slot == 0 ? 0x200 : 0x201;
	if (ready->target_cpu[slot] != cpu ||
	    ready->observed_target_mpidr[slot] != expected_mpidr)
		return -EPERM;

	return 0;
}
'''
    new = r'''static int
mt6797_a72_ready_token_validate(unsigned int cpu,
				const struct arm64_late_cpu_ready_token *ready)
{
	unsigned int slot;

	if (!ready)
		return -EAGAIN;
	if (ready->abi != ARM64_LATE_CPU_PLAN_ABI ||
	    strcmp(ready->profile_id, "mt6797-a53-a72-a41-v7") ||
	    !mt6797_a72_identity_nonzero(ready->plan_identity) ||
	    !mt6797_a72_identity_nonzero(ready->source_parent_identity) ||
	    !mt6797_a72_identity_nonzero(ready->config_input_identity) ||
	    !mt6797_a72_identity_nonzero(ready->evidence_identity))
		return -EPERM;

	if (!cpumask_test_cpu(8, &ready->target_cpus) ||
	    !cpumask_test_cpu(9, &ready->target_cpus) ||
	    ready->target_cpu[0] != 8 || ready->target_cpu[1] != 9 ||
	    ready->expected_target_mpidr[0] != 0x200 ||
	    ready->expected_target_mpidr[1] != 0x201)
		return -EPERM;

	/* Dormant targets have expectations, but no target-local observations. */
	if (ready->observed_target_mpidr[0] ||
	    ready->observed_target_mpidr[1])
		return -EPERM;

	slot = cpu == 8 ? 0 : 1;
	if (ready->target_cpu[slot] != cpu)
		return -EPERM;

	return 0;
}
'''
    membership = replace_once(
        membership, old, new, "READY-token validator"
    )
    membership_path.write_text(membership, encoding="utf-8")

    fixture = "\t\t.observed_target_mpidr = { 0x200, 0x201 },\n"
    replacement = "\t\t.observed_target_mpidr = { 0, 0 },\n"
    for relative in (MEMBERSHIP_TEST, DERIVED_TEST, REGULATOR_TEST):
        path = root / relative
        text = path.read_text(encoding="utf-8")
        text = replace_once(text, fixture, replacement, f"{relative} READY fixture")
        path.write_text(text, encoding="utf-8")

    derived_path = root / DERIVED_TEST
    derived = derived_path.read_text(encoding="utf-8")
    anchor = r'''static void mt6797_a72_legacy_assertions_rejected_test(struct kunit *test)
'''
    test = r'''static void mt6797_a72_derived_observed_target_rejected_test(struct kunit *test)
{
	struct mt6797_a72_derived_test_state *state = test->priv;
	unsigned int target;

	for (target = 0; target < 2; target++) {
		state->ready = mt6797_a72_exact_ready();
		state->ready.observed_target_mpidr[target] =
			state->ready.expected_target_mpidr[target];
		mt6797_a72_expect_source_rejection(test, state, -EPERM, 0);
	}
}

static void mt6797_a72_legacy_assertions_rejected_test(struct kunit *test)
'''
    derived = replace_once(derived, anchor, test, "observed-target rejection test")
    cases = r'''	KUNIT_CASE(mt6797_a72_derived_ready_rejection_test),
	KUNIT_CASE(mt6797_a72_legacy_assertions_rejected_test),
'''
    updated_cases = r'''	KUNIT_CASE(mt6797_a72_derived_ready_rejection_test),
	KUNIT_CASE(mt6797_a72_derived_observed_target_rejected_test),
	KUNIT_CASE(mt6797_a72_legacy_assertions_rejected_test),
'''
    derived = replace_once(derived, cases, updated_cases, "KUnit case registration")
    derived_path.write_text(derived, encoding="utf-8")
