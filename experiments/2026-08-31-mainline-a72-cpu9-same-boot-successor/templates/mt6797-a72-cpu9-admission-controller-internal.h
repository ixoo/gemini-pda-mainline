/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_A72_CPU9_ADMISSION_CONTROLLER_INTERNAL_H
#define __MT6797_A72_CPU9_ADMISSION_CONTROLLER_INTERNAL_H

#include <asm/mt6797_a72_membership.h>

#include <linux/atomic.h>
#include <linux/types.h>

#include "mt6797-a72-cpu9-executor-internal.h"

struct arm64_late_cpu_ready_token;

enum mt6797_a72_cpu9_admission_failure_stage {
	MT6797_A72_CPU9_ADMISSION_FAILURE_NONE,
	MT6797_A72_CPU9_ADMISSION_FAILURE_CPU8,
	MT6797_A72_CPU9_ADMISSION_FAILURE_CPU8_PROOF,
	MT6797_A72_CPU9_ADMISSION_FAILURE_READY_TOKEN,
	MT6797_A72_CPU9_ADMISSION_FAILURE_DERIVE,
	MT6797_A72_CPU9_ADMISSION_FAILURE_PUBLISH,
	MT6797_A72_CPU9_ADMISSION_FAILURE_PREPARE,
	MT6797_A72_CPU9_ADMISSION_FAILURE_CPU9_REQUEST,
};

struct mt6797_a72_cpu9_admission_cpu8_proof {
	u64 attempt_id;
	u32 cpu_requests;
	bool lifecycle_terminal;
	bool terminal_exact;
	bool membership_published;
	bool p27_retained;
	bool provider_retained;
	bool cpu8_online;
	bool cpu9_online;
};

struct mt6797_a72_cpu9_admission_ops {
	int (*run_cpu8)(void *context);
	int (*cpu8_proof)(void *context,
			  struct mt6797_a72_cpu9_admission_cpu8_proof *proof);
	const struct arm64_late_cpu_ready_token *(*ready_token)(void *context);
	int (*derive_cpu9)(void *context,
			   const struct arm64_late_cpu_ready_token *ready,
			   struct mt6797_a72_transaction *transaction,
			   u32 *derive_stage);
	int (*publish_cpu9)(void *context,
			    struct mt6797_a72_transaction *transaction);
	int (*prepare_cpu9)(
		void *context,
		const struct mt6797_a72_cpu9_executor_request *request);
	int (*add_cpu)(void *context, unsigned int cpu);
};

struct mt6797_a72_cpu9_admission_state {
	atomic_t consumed;
	u32 cpu8_requests;
	u32 cpu9_requests;
	u32 cpu_off_requests;
	u32 retries;
	u32 failure_stage;
	u32 derive_stage;
	int cpu8_ret;
	int cpu8_proof_ret;
	int operation_ret;
	struct mt6797_a72_transaction cpu9_transaction;
	struct mt6797_a72_cpu9_executor_request cpu9_request;
};

void mt6797_a72_cpu9_admission_state_init(
	struct mt6797_a72_cpu9_admission_state *state);
int mt6797_a72_cpu9_admission_run(
	struct mt6797_a72_cpu9_admission_state *state,
	const struct mt6797_a72_cpu9_admission_ops *ops, void *context);

#endif /* __MT6797_A72_CPU9_ADMISSION_CONTROLLER_INTERNAL_H */
