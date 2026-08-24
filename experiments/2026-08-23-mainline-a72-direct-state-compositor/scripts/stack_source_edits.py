#!/usr/bin/env python3
"""Apply deterministic A72 direct-state stack-safety follow-up edits."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        first = old.splitlines()[0] if old.splitlines() else "<empty>"
        raise SystemExit(
            f"{path}: expected one anchor beginning {first!r}, found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_count(path: Path, old: str, new: str, expected: int) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != expected:
        raise SystemExit(
            f"{path}: expected {expected} occurrences of {old!r}, found {count}"
        )
    path.write_text(text.replace(old, new), encoding="utf-8")


def core(root: Path) -> None:
    membership = root / "arch/arm64/kernel/mt6797_a72_membership.c"
    old_owner = dedent(r'''
static bool
mt6797_a72_direct_owner_pristine_locked(struct mt6797_a72_owner_snapshot *snapshot)
{
	const struct mt6797_a72_owner_snapshot expected = {
		.diagnostic_blockers = MT6797_A72_BLOCK_MASK,
		.abi = MT6797_A72_TRANSACTION_ABI,
		.health = MT6797_A72_OWNER_CLOSED,
		.phase = MT6797_A72_PHASE_UNINITIALIZED,
		.provider_state = MT6797_A72_PROVIDER_NONE,
	};

	mt6797_a72_direct_owner_snapshot_locked(snapshot);
	return !memcmp(snapshot, &expected, sizeof(expected)) &&
		!a72_owner.controller && !a72_owner.next_generation &&
		!a72_owner.next_cookie;
}
''').lstrip("\n")
    new_owner = dedent(r'''
static const struct mt6797_a72_owner_snapshot a72_direct_expected_owner = {
	.diagnostic_blockers = MT6797_A72_BLOCK_MASK,
	.abi = MT6797_A72_TRANSACTION_ABI,
	.health = MT6797_A72_OWNER_CLOSED,
	.phase = MT6797_A72_PHASE_UNINITIALIZED,
	.provider_state = MT6797_A72_PROVIDER_NONE,
};

struct mt6797_a72_direct_state_workspace {
	struct mt6797_a72_direct_state_snapshot observed;
	struct mt6797_a72_owner_snapshot owner_after;
};

static struct mt6797_a72_direct_state_workspace a72_direct_workspace;

static bool
mt6797_a72_direct_owner_pristine_locked(struct mt6797_a72_owner_snapshot *snapshot)
{
	mt6797_a72_direct_owner_snapshot_locked(snapshot);
	return !memcmp(snapshot, &a72_direct_expected_owner,
		       sizeof(a72_direct_expected_owner)) &&
		!a72_owner.controller && !a72_owner.next_generation &&
		!a72_owner.next_cookie;
}
''').lstrip("\n")
    replace_once(membership, old_owner, new_owner)

    old_snapshot = dedent(r'''
static int
mt6797_a72_direct_state_snapshot_locked(const struct mt6797_a72_direct_topology *topology,
					struct mt6797_a72_direct_state_snapshot *snapshot)
{
	struct mt6797_a72_direct_state_snapshot observed = { };
	struct mt6797_a72_owner_snapshot owner_after;
	unsigned long flags;
	int ret;

	if (!mt6797_a72_direct_topology_valid(topology))
		return -EPERM;

	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (!mt6797_a72_direct_owner_pristine_locked(&observed.owner)) {
		raw_spin_unlock_irqrestore(&a72_state_lock, flags);
		return -EPERM;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);

	mutex_lock(&a72_direct_source_registry_lock);
	if (!a72_direct_source_ops) {
		ret = -ENODEV;
		goto out_unlock;
	}
	ret = a72_direct_source_ops->snapshot(a72_direct_source_context,
					      &observed.source);
	if (ret)
		goto out_unlock;
	if (!mt6797_a72_direct_source_valid(&observed.source)) {
		ret = -EPROTO;
		goto out_unlock;
	}

	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (!mt6797_a72_direct_owner_pristine_locked(&owner_after) ||
	    memcmp(&observed.owner, &owner_after, sizeof(owner_after)))
		ret = -EPERM;
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	if (ret)
		goto out_unlock;

	observed.abi = MT6797_A72_DIRECT_STATE_ABI;
	observed.valid = 1;
	observed.cpu8_possible = topology->cpu8_possible;
	observed.cpu9_possible = topology->cpu9_possible;
	observed.cpu8_present = topology->cpu8_present;
	observed.cpu9_present = topology->cpu9_present;
	observed.cpu8_online = topology->cpu8_online;
	observed.cpu9_online = topology->cpu9_online;
	*snapshot = observed;
out_unlock:
	mutex_unlock(&a72_direct_source_registry_lock);
	return ret;
}
''').lstrip("\n")
    new_snapshot = dedent(r'''
static int
mt6797_a72_direct_state_snapshot_locked(const struct mt6797_a72_direct_topology *topology,
					struct mt6797_a72_direct_state_snapshot *snapshot)
{
	struct mt6797_a72_direct_state_workspace *workspace =
		&a72_direct_workspace;
	struct mt6797_a72_direct_state_snapshot *observed =
		&workspace->observed;
	struct mt6797_a72_owner_snapshot *owner_after =
		&workspace->owner_after;
	unsigned long flags;
	int ret = -EPERM;

	memset(workspace, 0, sizeof(*workspace));
	if (!mt6797_a72_direct_topology_valid(topology))
		goto out_clear;

	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (!mt6797_a72_direct_owner_pristine_locked(&observed->owner)) {
		raw_spin_unlock_irqrestore(&a72_state_lock, flags);
		goto out_clear;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);

	mutex_lock(&a72_direct_source_registry_lock);
	if (!a72_direct_source_ops) {
		ret = -ENODEV;
		goto out_unlock;
	}
	ret = a72_direct_source_ops->snapshot(a72_direct_source_context,
					      &observed->source);
	if (ret)
		goto out_unlock;
	if (!mt6797_a72_direct_source_valid(&observed->source)) {
		ret = -EPROTO;
		goto out_unlock;
	}

	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (!mt6797_a72_direct_owner_pristine_locked(owner_after) ||
	    memcmp(&observed->owner, owner_after, sizeof(*owner_after)))
		ret = -EPERM;
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	if (ret)
		goto out_unlock;

	observed->abi = MT6797_A72_DIRECT_STATE_ABI;
	observed->valid = 1;
	observed->cpu8_possible = topology->cpu8_possible;
	observed->cpu9_possible = topology->cpu9_possible;
	observed->cpu8_present = topology->cpu8_present;
	observed->cpu9_present = topology->cpu9_present;
	observed->cpu8_online = topology->cpu8_online;
	observed->cpu9_online = topology->cpu9_online;
	*snapshot = *observed;
out_unlock:
	mutex_unlock(&a72_direct_source_registry_lock);
out_clear:
	memset(workspace, 0, sizeof(*workspace));
	return ret;
}
''').lstrip("\n")
    replace_once(membership, old_snapshot, new_snapshot)


def tests(root: Path) -> None:
    test = root / "arch/arm64/kernel/mt6797_a72_direct_state_test.c"
    old_state = dedent(r'''
struct direct_test_state {
	struct mt6797_a72_direct_source_snapshot source;
	enum direct_source_mutation mutation;
	int callback_result;
	u32 calls;
};
''').lstrip("\n")
    new_state = dedent(r'''
struct direct_test_state {
	struct mt6797_a72_direct_source_snapshot source;
	struct mt6797_a72_direct_state_snapshot observed;
	struct mt6797_a72_owner_snapshot owner_before;
	struct mt6797_a72_owner_snapshot owner_after;
	struct arm64_late_cpu_startup_snapshot p30_before;
	struct arm64_late_cpu_startup_snapshot p30_after;
	enum direct_source_mutation mutation;
	int callback_result;
	u32 calls;
};
''').lstrip("\n")
    old_zero = dedent(r'''
static void expect_zero(struct kunit *test,
			const struct mt6797_a72_direct_state_snapshot *snapshot)
{
	const struct mt6797_a72_direct_state_snapshot zero = { };

	KUNIT_EXPECT_EQ(test, memcmp(snapshot, &zero, sizeof(zero)), 0);
}
''').lstrip("\n")
    new_zero = dedent(r'''
static void expect_zero(struct kunit *test,
			const struct mt6797_a72_direct_state_snapshot *snapshot)
{
	KUNIT_EXPECT_PTR_EQ(test,
			    memchr_inv(snapshot, 0, sizeof(*snapshot)), NULL);
}
''').lstrip("\n")
    replace_once(test, old_zero, new_zero)

    replace_count(
        test,
        "\tstruct mt6797_a72_direct_state_snapshot observed;\n",
        "\tstruct mt6797_a72_direct_state_snapshot *observed = "
        "&state->observed;\n",
        7,
    )
    for declaration in (
        "\tstruct mt6797_a72_owner_snapshot before;\n",
        "\tstruct mt6797_a72_owner_snapshot after;\n",
        "\tstruct arm64_late_cpu_startup_snapshot p30_before;\n",
        "\tstruct arm64_late_cpu_startup_snapshot p30_after;\n",
    ):
        replace_once(test, declaration, "")
    replace_count(test, "&observed", "observed", 22)
    replace_count(test, "observed.", "observed->", 10)
    replace_count(test, "sizeof(observed)", "sizeof(*observed)", 7)
    replace_once(
        test,
        "mt6797_a72_membership_snapshot(&before);",
        "mt6797_a72_membership_snapshot(&state->owner_before);",
    )
    replace_once(
        test,
        "arm64_late_cpu_startup_snapshot(&p30_before);",
        "arm64_late_cpu_startup_snapshot(&state->p30_before);",
    )
    replace_once(
        test,
        "mt6797_a72_membership_snapshot(&after);",
        "mt6797_a72_membership_snapshot(&state->owner_after);",
    )
    replace_once(
        test,
        "arm64_late_cpu_startup_snapshot(&p30_after);",
        "arm64_late_cpu_startup_snapshot(&state->p30_after);",
    )
    replace_once(
        test,
        "memcmp(&before, &after, sizeof(before))",
        "memcmp(&state->owner_before,\n"
        "\t\t\t       &state->owner_after,\n"
        "\t\t\t       sizeof(state->owner_before))",
    )
    replace_once(
        test,
        "memcmp(&p30_before, &p30_after,\n"
        "\t\t\t\t     sizeof(p30_before))",
        "memcmp(&state->p30_before,\n"
        "\t\t\t       &state->p30_after,\n"
        "\t\t\t       sizeof(state->p30_before))",
    )
    replace_once(test, old_state, new_state)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("core", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.phase == "core":
        core(root)
    else:
        tests(root)


if __name__ == "__main__":
    main()
