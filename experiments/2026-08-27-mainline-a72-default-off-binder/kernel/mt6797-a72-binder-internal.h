/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_A72_BINDER_INTERNAL_H
#define __MT6797_A72_BINDER_INTERNAL_H

#include <linux/atomic.h>
#include <linux/cpuhotplug.h>
#include <linux/gemini_transition_ledger.h>
#include <linux/mt6797-a72-provider.h>
#include <linux/mtk_wdt.h>
#include <linux/smp.h>
#include <linux/soc/mediatek/mt6797-a72-binder.h>
#include <linux/soc/mediatek/mt6797-a72-platform-state.h>
#include <linux/soc/mediatek/mt6797-bigidvfs-backend.h>
#include <linux/types.h>

#include <asm/mt6797_a72_membership.h>

#include "mt6797-a72-transition-internal.h"

struct device;

struct mt6797_a72_binder_backend_ops {
	int (*ledger_begin)(u64 attempt_id);
	int (*ledger_checkpoint)(u64 attempt_id, u32 phase, u32 stage,
				 u32 terminal);
	bool (*provider_available)(void);
	int (*membership_preflight)(unsigned int cpu, enum cpuhp_state target);
	int (*membership_validate)(unsigned int cpu, int tasks_frozen,
				   enum cpuhp_state target);
	int (*membership_claim)(struct mt6797_a72_transaction *transaction);
	bool (*membership_owns_token)(
		const struct arm64_late_cpu_up_token *token);
	int (*membership_reject)(struct mt6797_a72_transaction *transaction);
	int (*membership_begin_p27)(
		struct mt6797_a72_transaction *transaction);
	int (*membership_complete_p27)(
		struct mt6797_a72_transaction *transaction,
		const struct mt6797_a72_p27_preparation *preparation);
	int (*membership_provider_acquire)(
		struct mt6797_a72_transaction *transaction,
		struct mt6797_a72_provider_response *response);
	int (*membership_provider_abort)(
		struct mt6797_a72_transaction *transaction,
		struct mt6797_a72_provider_response *response);
	int (*membership_begin_p28)(
		struct mt6797_a72_transaction *transaction);
	int (*membership_complete_p28)(
		struct mt6797_a72_transaction *transaction,
		const struct mt6797_a72_p28_preparation *preparation);
	int (*membership_complete_p29)(
		struct mt6797_a72_transaction *transaction,
		const struct mt6797_a72_p29_rollback_proof *rollback);
	int (*membership_begin_cpu_on)(
		struct mt6797_a72_transaction *transaction);
	int (*membership_publish_success)(
		struct mt6797_a72_transaction *transaction);
	int (*membership_finalize_success)(
		struct mt6797_a72_transaction *transaction);
	int (*watchdog_takeover)(struct device *dev, unsigned int timeout_ms,
				 struct mtk_wdt_recovery_result *result);
	int (*p27_acquire)(struct device *dev,
			   const struct mt6797_a72_platform_effect_handle *handle,
			   struct mt6797_a72_platform_effect_result *result);
	int (*p27_release)(struct device *dev,
			   const struct mt6797_a72_platform_effect_handle *handle,
			   struct mt6797_a72_platform_effect_result *result);
	int (*isolation_clear)(
		struct device *dev,
		const struct mt6797_a72_platform_effect_handle *handle,
		const struct mt6797_a72_provider_handle *provider,
		struct mt6797_a72_platform_effect_result *result);
	int (*sram_enable)(struct device *dev,
			   const struct mt6797_bigidvfs_sram_request *request,
			   struct mt6797_bigidvfs_sram_result *result);
	int (*dcm_update)(struct device *dev,
			  const struct mt6797_a72_platform_effect_handle *handle,
			  bool cpu8_online, bool cpu9_online,
			  struct mt6797_a72_platform_effect_result *result);
	bool (*cpu_online)(unsigned int cpu);
	int (*ipi_call)(unsigned int cpu, smp_call_func_t func, void *info,
			int wait);
};

struct mt6797_a72_binder {
	struct device *dev;
	struct device *watchdog;
	struct device *platform_state;
	struct device *bigidvfs;
	const struct mt6797_a72_binder_backend_ops *backend;
	struct mt6797_a72_transition_controller transition;
	struct mt6797_a72_transaction transaction;
	struct mt6797_a72_transition_result result;
	struct mt6797_a72_platform_effect_handle effect_handle;
	struct mt6797_a72_platform_effect_result p27;
	struct mt6797_a72_platform_effect_result isolation;
	struct mt6797_a72_platform_effect_result dcm;
	struct mt6797_bigidvfs_sram_result sram;
	struct mt6797_a72_provider_response provider;
	mt6797_a72_cpu_boot_fn cpu_boot;
	atomic_t boot_claimed;
	bool ledger_begun;
	bool p28_begun;
};

#if IS_ENABLED(CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER_KUNIT_TEST)
void mt6797_a72_binder_test_init(
	struct mt6797_a72_binder *binder,
	const struct mt6797_a72_binder_backend_ops *backend);
int mt6797_a72_binder_test_boot(struct mt6797_a72_binder *binder,
	unsigned int cpu, mt6797_a72_cpu_boot_fn cpu_boot);
int mt6797_a72_binder_test_secondary_complete(
	struct mt6797_a72_binder *binder, unsigned int cpu);
int mt6797_a72_binder_test_complete(struct mt6797_a72_binder *binder,
	unsigned int cpu, enum cpuhp_state target);
int mt6797_a72_binder_test_failure(struct mt6797_a72_binder *binder,
	unsigned int cpu, int error, bool *publish_p32);
#endif

#endif /* __MT6797_A72_BINDER_INTERNAL_H */
