#!/usr/bin/env python3
"""Apply the frozen atomic A72 publication source phases."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = SCRIPT_DIR.parent / "source"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        first = old.splitlines()[0] if old.splitlines() else "<empty>"
        raise SystemExit(
            f"{path}: expected one anchor beginning {first!r}, found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def finalizer(root: Path) -> None:
    header = root / "arch/arm64/include/asm/late_cpu_startup.h"
    replace_once(
        header,
        "struct arm64_late_cpu_bootstrap_claim {\n"
        "\tu32 abi;\n"
        "\tu32 reserved;\n"
        "\tu64 cookie;\n"
        "};\n\n"
        "#ifdef CONFIG_ARM64_LATE_CPU_STARTUP_FAILSTOP\n",
        "struct arm64_late_cpu_bootstrap_claim {\n"
        "\tu32 abi;\n"
        "\tu32 reserved;\n"
        "\tu64 cookie;\n"
        "};\n\n"
        "typedef int (*arm64_late_cpu_bootstrap_commit_t)(void *context);\n\n"
        "#ifdef CONFIG_ARM64_LATE_CPU_STARTUP_FAILSTOP\n",
    )
    replace_once(
        header,
        "int arm64_late_cpu_startup_release_pristine(struct arm64_late_cpu_bootstrap_claim *claim);\n"
        "int arm64_late_cpu_startup_prepare",
        "int arm64_late_cpu_startup_release_pristine(struct arm64_late_cpu_bootstrap_claim *claim);\n"
        "int\n"
        "arm64_late_cpu_startup_finalize_pristine("
        "struct arm64_late_cpu_bootstrap_claim *claim,\n"
        "\tarm64_late_cpu_bootstrap_commit_t commit, void *context);\n"
        "int arm64_late_cpu_startup_prepare",
    )
    release_stub = dedent(r'''
static inline int
arm64_late_cpu_startup_release_pristine(struct arm64_late_cpu_bootstrap_claim *claim)
{
	(void)claim;
	return -EOPNOTSUPP;
}

''').lstrip("\n")
    finalize_stub = dedent(r'''
static inline int
arm64_late_cpu_startup_finalize_pristine(struct arm64_late_cpu_bootstrap_claim *claim,
	arm64_late_cpu_bootstrap_commit_t commit, void *context)
{
	(void)claim;
	(void)commit;
	(void)context;
	return -EOPNOTSUPP;
}

''').lstrip("\n")
    replace_once(header, release_stub, release_stub + finalize_stub)

    source = root / "arch/arm64/kernel/late_cpu_startup.c"
    replace_once(
        source,
        "static bool late_startup_pristine_locked(void)\n",
        "static bool late_startup_pristine_locked(u64 allowed_claim_cookie)\n",
    )
    replace_once(
        source,
        "\t    late_startup.bootstrap_claim_cookie ||\n",
        "\t    late_startup.bootstrap_claim_cookie != allowed_claim_cookie ||\n",
    )
    replace_once(
        source,
        "\tif (!late_startup_pristine_locked()) {\n",
        "\tif (!late_startup_pristine_locked(0)) {\n",
    )
    finalize_function = dedent(r'''
int
arm64_late_cpu_startup_finalize_pristine(struct arm64_late_cpu_bootstrap_claim *claim,
	arm64_late_cpu_bootstrap_commit_t commit, void *context)
{
	unsigned long flags;
	int ret;

	if (!claim || claim->abi != ARM64_LATE_CPU_BOOTSTRAP_CLAIM_ABI ||
	    claim->reserved || !claim->cookie || !commit)
		return -EINVAL;
	raw_spin_lock_irqsave(&late_startup.lock, flags);
	if (claim->cookie != late_startup.bootstrap_claim_cookie) {
		ret = -ESTALE;
	} else if (!late_startup_pristine_locked(claim->cookie)) {
		ret = -EBUSY;
	} else {
		late_startup.bootstrap_claim_cookie = 0;
		*claim = (struct arm64_late_cpu_bootstrap_claim){};
		ret = commit(context);
	}
	raw_spin_unlock_irqrestore(&late_startup.lock, flags);
	return ret;
}

''').lstrip("\n")
    replace_once(
        source,
        "int arm64_late_cpu_startup_prepare(const struct arm64_late_cpu_up_token *token)\n",
        finalize_function
        + "int arm64_late_cpu_startup_prepare(const struct arm64_late_cpu_up_token *token)\n",
    )


def publisher(root: Path) -> None:
    header = root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    api = dedent(r'''
#ifdef CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER
int
mt6797_a72_membership_publish_bootstrap(const struct mt6797_a72_a34_replay *replay);
#else
static inline int
mt6797_a72_membership_publish_bootstrap(const struct mt6797_a72_a34_replay *replay)
{
	(void)replay;
	return -EOPNOTSUPP;
}
#endif

#ifdef CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST
int
mt6797_a72_membership_test_publish_bootstrap(const struct mt6797_a72_direct_topology *topology,
	const struct mt6797_a72_a34_replay *replay,
	bool dirty_owner_before_finalize);
#endif

''').lstrip("\n")
    replace_once(
        header,
        "#ifdef CONFIG_ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL\n",
        api + "#ifdef CONFIG_ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL\n",
    )

    source = root / "arch/arm64/kernel/mt6797_a72_membership.c"
    code = dedent(r'''
#ifdef CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER
struct mt6797_a72_bootstrap_plan {
	u64 diagnostic_blockers;
	u64 next_generation;
	u64 next_cookie;
	u32 phase;
	u32 members;
	u32 provider_state;
	u32 bootstrap_valid;
	u32 members_valid;
	u32 attempts_available;
};

struct mt6797_a72_bootstrap_workspace {
	struct mt6797_a72_a34_observation observation;
	struct mt6797_a72_owner_snapshot owner_after;
	struct arm64_late_cpu_bootstrap_claim claim;
	struct mt6797_a72_bootstrap_plan plan;
};

static struct mt6797_a72_bootstrap_workspace a72_bootstrap_workspace;

static int
mt6797_a72_bootstrap_replay_valid(const struct mt6797_a72_a34_replay *replay)
{
	if (!replay)
		return -EINVAL;
	if (replay->abi != MT6797_A72_A34_REPLAY_ABI ||
	    replay->reserved[0] || replay->reserved[1] ||
	    replay->reserved[2] || replay->reserved[3])
		return -EPROTO;
	if (replay->valid != 1 ||
	    replay->proof == MT6797_A72_A34_REPLAY_UNKNOWN)
		return -ENODATA;
	if (replay->proof !=
	    MT6797_A72_A34_REPLAY_APPLICABLE_PRIMARY_BL31_CLEAR ||
	    replay->private_replay_value)
		return -EPERM;
	return 0;
}

static int mt6797_a72_bootstrap_owner_precheck(void)
{
	struct mt6797_a72_bootstrap_workspace *workspace =
		&a72_bootstrap_workspace;
	struct mt6797_a72_owner_snapshot *owner_after =
		&workspace->owner_after;
	unsigned long flags;
	int ret;

	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (a72_owner.health == MT6797_A72_OWNER_AVAILABLE)
		ret = -EALREADY;
	else if (!mt6797_a72_direct_owner_pristine_locked(owner_after))
		ret = -EPERM;
	else
		ret = 0;
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	return ret;
}

static void
mt6797_a72_bootstrap_prepare_plan(struct mt6797_a72_bootstrap_plan *plan)
{
	*plan = (struct mt6797_a72_bootstrap_plan) {
		.diagnostic_blockers = MT6797_A72_BLOCK_MASK &
			~MT6797_A72_BLOCK_A34_BOOTSTRAP,
		.next_generation = 1,
		.next_cookie = 0xa7200001,
		.phase = MT6797_A72_PHASE_IDLE,
		.provider_state = MT6797_A72_PROVIDER_NONE,
		.bootstrap_valid = 1,
		.members_valid = 1,
		.attempts_available = MT6797_A72_ATTEMPT_MASK,
	};
}

static int mt6797_a72_bootstrap_commit(void *context)
{
	struct mt6797_a72_bootstrap_workspace *workspace = context;
	struct mt6797_a72_owner_snapshot *owner_after =
		&workspace->owner_after;
	const struct mt6797_a72_bootstrap_plan *plan = &workspace->plan;
	unsigned long flags;
	int ret = -EPERM;

	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (!mt6797_a72_direct_owner_pristine_locked(owner_after) ||
	    memcmp(&workspace->observation.direct.owner, owner_after,
		   sizeof(*owner_after)))
		goto out;

	a72_owner.diagnostic_blockers = plan->diagnostic_blockers;
	a72_owner.phase = plan->phase;
	a72_owner.members = plan->members;
	a72_owner.provider_state = plan->provider_state;
	a72_owner.bootstrap_valid = plan->bootstrap_valid;
	a72_owner.members_valid = plan->members_valid;
	a72_owner.attempts_available = plan->attempts_available;
	a72_owner.next_generation = plan->next_generation;
	a72_owner.next_cookie = plan->next_cookie;
	a72_owner.health = MT6797_A72_OWNER_AVAILABLE;
	ret = 0;
out:
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	return ret;
}

static int
mt6797_a72_membership_publish_bootstrap_locked(const struct mt6797_a72_direct_topology *topology,
	const struct mt6797_a72_a34_replay *replay,
	bool dirty_owner_before_finalize)
{
	struct mt6797_a72_bootstrap_workspace *workspace =
		&a72_bootstrap_workspace;
	int release_ret;
	int ret;
#ifdef CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST
	unsigned long flags;
#endif

	memset(workspace, 0, sizeof(*workspace));
	ret = mt6797_a72_bootstrap_owner_precheck();
	if (ret)
		goto out_clear;
	ret = mt6797_a72_bootstrap_replay_valid(replay);
	if (ret)
		goto out_clear;
	ret = mt6797_a72_direct_state_snapshot_locked(topology,
						      &workspace->observation.direct);
	if (ret)
		goto out_clear;
	workspace->observation.abi = MT6797_A72_A34_ELIGIBILITY_ABI;
	workspace->observation.replay = *replay;
	ret = mt6797_a72_a34_evaluate(&workspace->observation);
	if (ret)
		goto out_clear;
	mt6797_a72_bootstrap_prepare_plan(&workspace->plan);
	ret = arm64_late_cpu_startup_claim_pristine(&workspace->claim);
	if (ret)
		goto out_clear;
#ifdef CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST
	if (dirty_owner_before_finalize) {
		raw_spin_lock_irqsave(&a72_state_lock, flags);
		a72_owner.next_cookie = 1;
		raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	}
#else
	(void)dirty_owner_before_finalize;
#endif
	ret = arm64_late_cpu_startup_finalize_pristine(&workspace->claim,
			mt6797_a72_bootstrap_commit, workspace);
	if (workspace->claim.cookie) {
		release_ret = arm64_late_cpu_startup_release_pristine(&workspace->claim);
		if (release_ret)
			ret = release_ret;
	}
out_clear:
	memset(workspace, 0, sizeof(*workspace));
	return ret;
}

int
mt6797_a72_membership_publish_bootstrap(const struct mt6797_a72_a34_replay *replay)
{
	struct mt6797_a72_direct_topology topology = {};
	int ret;

	cpus_read_lock();
	mutex_lock(&a72_transition_lock);
	if (nr_cpu_ids <= 9) {
		ret = -ENODEV;
		goto out_unlock;
	}
	topology.cpu8_possible = cpu_possible(8);
	topology.cpu9_possible = cpu_possible(9);
	topology.cpu8_present = cpu_present(8);
	topology.cpu9_present = cpu_present(9);
	topology.cpu8_online = cpu_online(8);
	topology.cpu9_online = cpu_online(9);
	topology.cpu8_method_valid = get_cpu_ops(8) == &mt6797_psci_ops;
	topology.cpu9_method_valid = get_cpu_ops(9) == &mt6797_psci_ops;
	topology.cpu8_mpidr = cpu_logical_map(8);
	topology.cpu9_mpidr = cpu_logical_map(9);
	ret = mt6797_a72_membership_publish_bootstrap_locked(&topology, replay,
						      false);
out_unlock:
	mutex_unlock(&a72_transition_lock);
	cpus_read_unlock();
	return ret;
}

#ifdef CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST
int
mt6797_a72_membership_test_publish_bootstrap(const struct mt6797_a72_direct_topology *topology,
	const struct mt6797_a72_a34_replay *replay,
	bool dirty_owner_before_finalize)
{
	int ret;

	if (!topology)
		return -EINVAL;
	cpus_read_lock();
	mutex_lock(&a72_transition_lock);
	ret = mt6797_a72_membership_publish_bootstrap_locked(topology, replay,
						dirty_owner_before_finalize);
	mutex_unlock(&a72_transition_lock);
	cpus_read_unlock();
	return ret;
}
#endif
#endif

''').lstrip("\n")
    replace_once(
        source,
        "static bool\nmt6797_a72_p32_target_locked(unsigned int cpu)\n",
        code + "static bool\nmt6797_a72_p32_target_locked(unsigned int cpu)\n",
    )

    platforms = root / "arch/arm64/Kconfig.platforms"
    config = dedent(r'''
config ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER
	bool "Publish exact MT6797 A72 bootstrap state"
	depends on HOTPLUG_CPU
	depends on ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR
	depends on ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR
	default n
	help
	  Add one default-off atomic owner publication boundary under the CPU
	  hotplug read lock, transition mutex, P30 pristine claim, and owner raw
	  lock. The path has no production caller or physical source binding.

	  Publication clears only the diagnostic A34-bootstrap blocker. Both
	  CPU-up vetoes, the MT6797 CPU boot veto, and CPU-disable veto remain.
	  This option performs no provider, hardware, CPU_ON, or CPU_OFF action.

''').lstrip("\n")
    replace_once(
        platforms,
        "config ARM64_MT6797_A72_P24_ADMISSION_HOOKS\n",
        config + "config ARM64_MT6797_A72_P24_ADMISSION_HOOKS\n",
    )


def tests(root: Path) -> None:
    test_path = root / "arch/arm64/kernel/mt6797_a72_atomic_publication_test.c"
    if test_path.exists():
        raise SystemExit(f"refusing to overwrite {test_path}")
    test_path.write_bytes(
        (SOURCE_DIR / "mt6797_a72_atomic_publication_test.c").read_bytes()
    )

    kconfig = root / "arch/arm64/Kconfig"
    config = dedent(r'''
config ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST
	bool "KUnit tests for atomic MT6797 A72 bootstrap publication"
	depends on KUNIT=y
	depends on HOTPLUG_CPU
	depends on ARM64_MT6797_A72_P30_PROTOCOL_MODEL
	select ARM64_LATE_CPU_STARTUP_KUNIT_TEST
	select ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL
	select ARM64_MT6797_A72_P24_ADMISSION_HOOKS
	select ARM64_MT6797_A72_P24_OWNER_TEST_SEED
	select ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR
	select ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR
	select ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER
	help
	  Exercise the nested P30 finalizer and exact one-shot owner commit with
	  injected topology, direct state, and replay applicability. Cover every
	  fail-closed input and retain both CPU vetoes without hardware effects.

	  The suite supplies no physical source, production caller, provider
	  action, CPU_ON, CPU_OFF, device access, or boot candidate.

''').lstrip("\n")
    replace_once(
        kconfig,
        "config ARM64_MT6797_A72_PROVIDER_OWNER\n",
        config + "config ARM64_MT6797_A72_PROVIDER_OWNER\n",
    )

    makefile = root / "arch/arm64/kernel/Makefile"
    anchor = (
        "obj-$(CONFIG_ARM64_MT6797_A72_DIRECT_STATE_KUNIT_TEST) "
        "+= mt6797_a72_direct_state_test.o\n"
    )
    replace_once(
        makefile,
        anchor,
        anchor
        + "obj-$(CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST) "
        "+= mt6797_a72_atomic_publication_test.o\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--phase", choices=("finalizer", "publisher", "tests"), required=True
    )
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.phase == "finalizer":
        finalizer(root)
    elif args.phase == "publisher":
        publisher(root)
    else:
        tests(root)


if __name__ == "__main__":
    main()
