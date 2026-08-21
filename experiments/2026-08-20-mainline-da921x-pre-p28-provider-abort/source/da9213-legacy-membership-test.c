// SPDX-License-Identifier: GPL-2.0-only
/* Hardware-free integration coverage for the pre-P28 provider abort. */

#include <kunit/test.h>
#include <linux/errno.h>
#include <linux/i2c.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/string.h>

#include <asm/memory.h>
#include <asm/mt6797_a72_membership.h>
#include <asm/smp.h>

#include "da9213-legacy-provider-contract.h"

#define DA9213_MEMBERSHIP_TEST_ADDRESS	0x2a
#define DA9213_MEMBERSHIP_TEST_RETRIES	3
#define DA9213_MEMBERSHIP_MUTATIONS	14
#define DA9213_MEMBERSHIP_P29_MUTATIONS	9

struct da9213_membership_fake {
	struct i2c_adapter adapter;
	u8 registers[256];
	unsigned int lock_calls;
	unsigned int unlock_calls;
	unsigned int operation_calls;
	unsigned int total_calls;
	unsigned int delay_calls;
	unsigned int fail_ordinal;
	unsigned int short_ordinal;
	unsigned int write_count;
	u8 write_registers[2];
	u8 write_values[2];
	bool locked;
	bool transfer_unlocked;
	bool retry_nonzero;
};

struct da9213_membership_synthetic {
	unsigned int acquire_mutation;
	unsigned int release_mutation;
	unsigned int acquire_calls;
	unsigned int release_calls;
	u32 release_entry_provider_state;
	u8 release_entry_abort_budget;
	bool release_entry_handle_exact;
	struct mt6797_a72_provider_handle handle;
};

static struct da9213_membership_fake *active_fake;
static struct da9213_legacy_provider_endpoint *registered_endpoint;
static struct da9213_membership_synthetic *registered_synthetic;

static void da9213_membership_lock(struct i2c_adapter *adapter,
				   unsigned int flags)
{
	(void)adapter;
	(void)flags;
	active_fake->lock_calls++;
	active_fake->locked = true;
}

static int da9213_membership_trylock(struct i2c_adapter *adapter,
				     unsigned int flags)
{
	(void)adapter;
	(void)flags;
	return 0;
}

static void da9213_membership_unlock(struct i2c_adapter *adapter,
				     unsigned int flags)
{
	(void)adapter;
	(void)flags;
	active_fake->unlock_calls++;
	active_fake->locked = false;
}

static const struct i2c_lock_operations da9213_membership_lock_ops = {
	.lock_bus = da9213_membership_lock,
	.trylock_bus = da9213_membership_trylock,
	.unlock_bus = da9213_membership_unlock,
};

static int da9213_membership_transfer(struct i2c_adapter *adapter,
				      struct i2c_msg *messages, int count)
{
	struct da9213_membership_fake *fake = active_fake;
	u8 reg;

	if (!fake || adapter != &fake->adapter)
		return -EINVAL;
	fake->operation_calls++;
	fake->total_calls++;
	if (!fake->locked)
		fake->transfer_unlocked = true;
	if (adapter->retries)
		fake->retry_nonzero = true;
	if (fake->fail_ordinal == fake->operation_calls)
		return -EIO;
	if (fake->short_ordinal == fake->operation_calls)
		return count == 2 ? 1 : 0;

	if (count == 2 && messages[0].addr == DA9213_MEMBERSHIP_TEST_ADDRESS &&
	    messages[1].addr == DA9213_MEMBERSHIP_TEST_ADDRESS &&
	    !messages[0].flags && messages[1].flags == I2C_M_RD &&
	    messages[0].len == 1 && messages[1].len == 1 &&
	    messages[0].buf && messages[1].buf) {
		reg = messages[0].buf[0];
		messages[1].buf[0] = fake->registers[reg];
		return 2;
	}

	if (count == 1 && messages[0].addr == DA9213_MEMBERSHIP_TEST_ADDRESS &&
	    !messages[0].flags && messages[0].len == 2 && messages[0].buf) {
		reg = messages[0].buf[0];
		if (fake->write_count < ARRAY_SIZE(fake->write_registers)) {
			fake->write_registers[fake->write_count] = reg;
			fake->write_values[fake->write_count] = messages[0].buf[1];
		}
		fake->write_count++;
		fake->registers[reg] = messages[0].buf[1];
		return 1;
	}

	return -EPROTO;
}

static void da9213_membership_delay(unsigned long minimum,
				    unsigned long maximum)
{
	(void)minimum;
	(void)maximum;
	active_fake->delay_calls++;
}

static const struct da9213_legacy_provider_transport_ops
da9213_membership_transport_ops = {
	.transfer = da9213_membership_transfer,
	.delay = da9213_membership_delay,
};

static void da9213_membership_fake_init(struct da9213_membership_fake *fake)
{
	memset(fake, 0, sizeof(*fake));
	fake->adapter.lock_ops = &da9213_membership_lock_ops;
	fake->adapter.retries = DA9213_MEMBERSHIP_TEST_RETRIES;
	fake->registers[0x56] = 0x7b;
	fake->registers[0x51] = 0xc1;
	fake->registers[0x5e] = 0x00;
	fake->registers[0xd9] = 0x46;
	fake->registers[0xda] = 0x46;
	active_fake = fake;
}

static struct mt6797_a72_entry_snapshot da9213_membership_entry(void)
{
	return (struct mt6797_a72_entry_snapshot) {
		.cpuhp_state_cpu8 = CPUHP_OFFLINE,
		.cpuhp_state_cpu9 = CPUHP_OFFLINE,
		.observer_window = MT6797_A72_OBSERVER_WINDOW_OPEN,
		.flags = MT6797_A72_ENTRY_FLAGS_MASK,
		.cpu8_mpidr = 0x200,
		.cpu9_mpidr = 0x201,
	};
}

static struct mt6797_a72_a36_prestate da9213_membership_prestate(void)
{
	return (struct mt6797_a72_a36_prestate) {
		.abi = MT6797_A72_A36_PRESTATE_ABI,
		.operation = ARM64_LATE_CPU_STARTUP_OP_CPU8_UP,
		.observer_window = MT6797_A72_OBSERVER_WINDOW_OPEN,
		.call_shape = MT6797_A72_A36_CALL_SHAPE_TWO_ARG,
		.da921x_page = MT6797_A72_A36_DA921X_PAGE,
		.buckb_vsel = MT6797_A72_A36_BUCKB_VSEL,
		.spm_218 = MT6797_A72_A36_SPM_218,
		.spm_290 = MT6797_A72_A36_SPM_290,
		.secure_sentinels_stable = 1,
		.protected_clock_valid = 1,
		.pstore_console_available = 1,
		.watchdog_owned = 1,
		.target_mpidr = 0x200,
		.secondary_entry_pa = __pa_symbol(secondary_entry),
		.generation = 1,
		.cookie = 0xa7200001,
	};
}

static struct arm64_late_cpu_ready_token da9213_membership_ready(void)
{
	struct arm64_late_cpu_ready_token ready = {
		.abi = ARM64_LATE_CPU_PLAN_ABI,
		.plan_identity = { 1, 2, 3, 4 },
		.source_parent_identity = { 5, 6, 7, 8 },
		.config_input_identity = { 9, 10, 11, 12 },
		.evidence_identity = { 13, 14, 15, 16 },
		.target_cpu = { 8, 9 },
		.expected_target_mpidr = { 0x200, 0x201 },
		.observed_target_mpidr = { 0x200, 0x201 },
	};

	strscpy(ready.profile_id, "mt6797-a53-a72-a41-v7",
		sizeof(ready.profile_id));
	cpumask_set_cpu(8, &ready.target_cpus);
	cpumask_set_cpu(9, &ready.target_cpus);
	return ready;
}

static int
da9213_membership_seed_p27(struct mt6797_a72_transaction *transaction)
{
	struct mt6797_a72_entry_snapshot entry = da9213_membership_entry();
	struct mt6797_a72_a36_prestate prestate = da9213_membership_prestate();
	struct arm64_late_cpu_ready_token ready = da9213_membership_ready();
	struct mt6797_a72_p27_preparation preparation;
	int ret;

	mt6797_a72_membership_test_seed_available();
	ret = mt6797_a72_membership_begin_up(8, CPUHP_ONLINE,
					     MT6797_A72_ATTEMPT_CPU8_UP,
					     &entry, &ready, &prestate,
					     transaction);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_publish_up(transaction);
	if (ret)
		return ret;
	ret = mt6797_a72_membership_begin_p27_preparation(transaction);
	if (ret)
		return ret;
	preparation = (struct mt6797_a72_p27_preparation) {
		.abi = MT6797_A72_P27_PREPARATION_ABI,
		.operation = transaction->identity.operation,
		.stage = MT6797_A72_P27_STAGE_COMPLETE,
		.effect_mask = MT6797_A72_P27_EFFECT_MASK,
		.generation = transaction->identity.generation,
		.cookie = transaction->identity.cookie,
	};
	return mt6797_a72_membership_complete_p27_preparation(transaction,
							     &preparation);
}

static struct mt6797_a72_p29_rollback_proof
da9213_membership_p29(const struct mt6797_a72_transaction *transaction)
{
	return (struct mt6797_a72_p29_rollback_proof) {
		.abi = MT6797_A72_P29_ROLLBACK_ABI,
		.operation = transaction->identity.operation,
		.restored_effect_mask = MT6797_A72_P27_EFFECT_MASK,
		.transaction_generation = transaction->identity.generation,
		.transaction_cookie = transaction->identity.cookie,
	};
}

static int
da9213_membership_register_endpoint(struct da9213_legacy_provider_endpoint *endpoint,
				    struct da9213_membership_fake *fake)
{
	int ret;

	ret = da9213_legacy_provider_test_register(endpoint, &fake->adapter,
						   DA9213_MEMBERSHIP_TEST_ADDRESS,
						   &da9213_membership_transport_ops);
	if (!ret)
		registered_endpoint = endpoint;
	return ret;
}

static void da9213_membership_unregister_endpoint(void)
{
	if (registered_endpoint)
		da9213_legacy_provider_test_unregister(registered_endpoint);
	registered_endpoint = NULL;
}

static void
da9213_membership_mutate_response(struct mt6797_a72_provider_response *response,
				  unsigned int mutation)
{
	switch (mutation) {
	case 1:
		response->abi++;
		break;
	case 2:
		response->returned = 0;
		break;
	case 3:
		response->vote_requested = 0;
		break;
	case 4:
		response->provider_mutated = 0;
		break;
	case 5:
		response->rail_mutated = 0;
		break;
	case 6:
		response->settle_us++;
		break;
	case 7:
		response->da921x_page++;
		break;
	case 8:
		response->buckb_enabled ^= 1;
		break;
	case 9:
		response->buckb_vsel++;
		break;
	case 10:
		response->origin++;
		break;
	case 11:
		response->reserved = 1;
		break;
	case 12:
		response->origin_generation++;
		break;
	case 13:
		response->held_handle.generation++;
		break;
	case 14:
		response->held_handle.cookie++;
		break;
	default:
		break;
	}
}

static int
da9213_membership_synthetic_acquire(void *context,
				    const struct mt6797_a72_provider_request *request,
				    struct mt6797_a72_provider_response *response)
{
	struct da9213_membership_synthetic *synthetic = context;

	synthetic->acquire_calls++;
	synthetic->handle.generation = request->transaction_generation;
	synthetic->handle.cookie = request->transaction_cookie;
	*response = (struct mt6797_a72_provider_response) {
		.abi = MT6797_A72_PROVIDER_CALL_ABI,
		.returned = 1,
		.vote_requested = 1,
		.provider_mutated = 1,
		.rail_mutated = 1,
		.settle_us = MT6797_A72_PROVIDER_CALL_SETTLE_US,
		.da921x_page = MT6797_A72_PROVIDER_CALL_DA921X_PAGE,
		.buckb_enabled = 1,
		.buckb_vsel = MT6797_A72_PROVIDER_CALL_BUCKB_VSEL,
		.origin = MT6797_A72_PROVIDER_ORIGIN_M01,
		.origin_generation = request->transaction_generation,
		.held_handle = synthetic->handle,
	};
	da9213_membership_mutate_response(response, synthetic->acquire_mutation);
	return 0;
}

static int
da9213_membership_synthetic_release(void *context,
				    const struct mt6797_a72_provider_handle *handle,
				    struct mt6797_a72_provider_response *response)
{
	struct da9213_membership_synthetic *synthetic = context;
	struct mt6797_a72_owner_snapshot snapshot;

	synthetic->release_calls++;
	mt6797_a72_membership_snapshot(&snapshot);
	synthetic->release_entry_provider_state = snapshot.provider_state;
	synthetic->release_entry_abort_budget =
		snapshot.active.budgets.provider_abort;
	synthetic->release_entry_handle_exact =
		snapshot.provider_identity.generation == handle->generation &&
		snapshot.provider_identity.cookie == handle->cookie &&
		snapshot.active.provider_identity.generation == handle->generation &&
		snapshot.active.provider_identity.cookie == handle->cookie;
	*response = (struct mt6797_a72_provider_response) {
		.abi = MT6797_A72_PROVIDER_CALL_ABI,
		.returned = 1,
		.vote_requested = 1,
		.provider_mutated = 1,
		.rail_mutated = 1,
		.settle_us = MT6797_A72_PROVIDER_CALL_SETTLE_US,
		.da921x_page = MT6797_A72_PROVIDER_CALL_DA921X_PAGE,
		.buckb_enabled = 0,
		.buckb_vsel = MT6797_A72_PROVIDER_CALL_BUCKB_VSEL,
		.origin = MT6797_A72_PROVIDER_ORIGIN_M01,
		.origin_generation = handle->generation,
		.held_handle = *handle,
	};
	da9213_membership_mutate_response(response, synthetic->release_mutation);
	return 0;
}

static const struct mt6797_a72_provider_ops
da9213_membership_synthetic_ops = {
	.acquire = da9213_membership_synthetic_acquire,
	.release = da9213_membership_synthetic_release,
};

static int
da9213_membership_register_synthetic(struct da9213_membership_synthetic *synthetic)
{
	int ret;

	ret = mt6797_a72_provider_register(&da9213_membership_synthetic_ops, synthetic);
	if (!ret)
		registered_synthetic = synthetic;
	return ret;
}

static void da9213_membership_unregister_synthetic(void)
{
	if (registered_synthetic)
		mt6797_a72_provider_unregister(&da9213_membership_synthetic_ops,
					       registered_synthetic);
	registered_synthetic = NULL;
}

static void expect_fault(struct kunit *test, u32 cause)
{
	struct mt6797_a72_owner_snapshot snapshot;

	mt6797_a72_membership_snapshot(&snapshot);
	KUNIT_EXPECT_EQ(test, snapshot.health,
			(u32)MT6797_A72_OWNER_FAULTED);
	KUNIT_EXPECT_EQ(test, snapshot.phase, (u32)MT6797_A72_PHASE_FAULT);
	KUNIT_EXPECT_EQ(test, snapshot.provider_state,
			(u32)MT6797_A72_PROVIDER_FAULT_UNKNOWN);
	KUNIT_EXPECT_TRUE(test, snapshot.first_fault.valid);
	KUNIT_EXPECT_EQ(test, snapshot.first_fault.cause, cause);
	KUNIT_EXPECT_EQ(test, snapshot.active.budgets.provider_acquire,
			(u8)MT6797_A72_BUDGET_CONSUMED);
}

static void da9213_membership_positive_abort_success(struct kunit *test)
{
	struct da9213_legacy_provider_endpoint endpoint;
	struct da9213_membership_fake fake;
	struct mt6797_a72_provider_response response;
	struct mt6797_a72_p29_rollback_proof rollback;
	struct mt6797_a72_owner_snapshot snapshot;
	struct mt6797_a72_transaction transaction;
	int ret;

	da9213_membership_fake_init(&fake);
	ret = da9213_membership_register_endpoint(&endpoint, &fake);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = da9213_membership_seed_p27(&transaction);
	KUNIT_ASSERT_EQ(test, ret, 0);
	ret = mt6797_a72_membership_run_provider_acquire(&transaction, &response);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_EQ(test, transaction.budgets.provider_abort,
			(u8)MT6797_A72_BUDGET_AVAILABLE);
	KUNIT_EXPECT_EQ(test, fake.registers[0x5e], (u8)0x01);
	ret = mt6797_a72_membership_run_provider_abort(&transaction, &response);
	KUNIT_ASSERT_EQ(test, ret, 0);
	KUNIT_EXPECT_TRUE(test, transaction.provider_abort_valid);
	KUNIT_EXPECT_EQ(test, transaction.budgets.provider_abort,
			(u8)MT6797_A72_BUDGET_CONSUMED);
	KUNIT_EXPECT_EQ(test, fake.registers[0x5e], (u8)0x00);
	KUNIT_EXPECT_EQ(test, fake.write_count, 2U);
	KUNIT_EXPECT_EQ(test, fake.write_values[0], (u8)0x01);
	KUNIT_EXPECT_EQ(test, fake.write_values[1], (u8)0x00);
	KUNIT_EXPECT_EQ(test, fake.lock_calls, 2U);
	KUNIT_EXPECT_EQ(test, fake.unlock_calls, 2U);
	KUNIT_EXPECT_FALSE(test, fake.transfer_unlocked);
	KUNIT_EXPECT_FALSE(test, fake.retry_nonzero);
	KUNIT_EXPECT_EQ(test, fake.adapter.retries,
			DA9213_MEMBERSHIP_TEST_RETRIES);
	KUNIT_EXPECT_EQ(test, transaction.provider_identity.generation, (u64)0);
	KUNIT_EXPECT_EQ(test, transaction.provider_identity.cookie, (u64)0);
	mt6797_a72_membership_snapshot(&snapshot);
	KUNIT_EXPECT_EQ(test, snapshot.provider_state,
			(u32)MT6797_A72_PROVIDER_NONE);
	KUNIT_EXPECT_EQ(test, snapshot.provider_identity.generation, (u64)0);
	KUNIT_EXPECT_EQ(test, snapshot.provider_identity.cookie, (u64)0);
	KUNIT_EXPECT_EQ(test,
			snapshot.active.provider_identity.generation, (u64)0);
	KUNIT_EXPECT_EQ(test, snapshot.active.provider_identity.cookie, (u64)0);
	rollback = da9213_membership_p29(&transaction);
	ret = mt6797_a72_membership_complete_p29_rollback(&transaction,
							  &rollback);
	KUNIT_ASSERT_EQ(test, ret, 0);
	mt6797_a72_membership_snapshot(&snapshot);
	KUNIT_EXPECT_EQ(test, snapshot.phase,
			(u32)MT6797_A72_PHASE_REJECTED);
	KUNIT_EXPECT_EQ(test, snapshot.provider_state,
			(u32)MT6797_A72_PROVIDER_NONE);
	KUNIT_EXPECT_EQ(test, snapshot.retired_mask, (u32)BIT(0));
	KUNIT_EXPECT_EQ(test,
			snapshot.retired[0].p28_preparation.stage,
			(u32)MT6797_A72_P28_STAGE_NONE);
	KUNIT_EXPECT_EQ(test, snapshot.retired[0].budgets.cpu_on,
			(u8)MT6797_A72_BUDGET_AVAILABLE);
	da9213_membership_unregister_endpoint();
}

static void da9213_membership_acquire_transport_faults(struct kunit *test)
{
	unsigned int mode;
	unsigned int ordinal;

	for (mode = 0; mode < 2; mode++) {
		for (ordinal = 1; ordinal <= DA9213_LEGACY_PROVIDER_ACTIONS;
		     ordinal++) {
			struct da9213_legacy_provider_endpoint endpoint;
			struct da9213_membership_fake fake;
			struct mt6797_a72_provider_response response;
			struct mt6797_a72_transaction transaction;
			int ret;

			da9213_membership_fake_init(&fake);
			if (mode)
				fake.short_ordinal = ordinal;
			else
				fake.fail_ordinal = ordinal;
			ret = da9213_membership_register_endpoint(&endpoint, &fake);
			KUNIT_ASSERT_EQ(test, ret, 0);
			ret = da9213_membership_seed_p27(&transaction);
			KUNIT_ASSERT_EQ(test, ret, 0);
			ret = mt6797_a72_membership_run_provider_acquire(&transaction, &response);
			KUNIT_EXPECT_LT_MSG(test, ret, 0, "mode=%u ordinal=%u",
					    mode, ordinal);
			KUNIT_EXPECT_EQ(test, fake.operation_calls, ordinal);
			expect_fault(test, MT6797_A72_FAULT_PROVIDER_ACQUIRE_RETURN);
			ret = mt6797_a72_membership_run_provider_acquire(&transaction, &response);
			KUNIT_EXPECT_EQ(test, ret, -EPERM);
			KUNIT_EXPECT_EQ(test, fake.operation_calls, ordinal);
			da9213_membership_unregister_endpoint();
		}
	}
}

static void da9213_membership_acquire_malformed_success(struct kunit *test)
{
	unsigned int mutation;

	for (mutation = 1; mutation <= DA9213_MEMBERSHIP_MUTATIONS; mutation++) {
		struct da9213_membership_synthetic synthetic = {
			.acquire_mutation = mutation,
		};
		struct mt6797_a72_provider_response response;
		struct mt6797_a72_transaction transaction;
		int ret;

		ret = da9213_membership_register_synthetic(&synthetic);
		KUNIT_ASSERT_EQ(test, ret, 0);
		ret = da9213_membership_seed_p27(&transaction);
		KUNIT_ASSERT_EQ(test, ret, 0);
		ret = mt6797_a72_membership_run_provider_acquire(&transaction,
								 &response);
		KUNIT_EXPECT_EQ_MSG(test, ret, -EPROTO, "mutation=%u", mutation);
		KUNIT_EXPECT_EQ(test, synthetic.acquire_calls, 1U);
		expect_fault(test, MT6797_A72_FAULT_PROVIDER_ACQUIRE_RETURN);
		ret = mt6797_a72_membership_run_provider_acquire(&transaction,
								 &response);
		KUNIT_EXPECT_EQ(test, ret, -EPERM);
		KUNIT_EXPECT_EQ(test, synthetic.acquire_calls, 1U);
		da9213_membership_unregister_synthetic();
	}
}

static void da9213_membership_release_transport_faults(struct kunit *test)
{
	unsigned int mode;
	unsigned int ordinal;

	for (mode = 0; mode < 2; mode++) {
		for (ordinal = 1; ordinal <= DA9213_LEGACY_PROVIDER_ACTIONS;
		     ordinal++) {
			struct da9213_legacy_provider_endpoint endpoint;
			struct da9213_membership_fake fake;
			struct mt6797_a72_provider_response response;
			struct mt6797_a72_owner_snapshot snapshot;
			struct mt6797_a72_transaction transaction;
			u64 held_generation;
			int ret;

			da9213_membership_fake_init(&fake);
			ret = da9213_membership_register_endpoint(&endpoint, &fake);
			KUNIT_ASSERT_EQ(test, ret, 0);
			ret = da9213_membership_seed_p27(&transaction);
			KUNIT_ASSERT_EQ(test, ret, 0);
			ret = mt6797_a72_membership_run_provider_acquire(&transaction, &response);
			KUNIT_ASSERT_EQ(test, ret, 0);
			held_generation = transaction.provider_identity.generation;
			fake.operation_calls = 0;
			if (mode)
				fake.short_ordinal = ordinal;
			else
				fake.fail_ordinal = ordinal;
			ret = mt6797_a72_membership_run_provider_abort(&transaction, &response);
			KUNIT_EXPECT_LT_MSG(test, ret, 0, "mode=%u ordinal=%u",
					    mode, ordinal);
			KUNIT_EXPECT_EQ(test, fake.operation_calls, ordinal);
			expect_fault(test, MT6797_A72_FAULT_PROVIDER_RELEASE_RETURN);
			mt6797_a72_membership_snapshot(&snapshot);
			KUNIT_EXPECT_EQ(test, snapshot.provider_identity.generation,
					held_generation);
			KUNIT_EXPECT_EQ(test, snapshot.active.budgets.provider_abort,
					(u8)MT6797_A72_BUDGET_CONSUMED);
			ret = mt6797_a72_membership_run_provider_abort(&transaction, &response);
			KUNIT_EXPECT_EQ(test, ret, -EPERM);
			KUNIT_EXPECT_EQ(test, fake.operation_calls, ordinal);
			da9213_membership_unregister_endpoint();
		}
	}
}

static void da9213_membership_release_malformed_success(struct kunit *test)
{
	unsigned int mutation;

	for (mutation = 1; mutation <= DA9213_MEMBERSHIP_MUTATIONS; mutation++) {
		struct da9213_membership_synthetic synthetic = {
			.release_mutation = mutation,
		};
		struct mt6797_a72_provider_response response;
		struct mt6797_a72_transaction transaction;
		int ret;

		ret = da9213_membership_register_synthetic(&synthetic);
		KUNIT_ASSERT_EQ(test, ret, 0);
		ret = da9213_membership_seed_p27(&transaction);
		KUNIT_ASSERT_EQ(test, ret, 0);
		ret = mt6797_a72_membership_run_provider_acquire(&transaction, &response);
		KUNIT_ASSERT_EQ(test, ret, 0);
		ret = mt6797_a72_membership_run_provider_abort(&transaction, &response);
		KUNIT_EXPECT_LT_MSG(test, ret, 0, "mutation=%u", mutation);
		KUNIT_EXPECT_EQ(test, synthetic.release_calls, 1U);
		KUNIT_EXPECT_EQ(test, synthetic.release_entry_provider_state,
				(u32)MT6797_A72_PROVIDER_RELEASE_INFLIGHT);
		KUNIT_EXPECT_EQ(test, synthetic.release_entry_abort_budget,
				(u8)MT6797_A72_BUDGET_CONSUMED);
		KUNIT_EXPECT_TRUE(test, synthetic.release_entry_handle_exact);
		expect_fault(test, MT6797_A72_FAULT_PROVIDER_RELEASE_RETURN);
		ret = mt6797_a72_membership_run_provider_abort(&transaction,
							       &response);
		KUNIT_EXPECT_EQ(test, ret, -EPERM);
		KUNIT_EXPECT_EQ(test, synthetic.release_calls, 1U);
		da9213_membership_unregister_synthetic();
	}
}

static void
da9213_membership_mutate_p29(struct mt6797_a72_p29_rollback_proof *rollback,
			     unsigned int mutation)
{
	switch (mutation) {
	case 1:
		rollback->abi++;
		break;
	case 2:
		rollback->operation++;
		break;
	case 3:
		rollback->restored_effect_mask ^=
			MT6797_A72_P27_BPLL_ORDER_READ;
		break;
	case 4:
		rollback->residual_effect_mask = 1;
		break;
	case 5:
		rollback->p28_started = 1;
		break;
	case 6:
		rollback->cpu_on_issued = 1;
		break;
	case 7:
		rollback->reserved = 1;
		break;
	case 8:
		rollback->transaction_generation++;
		break;
	case 9:
		rollback->transaction_cookie++;
		break;
	default:
		break;
	}
}

static void da9213_membership_abort_guards_and_p29(struct kunit *test)
{
	unsigned int mutation;

	for (mutation = 1; mutation <= DA9213_MEMBERSHIP_P29_MUTATIONS;
	     mutation++) {
		struct da9213_legacy_provider_endpoint endpoint;
		struct da9213_membership_fake fake;
		struct mt6797_a72_provider_response response;
		struct mt6797_a72_p29_rollback_proof rollback;
		struct mt6797_a72_transaction stale;
		struct mt6797_a72_transaction transaction;
		unsigned int calls;
		int ret;

		da9213_membership_fake_init(&fake);
		ret = da9213_membership_register_endpoint(&endpoint, &fake);
		KUNIT_ASSERT_EQ(test, ret, 0);
		ret = da9213_membership_seed_p27(&transaction);
		KUNIT_ASSERT_EQ(test, ret, 0);
		ret = mt6797_a72_membership_run_provider_acquire(&transaction, &response);
		KUNIT_ASSERT_EQ(test, ret, 0);
		stale = transaction;
		stale.provider_identity.cookie++;
		calls = fake.total_calls;
		ret = mt6797_a72_membership_run_provider_abort(&stale, &response);
		KUNIT_EXPECT_EQ(test, ret, -EPERM);
		KUNIT_EXPECT_EQ(test, fake.total_calls, calls);
		ret = mt6797_a72_membership_run_provider_abort(&transaction, &response);
		KUNIT_ASSERT_EQ(test, ret, 0);
		calls = fake.total_calls;
		ret = mt6797_a72_membership_run_provider_abort(&transaction, &response);
		KUNIT_EXPECT_EQ(test, ret, -EPERM);
		KUNIT_EXPECT_EQ(test, fake.total_calls, calls);
		rollback = da9213_membership_p29(&transaction);
		da9213_membership_mutate_p29(&rollback, mutation);
		ret = mt6797_a72_membership_complete_p29_rollback(&transaction,
								  &rollback);
		KUNIT_EXPECT_EQ_MSG(test, ret, -EPERM, "mutation=%u", mutation);
		rollback = da9213_membership_p29(&transaction);
		ret = mt6797_a72_membership_complete_p29_rollback(&transaction, &rollback);
		KUNIT_EXPECT_EQ(test, ret, 0);
		da9213_membership_unregister_endpoint();
	}
}

static int da9213_membership_test_init(struct kunit *test)
{
	(void)test;
	da9213_membership_unregister_endpoint();
	da9213_membership_unregister_synthetic();
	active_fake = NULL;
	mt6797_a72_membership_test_reset();
	return 0;
}

static void da9213_membership_test_exit(struct kunit *test)
{
	(void)test;
	da9213_membership_unregister_endpoint();
	da9213_membership_unregister_synthetic();
	active_fake = NULL;
	mt6797_a72_membership_test_reset();
}

static struct kunit_case da9213_membership_test_cases[] = {
	KUNIT_CASE(da9213_membership_positive_abort_success),
	KUNIT_CASE(da9213_membership_acquire_transport_faults),
	KUNIT_CASE(da9213_membership_acquire_malformed_success),
	KUNIT_CASE(da9213_membership_release_transport_faults),
	KUNIT_CASE(da9213_membership_release_malformed_success),
	KUNIT_CASE(da9213_membership_abort_guards_and_p29),
	{ }
};

static struct kunit_suite da9213_membership_test_suite = {
	.name = "da9213-legacy-membership-provider",
	.init = da9213_membership_test_init,
	.exit = da9213_membership_test_exit,
	.test_cases = da9213_membership_test_cases,
};

kunit_test_suite(da9213_membership_test_suite);

MODULE_LICENSE("GPL");
