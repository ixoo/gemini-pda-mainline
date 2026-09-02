#!/usr/bin/env python3
"""Add the hardware-free CPU9 down and distinct-restore owner."""

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
    root = args.source_root.resolve()
    header = root / "arch/arm64/include/asm/mt6797_a72_membership.h"
    source = root / "arch/arm64/kernel/mt6797_a72_membership.c"

    replace_once(
        header,
        "#define MT6797_A72_ATTEMPT_CPU8_LAST_OFF BIT(3)\n"
        "#define MT6797_A72_ATTEMPT_MASK GENMASK(3, 0)\n",
        "#define MT6797_A72_ATTEMPT_CPU8_LAST_OFF BIT(3)\n"
        "#define MT6797_A72_ATTEMPT_CPU9_RESTORE BIT(4)\n"
        "#define MT6797_A72_ATTEMPT_MASK GENMASK(4, 0)\n",
    )
    replace_once(
        header,
        "struct mt6797_a72_owner_snapshot {\n",
        r'''#define MT6797_A72_HOTPLUG_ABI 1
#define MT6797_A72_CPU9_OFF_PROOF_ABI 1
#define MT6797_A72_HOTPLUG_RETIRED_SLOTS 2
#define MT6797_A72_AFFINITY_LEVEL0 0
#define MT6797_A72_AFFINITY_STATE_OFF 1

enum mt6797_a72_hotplug_operation {
	MT6797_A72_HOTPLUG_OPERATION_NONE,
	MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN,
	MT6797_A72_HOTPLUG_OPERATION_CPU9_RESTORE,
};

enum mt6797_a72_hotplug_phase {
	MT6797_A72_HOTPLUG_NONE,
	MT6797_A72_HOTPLUG_IDLE,
	MT6797_A72_HOTPLUG_DOWN_FROZEN,
	MT6797_A72_HOTPLUG_DOWN_VALIDATED,
	MT6797_A72_HOTPLUG_OFF_COMMITTED,
	MT6797_A72_HOTPLUG_OFF_PROVEN,
	MT6797_A72_HOTPLUG_OFFLINE,
	MT6797_A72_HOTPLUG_RESTORE_FROZEN,
	MT6797_A72_HOTPLUG_RESTORE_ON_ISSUED,
	MT6797_A72_HOTPLUG_RESTORED,
	MT6797_A72_HOTPLUG_REJECTED,
	MT6797_A72_HOTPLUG_FAULT,
};

struct mt6797_a72_hotplug_identity {
	u32 abi;
	u32 operation;
	u32 target_cpu;
	u32 cpuhp_target;
	u64 target_mpidr;
	u64 generation;
	u64 cookie;
	u64 parent_generation;
	u64 parent_cookie;
};

struct mt6797_a72_hotplug_budgets {
	u8 cpu_off;
	u8 affinity;
	u8 cpu_on;
	u8 reserved;
};

struct mt6797_a72_cpu9_off_proof {
	u32 abi;
	u32 valid;
	u32 affinity_attempted;
	u32 affinity_level;
	u32 affinity_state;
	u32 cpu9_per_core_off;
	u32 cpu8_responsive;
	u32 shared_state_unchanged;
	u32 members_before;
	u32 online_mask_after;
	struct mt6797_a72_provider_identity provider_identity;
	u64 transaction_generation;
	u64 transaction_cookie;
};

struct mt6797_a72_hotplug_transaction {
	struct mt6797_a72_hotplug_identity identity;
	struct mt6797_a72_hotplug_budgets budgets;
	struct mt6797_a72_provider_identity provider_identity;
	struct mt6797_a72_cpu9_off_proof off_proof;
	u32 entry_members;
	u32 entry_online_mask;
	u32 off_committed;
	u32 off_proven;
	u32 completed;
	u32 restored;
	s32 failure_error;
	u32 valid;
};

struct mt6797_a72_hotplug_snapshot {
	struct mt6797_a72_hotplug_transaction active;
	struct mt6797_a72_hotplug_transaction
		retired[MT6797_A72_HOTPLUG_RETIRED_SLOTS];
	u32 abi;
	u32 phase;
	u32 retired_mask;
	u32 members;
	u32 attempts_consumed;
	u32 owner_health;
	u32 controller_present;
};

struct mt6797_a72_owner_snapshot {
''',
    )
    replace_once(
        header,
        "int mt6797_a72_finalize_cpu9_success_locked(struct mt6797_a72_transaction *transaction);\n"
        "#endif\n",
        r'''int mt6797_a72_finalize_cpu9_success_locked(struct mt6797_a72_transaction *transaction);
int mt6797_a72_hotplug_prepare_down(unsigned int cpu,
				    enum cpuhp_state target,
				    bool cpu8_online, bool cpu9_online,
				    struct mt6797_a72_hotplug_transaction *transaction);
int mt6797_a72_hotplug_validate_down(
	struct mt6797_a72_hotplug_transaction *transaction,
	int tasks_frozen, enum cpuhp_state target,
	bool cpu8_online, bool cpu9_online);
int mt6797_a72_hotplug_commit_off(unsigned int cpu);
int mt6797_a72_hotplug_prove_off(
	struct mt6797_a72_hotplug_transaction *transaction,
	const struct mt6797_a72_cpu9_off_proof *proof);
int mt6797_a72_hotplug_complete_down(
	struct mt6797_a72_hotplug_transaction *transaction,
	bool cpu8_online, bool cpu9_online);
int mt6797_a72_hotplug_fail_down(
	struct mt6797_a72_hotplug_transaction *transaction, int error);
int mt6797_a72_hotplug_prepare_restore(
	unsigned int cpu, enum cpuhp_state target,
	bool cpu8_online, bool cpu9_online,
	struct mt6797_a72_hotplug_transaction *transaction);
int mt6797_a72_hotplug_begin_restore(
	struct mt6797_a72_hotplug_transaction *transaction,
	bool cpu8_online, bool cpu9_online);
int mt6797_a72_hotplug_complete_restore(
	struct mt6797_a72_hotplug_transaction *transaction,
	bool cpu8_online, bool cpu9_online);
int mt6797_a72_hotplug_fail_restore(
	struct mt6797_a72_hotplug_transaction *transaction, int error);
void mt6797_a72_hotplug_snapshot(
	struct mt6797_a72_hotplug_snapshot *snapshot);
#endif
''',
    )
    replace_once(
        source,
        "struct mt6797_a72_owner_state {\n"
        "\tstruct mt6797_a72_transaction active;\n",
        "struct mt6797_a72_owner_state {\n"
        "\tstruct mt6797_a72_transaction active;\n"
        "\tstruct mt6797_a72_hotplug_transaction hotplug_active;\n"
        "\tstruct mt6797_a72_hotplug_transaction\n"
        "\t\thotplug_retired[MT6797_A72_HOTPLUG_RETIRED_SLOTS];\n",
    )
    replace_once(
        source,
        "\tu32 attempts_consumed;\n"
        "\tu32 retired_mask;\n"
        "};\n",
        "\tu32 attempts_consumed;\n"
        "\tu32 retired_mask;\n"
        "\tu32 hotplug_phase;\n"
        "\tu32 hotplug_retired_mask;\n"
        "};\n",
    )
    replace_once(
        source,
        "\t\ta72_owner.phase = MT6797_A72_PHASE_IDLE;\n"
        "\t\tret = 0;\n"
        "\t}\n"
        "\traw_spin_unlock_irqrestore(&a72_state_lock, flags);\n"
        "\tmutex_unlock(&a72_transition_lock);\n"
        "\treturn ret;\n"
        "}\n\n"
        "int\n"
        "mt6797_a72_finalize_cpu9_success_locked",
        "\t\ta72_owner.phase = MT6797_A72_PHASE_IDLE;\n"
        "\t\ta72_owner.hotplug_phase = MT6797_A72_HOTPLUG_IDLE;\n"
        "\t\tret = 0;\n"
        "\t}\n"
        "\traw_spin_unlock_irqrestore(&a72_state_lock, flags);\n"
        "\tmutex_unlock(&a72_transition_lock);\n"
        "\treturn ret;\n"
        "}\n\n"
        "int\n"
        "mt6797_a72_finalize_cpu9_success_locked",
    )
    replace_once(
        source,
        "#ifdef CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED\n"
        "int mt6797_a72_membership_test_preflight_cpu9",
        r'''static bool
mt6797_a72_hotplug_identity_equal(
	const struct mt6797_a72_hotplug_identity *left,
	const struct mt6797_a72_hotplug_identity *right)
{
	return !memcmp(left, right, sizeof(*left));
}

static bool
mt6797_a72_hotplug_active_locked(
	const struct mt6797_a72_hotplug_transaction *transaction,
	enum mt6797_a72_hotplug_operation operation)
{
	const struct mt6797_a72_hotplug_transaction *active =
		&a72_owner.hotplug_active;

	return active->valid &&
		active->identity.abi == MT6797_A72_HOTPLUG_ABI &&
		active->identity.operation == operation &&
		active->identity.target_cpu == 9 &&
		active->identity.target_mpidr == 0x201 &&
		active->identity.generation && active->identity.cookie &&
		active->identity.generation != ~0ULL &&
		active->identity.cookie != ~0ULL &&
		!memcmp(&active->provider_identity,
			&a72_owner.provider_identity,
			sizeof(active->provider_identity)) &&
		(!transaction ||
		 mt6797_a72_hotplug_identity_equal(&active->identity,
						   &transaction->identity));
}

static void
mt6797_a72_hotplug_retire_locked(unsigned int slot,
				 enum mt6797_a72_hotplug_phase phase)
{
	a72_owner.hotplug_retired[slot] = a72_owner.hotplug_active;
	a72_owner.hotplug_retired_mask |= BIT(slot);
	memset(&a72_owner.hotplug_active, 0,
	       sizeof(a72_owner.hotplug_active));
	a72_owner.controller = NULL;
	a72_owner.controller_cookie = 0;
	a72_owner.hotplug_phase = phase;
}

static void mt6797_a72_hotplug_fault_locked(int error)
{
	a72_owner.hotplug_active.failure_error = error;
	a72_owner.health = MT6797_A72_OWNER_FAULTED;
	a72_owner.phase = MT6797_A72_PHASE_FAULT;
	a72_owner.hotplug_phase = MT6797_A72_HOTPLUG_FAULT;
}

int mt6797_a72_hotplug_prepare_down(
	unsigned int cpu, enum cpuhp_state target,
	bool cpu8_online, bool cpu9_online,
	struct mt6797_a72_hotplug_transaction *transaction)
{
	struct mt6797_a72_hotplug_transaction minted = { };
	const struct mt6797_a72_transaction *parent;
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction)
		return -EINVAL;
	memset(transaction, 0, sizeof(*transaction));
	if (cpu != 9 || target != CPUHP_OFFLINE)
		return -EINVAL;

	mutex_lock(&a72_transition_lock);
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (a72_owner.health == MT6797_A72_OWNER_CLOSED) {
		ret = -EAGAIN;
	} else if (a72_owner.health == MT6797_A72_OWNER_FAULTED) {
		ret = -ESHUTDOWN;
	} else if (a72_owner.phase != MT6797_A72_PHASE_IDLE ||
		   a72_owner.hotplug_phase != MT6797_A72_HOTPLUG_IDLE ||
		   a72_owner.hotplug_active.valid ||
		   a72_owner.hotplug_retired_mask ||
		   a72_owner.members != (BIT(0) | BIT(1)) ||
		   a72_owner.provider_state != MT6797_A72_PROVIDER_HELD ||
		   !mt6797_a72_provider_identity_valid(
			   &a72_owner.provider_identity) ||
		   !mt6797_a72_cpu9_retired_parent_valid_locked(
			   BIT(0) | BIT(1)) ||
		   !cpu8_online || !cpu9_online ||
		   a72_owner.controller ||
		   !(a72_owner.attempts_available &
		     MT6797_A72_ATTEMPT_CPU9_OFF) ||
		   (a72_owner.attempts_consumed &
		    MT6797_A72_ATTEMPT_CPU9_OFF)) {
		ret = -EPERM;
	} else if (!a72_owner.next_generation || !a72_owner.next_cookie ||
		   a72_owner.next_generation == ~0ULL ||
		   a72_owner.next_cookie == ~0ULL) {
		ret = -EPROTO;
	} else {
		parent = &a72_owner.retired[1];
		minted.identity.abi = MT6797_A72_HOTPLUG_ABI;
		minted.identity.operation =
			MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN;
		minted.identity.target_cpu = 9;
		minted.identity.cpuhp_target = CPUHP_OFFLINE;
		minted.identity.target_mpidr = 0x201;
		minted.identity.generation = a72_owner.next_generation++;
		minted.identity.cookie = a72_owner.next_cookie++;
		minted.identity.parent_generation =
			parent->identity.generation;
		minted.identity.parent_cookie = parent->identity.cookie;
		minted.budgets.cpu_off = MT6797_A72_BUDGET_AVAILABLE;
		minted.budgets.affinity = MT6797_A72_BUDGET_AVAILABLE;
		minted.provider_identity = a72_owner.provider_identity;
		minted.entry_members = BIT(0) | BIT(1);
		minted.entry_online_mask = BIT(0) | BIT(1);
		minted.valid = 1;
		a72_owner.attempts_available &=
			~MT6797_A72_ATTEMPT_CPU9_OFF;
		a72_owner.attempts_consumed |=
			MT6797_A72_ATTEMPT_CPU9_OFF;
		a72_owner.hotplug_active = minted;
		a72_owner.controller = current;
		a72_owner.controller_cookie = minted.identity.cookie;
		a72_owner.hotplug_phase = MT6797_A72_HOTPLUG_DOWN_FROZEN;
		*transaction = minted;
		ret = 0;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	mutex_unlock(&a72_transition_lock);
	return ret;
}

int mt6797_a72_hotplug_validate_down(
	struct mt6797_a72_hotplug_transaction *transaction,
	int tasks_frozen, enum cpuhp_state target,
	bool cpu8_online, bool cpu9_online)
{
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction)
		return -EINVAL;
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (!tasks_frozen && target == CPUHP_OFFLINE &&
	    a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
	    a72_owner.phase == MT6797_A72_PHASE_IDLE &&
	    a72_owner.hotplug_phase == MT6797_A72_HOTPLUG_DOWN_FROZEN &&
	    mt6797_a72_hotplug_active_locked(
		    transaction, MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN) &&
	    a72_owner.controller == current &&
	    a72_owner.controller_cookie ==
		    a72_owner.hotplug_active.identity.cookie &&
	    a72_owner.members == (BIT(0) | BIT(1)) &&
	    cpu8_online && cpu9_online) {
		a72_owner.hotplug_phase =
			MT6797_A72_HOTPLUG_DOWN_VALIDATED;
		*transaction = a72_owner.hotplug_active;
		ret = 0;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	return ret;
}

int mt6797_a72_hotplug_commit_off(unsigned int cpu)
{
	unsigned long flags;
	int ret = -EPERM;

	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (cpu == 9 &&
	    a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
	    a72_owner.hotplug_phase == MT6797_A72_HOTPLUG_DOWN_VALIDATED &&
	    mt6797_a72_hotplug_active_locked(
		    NULL, MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN) &&
	    a72_owner.hotplug_active.budgets.cpu_off ==
		    MT6797_A72_BUDGET_AVAILABLE &&
	    !a72_owner.hotplug_active.off_committed) {
		a72_owner.hotplug_active.budgets.cpu_off =
			MT6797_A72_BUDGET_CONSUMED;
		a72_owner.hotplug_active.off_committed = 1;
		a72_owner.hotplug_phase = MT6797_A72_HOTPLUG_OFF_COMMITTED;
		ret = 0;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	return ret;
}

static bool
mt6797_a72_hotplug_off_proof_valid_locked(
	const struct mt6797_a72_cpu9_off_proof *proof)
{
	const struct mt6797_a72_hotplug_transaction *active =
		&a72_owner.hotplug_active;

	return proof && proof->abi == MT6797_A72_CPU9_OFF_PROOF_ABI &&
		proof->valid == 1 && proof->affinity_attempted == 1 &&
		proof->affinity_level == MT6797_A72_AFFINITY_LEVEL0 &&
		proof->affinity_state == MT6797_A72_AFFINITY_STATE_OFF &&
		proof->cpu9_per_core_off == 1 && proof->cpu8_responsive == 1 &&
		proof->shared_state_unchanged == 1 &&
		proof->members_before == (BIT(0) | BIT(1)) &&
		proof->online_mask_after == BIT(0) &&
		!memcmp(&proof->provider_identity, &active->provider_identity,
			sizeof(proof->provider_identity)) &&
		proof->transaction_generation == active->identity.generation &&
		proof->transaction_cookie == active->identity.cookie;
}

int mt6797_a72_hotplug_prove_off(
	struct mt6797_a72_hotplug_transaction *transaction,
	const struct mt6797_a72_cpu9_off_proof *proof)
{
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction)
		return -EINVAL;
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
	    a72_owner.hotplug_phase == MT6797_A72_HOTPLUG_OFF_COMMITTED &&
	    mt6797_a72_hotplug_active_locked(
		    transaction, MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN) &&
	    a72_owner.hotplug_active.off_committed == 1 &&
	    a72_owner.hotplug_active.budgets.cpu_off ==
		    MT6797_A72_BUDGET_CONSUMED &&
	    a72_owner.hotplug_active.budgets.affinity ==
		    MT6797_A72_BUDGET_AVAILABLE) {
		a72_owner.hotplug_active.budgets.affinity =
			MT6797_A72_BUDGET_CONSUMED;
		if (!mt6797_a72_hotplug_off_proof_valid_locked(proof)) {
			mt6797_a72_hotplug_fault_locked(-EIO);
			ret = -EIO;
		} else {
			a72_owner.hotplug_active.off_proof = *proof;
			a72_owner.hotplug_active.off_proven = 1;
			a72_owner.hotplug_phase =
				MT6797_A72_HOTPLUG_OFF_PROVEN;
			*transaction = a72_owner.hotplug_active;
			ret = 0;
		}
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	return ret;
}

int mt6797_a72_hotplug_complete_down(
	struct mt6797_a72_hotplug_transaction *transaction,
	bool cpu8_online, bool cpu9_online)
{
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction)
		return -EINVAL;
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
	    a72_owner.phase == MT6797_A72_PHASE_IDLE &&
	    a72_owner.hotplug_phase == MT6797_A72_HOTPLUG_OFF_PROVEN &&
	    mt6797_a72_hotplug_active_locked(
		    transaction, MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN) &&
	    a72_owner.hotplug_active.off_committed == 1 &&
	    a72_owner.hotplug_active.off_proven == 1 &&
	    !a72_owner.hotplug_active.completed &&
	    a72_owner.members == (BIT(0) | BIT(1)) &&
	    cpu8_online && !cpu9_online) {
		a72_owner.hotplug_active.completed = 1;
		a72_owner.members = BIT(0);
		*transaction = a72_owner.hotplug_active;
		mt6797_a72_hotplug_retire_locked(
			0, MT6797_A72_HOTPLUG_OFFLINE);
		ret = 0;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	return ret;
}

int mt6797_a72_hotplug_fail_down(
	struct mt6797_a72_hotplug_transaction *transaction, int error)
{
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction || !error)
		return -EINVAL;
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (mt6797_a72_hotplug_active_locked(
		    transaction, MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN)) {
		switch (a72_owner.hotplug_phase) {
		case MT6797_A72_HOTPLUG_DOWN_FROZEN:
		case MT6797_A72_HOTPLUG_DOWN_VALIDATED:
			if (!a72_owner.hotplug_active.off_committed) {
				a72_owner.hotplug_active.failure_error = error;
				*transaction = a72_owner.hotplug_active;
				mt6797_a72_hotplug_retire_locked(
					0, MT6797_A72_HOTPLUG_REJECTED);
				ret = 0;
			}
			break;
		case MT6797_A72_HOTPLUG_OFF_COMMITTED:
		case MT6797_A72_HOTPLUG_OFF_PROVEN:
			mt6797_a72_hotplug_fault_locked(error);
			*transaction = a72_owner.hotplug_active;
			ret = 0;
			break;
		default:
			break;
		}
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	return ret;
}

int mt6797_a72_hotplug_prepare_restore(
	unsigned int cpu, enum cpuhp_state target,
	bool cpu8_online, bool cpu9_online,
	struct mt6797_a72_hotplug_transaction *transaction)
{
	struct mt6797_a72_hotplug_transaction minted = { };
	const struct mt6797_a72_hotplug_transaction *parent;
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction)
		return -EINVAL;
	memset(transaction, 0, sizeof(*transaction));
	if (cpu != 9 || target != CPUHP_ONLINE)
		return -EINVAL;

	mutex_lock(&a72_transition_lock);
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (a72_owner.health == MT6797_A72_OWNER_FAULTED) {
		ret = -ESHUTDOWN;
	} else if (a72_owner.health != MT6797_A72_OWNER_AVAILABLE ||
		   a72_owner.phase != MT6797_A72_PHASE_IDLE ||
		   a72_owner.hotplug_phase != MT6797_A72_HOTPLUG_OFFLINE ||
		   a72_owner.hotplug_active.valid ||
		   a72_owner.hotplug_retired_mask != BIT(0) ||
		   a72_owner.members != BIT(0) ||
		   a72_owner.provider_state != MT6797_A72_PROVIDER_HELD ||
		   !cpu8_online || cpu9_online || a72_owner.controller ||
		   !(a72_owner.attempts_available &
		     MT6797_A72_ATTEMPT_CPU9_RESTORE) ||
		   (a72_owner.attempts_consumed &
		    MT6797_A72_ATTEMPT_CPU9_RESTORE)) {
		ret = -EPERM;
	} else {
		parent = &a72_owner.hotplug_retired[0];
		if (!parent->valid || !parent->completed ||
		    !parent->off_committed || !parent->off_proven ||
		    parent->identity.operation !=
			    MT6797_A72_HOTPLUG_OPERATION_CPU9_DOWN ||
		    memcmp(&parent->provider_identity,
			   &a72_owner.provider_identity,
			   sizeof(parent->provider_identity))) {
			ret = -EPROTO;
		} else {
			minted.identity.abi = MT6797_A72_HOTPLUG_ABI;
			minted.identity.operation =
				MT6797_A72_HOTPLUG_OPERATION_CPU9_RESTORE;
			minted.identity.target_cpu = 9;
			minted.identity.cpuhp_target = CPUHP_ONLINE;
			minted.identity.target_mpidr = 0x201;
			minted.identity.generation =
				a72_owner.next_generation++;
			minted.identity.cookie = a72_owner.next_cookie++;
			minted.identity.parent_generation =
				parent->identity.generation;
			minted.identity.parent_cookie = parent->identity.cookie;
			minted.budgets.cpu_on =
				MT6797_A72_BUDGET_AVAILABLE;
			minted.provider_identity = a72_owner.provider_identity;
			minted.entry_members = BIT(0);
			minted.entry_online_mask = BIT(0);
			minted.valid = 1;
			a72_owner.attempts_available &=
				~MT6797_A72_ATTEMPT_CPU9_RESTORE;
			a72_owner.attempts_consumed |=
				MT6797_A72_ATTEMPT_CPU9_RESTORE;
			a72_owner.hotplug_active = minted;
			a72_owner.controller = current;
			a72_owner.controller_cookie = minted.identity.cookie;
			a72_owner.hotplug_phase =
				MT6797_A72_HOTPLUG_RESTORE_FROZEN;
			*transaction = minted;
			ret = 0;
		}
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	mutex_unlock(&a72_transition_lock);
	return ret;
}

int mt6797_a72_hotplug_begin_restore(
	struct mt6797_a72_hotplug_transaction *transaction,
	bool cpu8_online, bool cpu9_online)
{
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction)
		return -EINVAL;
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
	    a72_owner.hotplug_phase == MT6797_A72_HOTPLUG_RESTORE_FROZEN &&
	    mt6797_a72_hotplug_active_locked(
		    transaction, MT6797_A72_HOTPLUG_OPERATION_CPU9_RESTORE) &&
	    a72_owner.controller == current &&
	    a72_owner.controller_cookie ==
		    a72_owner.hotplug_active.identity.cookie &&
	    a72_owner.hotplug_active.budgets.cpu_on ==
		    MT6797_A72_BUDGET_AVAILABLE &&
	    a72_owner.members == BIT(0) && cpu8_online && !cpu9_online) {
		a72_owner.hotplug_active.budgets.cpu_on =
			MT6797_A72_BUDGET_CONSUMED;
		a72_owner.hotplug_phase =
			MT6797_A72_HOTPLUG_RESTORE_ON_ISSUED;
		*transaction = a72_owner.hotplug_active;
		ret = 0;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	return ret;
}

int mt6797_a72_hotplug_complete_restore(
	struct mt6797_a72_hotplug_transaction *transaction,
	bool cpu8_online, bool cpu9_online)
{
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction)
		return -EINVAL;
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if (a72_owner.health == MT6797_A72_OWNER_AVAILABLE &&
	    a72_owner.phase == MT6797_A72_PHASE_IDLE &&
	    a72_owner.hotplug_phase ==
		    MT6797_A72_HOTPLUG_RESTORE_ON_ISSUED &&
	    mt6797_a72_hotplug_active_locked(
		    transaction, MT6797_A72_HOTPLUG_OPERATION_CPU9_RESTORE) &&
	    a72_owner.hotplug_active.budgets.cpu_on ==
		    MT6797_A72_BUDGET_CONSUMED &&
	    a72_owner.members == BIT(0) && cpu8_online && cpu9_online) {
		a72_owner.hotplug_active.completed = 1;
		a72_owner.hotplug_active.restored = 1;
		a72_owner.members = BIT(0) | BIT(1);
		*transaction = a72_owner.hotplug_active;
		mt6797_a72_hotplug_retire_locked(
			1, MT6797_A72_HOTPLUG_RESTORED);
		ret = 0;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	return ret;
}

int mt6797_a72_hotplug_fail_restore(
	struct mt6797_a72_hotplug_transaction *transaction, int error)
{
	unsigned long flags;
	int ret = -EPERM;

	if (!transaction || !error)
		return -EINVAL;
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	if ((a72_owner.hotplug_phase ==
	     MT6797_A72_HOTPLUG_RESTORE_FROZEN ||
	     a72_owner.hotplug_phase ==
	     MT6797_A72_HOTPLUG_RESTORE_ON_ISSUED) &&
	    mt6797_a72_hotplug_active_locked(
		    transaction, MT6797_A72_HOTPLUG_OPERATION_CPU9_RESTORE)) {
		mt6797_a72_hotplug_fault_locked(error);
		*transaction = a72_owner.hotplug_active;
		ret = 0;
	}
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
	return ret;
}

void mt6797_a72_hotplug_snapshot(
	struct mt6797_a72_hotplug_snapshot *snapshot)
{
	unsigned long flags;

	if (!snapshot)
		return;
	memset(snapshot, 0, sizeof(*snapshot));
	raw_spin_lock_irqsave(&a72_state_lock, flags);
	snapshot->active = a72_owner.hotplug_active;
	memcpy(snapshot->retired, a72_owner.hotplug_retired,
	       sizeof(snapshot->retired));
	snapshot->abi = MT6797_A72_HOTPLUG_ABI;
	snapshot->phase = a72_owner.hotplug_phase;
	snapshot->retired_mask = a72_owner.hotplug_retired_mask;
	snapshot->members = a72_owner.members;
	snapshot->attempts_consumed = a72_owner.attempts_consumed;
	snapshot->owner_health = a72_owner.health;
	snapshot->controller_present = !!a72_owner.controller;
	raw_spin_unlock_irqrestore(&a72_state_lock, flags);
}

#ifdef CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED
int mt6797_a72_membership_test_preflight_cpu9''',
    )


if __name__ == "__main__":
    main()
