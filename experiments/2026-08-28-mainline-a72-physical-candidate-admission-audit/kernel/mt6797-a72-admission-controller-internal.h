/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_A72_ADMISSION_CONTROLLER_INTERNAL_H
#define __MT6797_A72_ADMISSION_CONTROLLER_INTERNAL_H

#include <asm/mt6797_a72_membership.h>

#include <linux/atomic.h>
#include <linux/types.h>

struct arm64_late_cpu_ready_token;

struct mt6797_a72_admission_controller_ops {
	bool (*binder_ready)(void *context);
	const struct arm64_late_cpu_ready_token *(*ready_token)(void *context);
	int (*source_register)(void *context);
	void (*source_unregister)(void *context);
	int (*derive_cpu8)(void *context,
			   const struct arm64_late_cpu_ready_token *ready,
			   struct mt6797_a72_transaction *transaction);
	int (*publish_up)(void *context,
			  struct mt6797_a72_transaction *transaction);
	int (*add_cpu)(void *context, unsigned int cpu);
};

struct mt6797_a72_admission_controller_state {
	atomic_t consumed;
	u32 cpu_requests;
	int operation_ret;
	struct mt6797_a72_transaction transaction;
};

void
mt6797_a72_admission_state_init(struct mt6797_a72_admission_controller_state *state);
int
mt6797_a72_admission_run(struct mt6797_a72_admission_controller_state *state,
	const struct mt6797_a72_admission_controller_ops *ops, void *context);

#endif /* __MT6797_A72_ADMISSION_CONTROLLER_INTERNAL_H */
