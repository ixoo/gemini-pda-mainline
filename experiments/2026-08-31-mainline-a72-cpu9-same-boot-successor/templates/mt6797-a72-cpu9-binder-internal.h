/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_A72_CPU9_BINDER_INTERNAL_H
#define __MT6797_A72_CPU9_BINDER_INTERNAL_H

#include <linux/atomic.h>
#include <linux/cpuhotplug.h>
#include <linux/smp.h>
#include <linux/soc/mediatek/mt6797-a72-cpu9-binder.h>

#include <asm/mt6797_a72_membership.h>
#include <asm/mt6797_a72_p30e.h>

#include "mt6797-a72-cpu9-executor-internal.h"

struct mt6797_a72_cpu9_binder_backend_ops {
	int (*ledger_begin)(u64 cpu8_attempt_id, u64 cpu9_attempt_id);
	int (*ledger_checkpoint)(u64 cpu9_attempt_id, u32 phase, u32 stage,
				 u32 terminal);
	int (*membership_preflight)(void);
	int (*membership_claim)(struct mt6797_a72_transaction *transaction);
	int (*membership_reject)(struct mt6797_a72_transaction *transaction);
	int (*membership_begin_cpu_on)(struct mt6797_a72_transaction *transaction);
	int (*p30e_prepare)(const struct mt6797_a72_transaction *transaction,
			     struct mt6797_a72_p30e_handoff *handoff);
	int (*p30e_arm)(unsigned int cpu,
			 const struct mt6797_a72_p30e_handoff *handoff);
	int (*p30e_readback)(unsigned int cpu,
			      const struct mt6797_a72_p30e_handoff *handoff,
			      struct arm64_mt6797_a72_p30e_wire *copy);
	int (*membership_publish_success)(
		struct mt6797_a72_transaction *transaction);
	int (*membership_finalize_success)(
		struct mt6797_a72_transaction *transaction);
	bool (*cpu_online)(unsigned int cpu);
	int (*ipi_call)(unsigned int cpu, smp_call_func_t func, void *info,
			int wait);
};

struct mt6797_a72_cpu9_binder {
	const struct mt6797_a72_cpu9_binder_backend_ops *backend;
	struct mt6797_a72_cpu9_executor_controller executor;
	struct mt6797_a72_cpu9_executor_request request;
	struct mt6797_a72_cpu9_executor_result result;
	struct mt6797_a72_transaction transaction;
	struct mt6797_a72_p30e_handoff p30e_handoff;
	struct arm64_mt6797_a72_p30e_wire p30e_snapshot;
	mt6797_a72_cpu_boot_fn cpu_boot;
	atomic_t prepared;
	atomic_t boot_claimed;
	s32 p30e_prepare_ret;
	s32 p30e_arm_ret;
	s32 p30e_readback_ret;
	bool ledger_begun;
	bool p30e_prepare_attempted;
	bool p30e_arm_attempted;
	bool p30e_armed;
	bool p30e_readback_attempted;
};

#if IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER_KUNIT_TEST)
void mt6797_a72_cpu9_binder_test_init(
	struct mt6797_a72_cpu9_binder *binder,
	const struct mt6797_a72_cpu9_binder_backend_ops *backend);
int mt6797_a72_cpu9_binder_test_prepare(
	struct mt6797_a72_cpu9_binder *binder,
	const struct mt6797_a72_cpu9_executor_request *request);
int mt6797_a72_cpu9_binder_test_preflight(
	struct mt6797_a72_cpu9_binder *binder, unsigned int cpu,
	enum cpuhp_state target);
int mt6797_a72_cpu9_binder_test_validate(
	struct mt6797_a72_cpu9_binder *binder, unsigned int cpu,
	int tasks_frozen, enum cpuhp_state target);
int mt6797_a72_cpu9_binder_test_boot(
	struct mt6797_a72_cpu9_binder *binder, unsigned int cpu,
	mt6797_a72_cpu_boot_fn cpu_boot);
int mt6797_a72_cpu9_binder_test_secondary_complete(
	struct mt6797_a72_cpu9_binder *binder, unsigned int cpu);
int mt6797_a72_cpu9_binder_test_complete(
	struct mt6797_a72_cpu9_binder *binder, unsigned int cpu,
	enum cpuhp_state target);
int mt6797_a72_cpu9_binder_test_failure(
	struct mt6797_a72_cpu9_binder *binder, unsigned int cpu, int error,
	bool *publish_p32);
#endif

#endif /* __MT6797_A72_CPU9_BINDER_INTERNAL_H */
