/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_A72_CPU9_EXECUTOR_INTERNAL_H
#define __MT6797_A72_CPU9_EXECUTOR_INTERNAL_H

#include <linux/atomic.h>
#include <linux/bitops.h>
#include <linux/types.h>

#define MT6797_A72_CPU9_EXECUTOR_CPU8 8U
#define MT6797_A72_CPU9_EXECUTOR_CPU9 9U

#define MT6797_A72_CPU9_RETAINED_P27 BIT(0)
#define MT6797_A72_CPU9_RETAINED_PROVIDER BIT(1)
#define MT6797_A72_CPU9_RETAINED_CPU8 BIT(2)
#define MT6797_A72_CPU9_RETAINED_REQUIRED                                                          \
	(MT6797_A72_CPU9_RETAINED_P27 | MT6797_A72_CPU9_RETAINED_PROVIDER |                        \
	 MT6797_A72_CPU9_RETAINED_CPU8)

enum mt6797_a72_cpu9_executor_stage {
	MT6797_A72_CPU9_STAGE_NONE,
	MT6797_A72_CPU9_STAGE_PRESTATE,
	MT6797_A72_CPU9_STAGE_CPU_ON,
	MT6797_A72_CPU9_STAGE_ONLINE_WAIT,
	MT6797_A72_CPU9_STAGE_IPI,
	MT6797_A72_CPU9_STAGE_MEMBERSHIP,
	MT6797_A72_CPU9_STAGE_COUNT,
};

enum mt6797_a72_cpu9_executor_phase {
	MT6797_A72_CPU9_PHASE_NONE,
	MT6797_A72_CPU9_PHASE_BEFORE,
	MT6797_A72_CPU9_PHASE_AFTER,
};

enum mt6797_a72_cpu9_executor_terminal {
	MT6797_A72_CPU9_TERMINAL_NONE,
	MT6797_A72_CPU9_REJECTED_PRESTATE,
	MT6797_A72_CPU9_FAULT_RETAIN_CPU8,
	MT6797_A72_CPU9_ONLINE_PROOF,
};

enum mt6797_a72_cpu9_executor_lifecycle {
	MT6797_A72_CPU9_LIFECYCLE_IDLE,
	MT6797_A72_CPU9_LIFECYCLE_STARTING,
	MT6797_A72_CPU9_LIFECYCLE_CPU_ON_ACCEPTED,
	MT6797_A72_CPU9_LIFECYCLE_SECONDARY_INFLIGHT,
	MT6797_A72_CPU9_LIFECYCLE_SECONDARY_COMPLETE,
	MT6797_A72_CPU9_LIFECYCLE_FINAL_INFLIGHT,
	MT6797_A72_CPU9_LIFECYCLE_TERMINAL,
};

struct mt6797_a72_cpu9_executor_controller {
	atomic_t consumed;
	atomic_t lifecycle;
};

#define MT6797_A72_CPU9_EXECUTOR_CONTROLLER_INIT                                                   \
	{.consumed = ATOMIC_INIT(0), .lifecycle = ATOMIC_INIT(MT6797_A72_CPU9_LIFECYCLE_IDLE)}

struct mt6797_a72_cpu9_executor_request {
	unsigned int cpu;
	u64 cpu8_attempt_id;
	u64 cpu9_attempt_id;
	u32 members;
	u32 retained_mask;
	bool cpu8_terminal_exact;
	bool cpu8_membership_published;
	bool provider_retained;
	bool cpu8_online;
	bool cpu9_online;
};

struct mt6797_a72_cpu9_executor_result {
	enum mt6797_a72_cpu9_executor_terminal terminal;
	enum mt6797_a72_cpu9_executor_stage last_stage;
	int stage_errno;
	int checkpoint_errno;
	bool attempted;
	bool cpu_on_accepted;
	bool membership_published;
	bool cpu8_online;
	bool cpu9_online;
	unsigned int cpu_requests;
	unsigned int cpu_off_requests;
	unsigned int retries;
	unsigned int checkpoints;
	unsigned int terminal_commits;
	u32 retained_mask;
};

struct mt6797_a72_cpu9_executor_ops {
	int (*checkpoint)(void *context, enum mt6797_a72_cpu9_executor_phase phase,
			  enum mt6797_a72_cpu9_executor_stage stage,
			  const struct mt6797_a72_cpu9_executor_result *result);
	int (*prestate)(void *context, const struct mt6797_a72_cpu9_executor_request *request);
	int (*cpu_on)(void *context, unsigned int cpu);
	int (*secondary_complete)(void *context, unsigned int cpu);
	int (*ipi_proof)(void *context, unsigned int cpu);
	int (*membership_commit)(void *context, unsigned int cpu);
	int (*terminal)(void *context, const struct mt6797_a72_cpu9_executor_result *result);
};

int mt6797_a72_cpu9_executor_begin(struct mt6797_a72_cpu9_executor_controller *controller,
				   const struct mt6797_a72_cpu9_executor_ops *ops, void *context,
				   const struct mt6797_a72_cpu9_executor_request *request,
				   struct mt6797_a72_cpu9_executor_result *result);
int mt6797_a72_cpu9_executor_secondary(struct mt6797_a72_cpu9_executor_controller *controller,
				       const struct mt6797_a72_cpu9_executor_ops *ops,
				       void *context, unsigned int cpu, bool cpu8_online,
				       bool cpu9_online,
				       struct mt6797_a72_cpu9_executor_result *result);
int mt6797_a72_cpu9_executor_complete(struct mt6797_a72_cpu9_executor_controller *controller,
				      const struct mt6797_a72_cpu9_executor_ops *ops, void *context,
				      unsigned int cpu, bool cpu8_online, bool cpu9_online,
				      struct mt6797_a72_cpu9_executor_result *result);
int mt6797_a72_cpu9_executor_fail(struct mt6797_a72_cpu9_executor_controller *controller,
				  const struct mt6797_a72_cpu9_executor_ops *ops, void *context,
				  unsigned int cpu, bool cpu8_online, bool cpu9_online, int error,
				  struct mt6797_a72_cpu9_executor_result *result);
int mt6797_a72_cpu9_executor_run(struct mt6797_a72_cpu9_executor_controller *controller,
				 const struct mt6797_a72_cpu9_executor_ops *ops, void *context,
				 const struct mt6797_a72_cpu9_executor_request *request,
				 struct mt6797_a72_cpu9_executor_result *result);

#endif /* __MT6797_A72_CPU9_EXECUTOR_INTERNAL_H */
