#!/usr/bin/env python3
"""Require the finalized CPU8/CPU9 pair before minting CPU9-down."""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = (args.source_root.resolve() /
              "arch/arm64/kernel/mt6797_a72_membership.c")

    replace_once(
        source,
        r'''static bool
mt6797_a72_cpu9_retired_parent_valid_locked(u32 expected_members)
{
	const struct mt6797_a72_transaction *cpu8 = &a72_owner.retired[0];

	return a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
		a72_owner.bootstrap_valid && a72_owner.members_valid &&
		a72_owner.members == expected_members &&
		a72_owner.provider_state == MT6797_A72_PROVIDER_HELD &&
		mt6797_a72_provider_identity_valid(&a72_owner.provider_identity) &&
		(a72_owner.retired_mask & BIT(0)) &&
		!(a72_owner.retired_mask & BIT(1)) && cpu8->valid &&
		cpu8->identity.abi == MT6797_A72_TRANSACTION_ABI &&
		cpu8->identity.operation == ARM64_LATE_CPU_STARTUP_OP_CPU8_UP &&
		cpu8->identity.target_cpu == 8 &&
		cpu8->identity.cpuhp_target == CPUHP_ONLINE &&
		cpu8->identity.target_mpidr == 0x200 &&
		cpu8->public_preflight == MT6797_A72_PUBLIC_ADMISSION_CLAIMED &&
		cpu8->p17_p18_published && cpu8->p27_valid &&
		cpu8->provider_acquire_valid && cpu8->p28_valid &&
		cpu8->p30_token_valid && cpu8->cpu8_success_published &&
		!cpu8->cpu9_success_published && !cpu8->p29_valid &&
		!cpu8->p32_valid &&
		!memcmp(&cpu8->provider_identity, &a72_owner.provider_identity,
			sizeof(cpu8->provider_identity));
}
''',
        r'''static bool
mt6797_a72_cpu8_retired_valid_locked(u32 expected_members)
{
	const struct mt6797_a72_transaction *cpu8 = &a72_owner.retired[0];

	return a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
		a72_owner.bootstrap_valid && a72_owner.members_valid &&
		a72_owner.members == expected_members &&
		a72_owner.provider_state == MT6797_A72_PROVIDER_HELD &&
		mt6797_a72_provider_identity_valid(&a72_owner.provider_identity) &&
		(a72_owner.retired_mask & BIT(0)) && cpu8->valid &&
		cpu8->identity.abi == MT6797_A72_TRANSACTION_ABI &&
		cpu8->identity.operation == ARM64_LATE_CPU_STARTUP_OP_CPU8_UP &&
		cpu8->identity.target_cpu == 8 &&
		cpu8->identity.cpuhp_target == CPUHP_ONLINE &&
		cpu8->identity.target_mpidr == 0x200 &&
		cpu8->public_preflight == MT6797_A72_PUBLIC_ADMISSION_CLAIMED &&
		cpu8->p17_p18_published && cpu8->p27_valid &&
		cpu8->provider_acquire_valid && cpu8->p28_valid &&
		cpu8->p30_token_valid && cpu8->cpu8_success_published &&
		!cpu8->cpu9_success_published && !cpu8->p29_valid &&
		!cpu8->p32_valid &&
		!memcmp(&cpu8->provider_identity, &a72_owner.provider_identity,
			sizeof(cpu8->provider_identity));
}

static bool
mt6797_a72_cpu9_retired_parent_valid_locked(u32 expected_members)
{
	return !(a72_owner.retired_mask & BIT(1)) &&
		mt6797_a72_cpu8_retired_valid_locked(expected_members);
}

static bool mt6797_a72_cpu9_terminal_parent_valid_locked(void)
{
	const struct mt6797_a72_transaction *cpu8 = &a72_owner.retired[0];
	const struct mt6797_a72_transaction *cpu9 = &a72_owner.retired[1];

	return a72_owner.retired_mask == (BIT(0) | BIT(1)) &&
		mt6797_a72_cpu8_retired_valid_locked(BIT(0) | BIT(1)) &&
		cpu9->valid && cpu9->a36_valid && cpu9->p30_token_valid &&
		cpu9->p17_p18_published &&
		cpu9->identity.abi == MT6797_A72_TRANSACTION_ABI &&
		cpu9->identity.operation == ARM64_LATE_CPU_STARTUP_OP_CPU9_UP &&
		cpu9->identity.target_cpu == 9 &&
		cpu9->identity.cpuhp_target == CPUHP_ONLINE &&
		cpu9->identity.target_mpidr == 0x201 &&
		cpu9->identity.generation && cpu9->identity.cookie &&
		cpu9->identity.generation != ~0ULL &&
		cpu9->identity.cookie != ~0ULL &&
		cpu9->identity.generation != cpu8->identity.generation &&
		cpu9->identity.cookie != cpu8->identity.cookie &&
		cpu9->controller_cookie == cpu9->identity.cookie &&
		cpu9->public_preflight == MT6797_A72_PUBLIC_ADMISSION_CLAIMED &&
		cpu9->budgets.cpu_on == MT6797_A72_BUDGET_CONSUMED &&
		mt6797_a72_cpu9_cluster_budgets_empty(cpu9) &&
		!cpu9->p27_valid && !cpu9->provider_acquire_valid &&
		!cpu9->provider_rejection_valid &&
		!cpu9->provider_abort_valid && !cpu9->p28_valid &&
		!cpu9->p29_valid && !cpu9->p32_valid && !cpu9->p32r_valid &&
		!cpu9->cpu8_success_published && cpu9->cpu9_success_published &&
		!memcmp(&cpu9->provider_identity, &a72_owner.provider_identity,
			sizeof(cpu9->provider_identity));
}
''',
    )
    replace_once(
        source,
        "!mt6797_a72_cpu9_retired_parent_valid_locked(BIT(0) |\n"
        "\t\t\t\t\t\t\t    BIT(1)) ||",
        "!mt6797_a72_cpu9_terminal_parent_valid_locked() ||",
    )


if __name__ == "__main__":
    main()
