/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_A72_TRANSITION_INTERNAL_H
#define __MT6797_A72_TRANSITION_INTERNAL_H

#include <linux/atomic.h>
#include <linux/bitops.h>
#include <linux/types.h>

#define MT6797_A72_TRANSITION_CPU8 8U
#define MT6797_A72_TRANSITION_CPU9 9U
#define MT6797_A72_TRANSITION_RECOVERY_MS 15000U

#define MT6797_A72_TRANSITION_OWNED_P27 BIT(0)
#define MT6797_A72_TRANSITION_OWNED_PROVIDER BIT(1)
#define MT6797_A72_TRANSITION_OWNED_CPU8 BIT(2)

enum mt6797_a72_transition_stage {
	MT6797_A72_TRANSITION_STAGE_ENTRY,
	MT6797_A72_TRANSITION_STAGE_WATCHDOG,
	MT6797_A72_TRANSITION_STAGE_P27,
	MT6797_A72_TRANSITION_STAGE_PROVIDER,
	MT6797_A72_TRANSITION_STAGE_ISOLATION,
	MT6797_A72_TRANSITION_STAGE_SRAM,
	MT6797_A72_TRANSITION_STAGE_CPU_ON,
	MT6797_A72_TRANSITION_STAGE_ONLINE_WAIT,
	MT6797_A72_TRANSITION_STAGE_IPI,
	MT6797_A72_TRANSITION_STAGE_DCM,
	MT6797_A72_TRANSITION_STAGE_COUNT,
};

enum mt6797_a72_transition_phase {
	MT6797_A72_TRANSITION_BEFORE,
	MT6797_A72_TRANSITION_AFTER,
};

enum mt6797_a72_transition_terminal {
	MT6797_A72_TRANSITION_TERMINAL_NONE,
	MT6797_A72_TRANSITION_REJECTED_PRESTATE,
	MT6797_A72_TRANSITION_ROLLED_BACK_PREISO,
	MT6797_A72_TRANSITION_ROLLBACK_FAULT_PREISO,
	MT6797_A72_TRANSITION_FAULT_RETAIN_POSTISO,
	MT6797_A72_TRANSITION_CPU8_ONLINE_PROOF,
};

enum mt6797_a72_transition_lifecycle {
	MT6797_A72_TRANSITION_LIFECYCLE_IDLE,
	MT6797_A72_TRANSITION_LIFECYCLE_STARTING,
	MT6797_A72_TRANSITION_LIFECYCLE_CPU_ON_ACCEPTED,
	MT6797_A72_TRANSITION_LIFECYCLE_SECONDARY_INFLIGHT,
	MT6797_A72_TRANSITION_LIFECYCLE_SECONDARY_COMPLETE,
	MT6797_A72_TRANSITION_LIFECYCLE_FINAL_INFLIGHT,
	MT6797_A72_TRANSITION_LIFECYCLE_TERMINAL,
};

struct mt6797_a72_transition_controller {
	atomic_t consumed;
	atomic_t lifecycle;
};

#define MT6797_A72_TRANSITION_CONTROLLER_INIT \
	{ .consumed = ATOMIC_INIT(0), \
	  .lifecycle = ATOMIC_INIT(MT6797_A72_TRANSITION_LIFECYCLE_IDLE) }

struct mt6797_a72_transition_request {
	unsigned int cpu;
	bool token_exact;
	bool prefix_complete;
	bool cpu8_online;
	bool cpu9_online;
};

struct mt6797_a72_transition_result {
	enum mt6797_a72_transition_terminal terminal;
	enum mt6797_a72_transition_stage last_stage;
	int stage_errno;
	int rollback_errno;
	bool attempted;
	bool watchdog_armed;
	bool isolation_attempted;
	bool isolation_crossed;
	bool cpu_on_accepted;
	bool p27_owned;
	bool provider_owned;
	bool cpu8_online;
	bool cpu9_online;
	unsigned int cpu_requests;
	unsigned int cpu_off_requests;
	unsigned int retries;
	unsigned int checkpoints;
	u32 rollback_mask;
	u32 retained_mask;
	u64 watchdog_identity;
};

struct mt6797_a72_transition_ops {
	void (*checkpoint)(void *context,
			   enum mt6797_a72_transition_phase phase,
			   enum mt6797_a72_transition_stage stage,
			   const struct mt6797_a72_transition_result *result);
	int (*watchdog_arm)(void *context, unsigned int timeout_ms,
			    u64 *identity);
	int (*p27_acquire)(void *context, bool *owned);
	int (*p27_release)(void *context);
	int (*provider_acquire)(void *context, bool *owned);
	int (*provider_release)(void *context);
	int (*isolation_clear)(void *context);
	int (*sram_enable)(void *context);
	int (*cpu_on)(void *context, unsigned int cpu);
	int (*secondary_complete)(void *context, unsigned int cpu);
	int (*ipi_proof)(void *context, unsigned int cpu);
	int (*dcm_update)(void *context);
};

int mt6797_a72_transition_begin(
	struct mt6797_a72_transition_controller *controller,
	const struct mt6797_a72_transition_ops *ops, void *context,
	const struct mt6797_a72_transition_request *request,
	struct mt6797_a72_transition_result *result);
int mt6797_a72_transition_secondary_complete(
	struct mt6797_a72_transition_controller *controller,
	const struct mt6797_a72_transition_ops *ops, void *context,
	unsigned int cpu, bool cpu8_online, bool cpu9_online,
	struct mt6797_a72_transition_result *result);
int mt6797_a72_transition_complete(
	struct mt6797_a72_transition_controller *controller,
	const struct mt6797_a72_transition_ops *ops, void *context,
	unsigned int cpu, bool cpu8_online, bool cpu9_online,
	struct mt6797_a72_transition_result *result);
int mt6797_a72_transition_fail(
	struct mt6797_a72_transition_controller *controller,
	const struct mt6797_a72_transition_ops *ops, void *context,
	unsigned int cpu, bool cpu8_online, bool cpu9_online, int error,
	struct mt6797_a72_transition_result *result);
int mt6797_a72_transition_run(
	struct mt6797_a72_transition_controller *controller,
	const struct mt6797_a72_transition_ops *ops, void *context,
	const struct mt6797_a72_transition_request *request,
	struct mt6797_a72_transition_result *result);

#endif /* __MT6797_A72_TRANSITION_INTERNAL_H */
