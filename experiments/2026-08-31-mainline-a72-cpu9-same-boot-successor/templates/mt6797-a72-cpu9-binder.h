/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __LINUX_SOC_MEDIATEK_MT6797_A72_CPU9_BINDER_H
#define __LINUX_SOC_MEDIATEK_MT6797_A72_CPU9_BINDER_H

#include <linux/cpuhotplug.h>
#include <linux/errno.h>
#include <linux/kconfig.h>
#include <linux/types.h>

#include <linux/soc/mediatek/mt6797-a72-binder.h>

struct mt6797_a72_cpu9_executor_request;

#if IS_ENABLED(CONFIG_MTK_MT6797_A72_CPU9_BINDER)
int mt6797_a72_cpu9_binder_prepare(
	const struct mt6797_a72_cpu9_executor_request *request);
int mt6797_a72_cpu9_binder_preflight(unsigned int cpu,
				      enum cpuhp_state target);
int mt6797_a72_cpu9_binder_validate(unsigned int cpu, int tasks_frozen,
				     enum cpuhp_state target);
int mt6797_a72_cpu9_binder_cpu_boot(unsigned int cpu,
				     mt6797_a72_cpu_boot_fn cpu_boot);
int mt6797_a72_cpu9_binder_secondary_complete(unsigned int cpu);
int mt6797_a72_cpu9_binder_complete(unsigned int cpu,
				     enum cpuhp_state target);
int mt6797_a72_cpu9_binder_failure(unsigned int cpu, int error,
				    bool *publish_p32);
#else
static inline int mt6797_a72_cpu9_binder_prepare(
	const struct mt6797_a72_cpu9_executor_request *request)
{
	(void)request;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_cpu9_binder_preflight(unsigned int cpu,
					     enum cpuhp_state target)
{
	(void)cpu;
	(void)target;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_cpu9_binder_validate(unsigned int cpu,
					    int tasks_frozen,
					    enum cpuhp_state target)
{
	(void)cpu;
	(void)tasks_frozen;
	(void)target;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_cpu9_binder_cpu_boot(
	unsigned int cpu, mt6797_a72_cpu_boot_fn cpu_boot)
{
	(void)cpu;
	(void)cpu_boot;
	return -EOPNOTSUPP;
}

static inline int
mt6797_a72_cpu9_binder_secondary_complete(unsigned int cpu)
{
	(void)cpu;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_cpu9_binder_complete(unsigned int cpu,
					    enum cpuhp_state target)
{
	(void)cpu;
	(void)target;
	return -EOPNOTSUPP;
}

static inline int mt6797_a72_cpu9_binder_failure(unsigned int cpu,
					   int error,
					   bool *publish_p32)
{
	(void)cpu;
	(void)error;
	if (publish_p32)
		*publish_p32 = false;
	return -EOPNOTSUPP;
}
#endif

#endif /* __LINUX_SOC_MEDIATEK_MT6797_A72_CPU9_BINDER_H */
