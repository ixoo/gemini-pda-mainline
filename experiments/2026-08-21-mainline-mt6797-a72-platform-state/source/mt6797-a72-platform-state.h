/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __LINUX_SOC_MEDIATEK_MT6797_A72_PLATFORM_STATE_H
#define __LINUX_SOC_MEDIATEK_MT6797_A72_PLATFORM_STATE_H

#include <linux/errno.h>
#include <linux/kconfig.h>
#include <linux/types.h>

struct device;

/**
 * struct mt6797_a72_platform_state - one immutable raw platform sample
 * @spm_pwr_status: general SPM power-domain status
 * @spm_pwr_status_2nd: second general SPM power-domain status
 * @spm_cpu_pwr_status: first SPM CPU power-status word
 * @spm_cpu_pwr_status_2nd: second SPM CPU power-status word
 * @spm_mp2_cpusys_pwr_con: MP2 cluster power-control word
 * @spm_mp2_cpu0_pwr_con: CPU8 power-control word
 * @spm_mp2_cpu1_pwr_con: CPU9 power-control word
 * @spm_cpu_ext_buck_iso: external CPU-buck isolation word
 * @mp2_sync_dcm: MP2 synchronous DCM word
 * @cci_mp2_port_control: MP2 CCI port-control word
 * @cci_status_before: global CCI status before the port read
 * @cci_status_after: global CCI status after the port read
 * @pwrap_reset_asserted: logical TOPRGU PWRAP reset state
 * @valid: all fields were captured in one stable bounded transaction
 *
 * This record carries raw observation only. It does not classify recovery,
 * authorize an A72 transition, or provide cross-PSCI serialization.
 */
struct mt6797_a72_platform_state {
	u32 spm_pwr_status;
	u32 spm_pwr_status_2nd;
	u32 spm_cpu_pwr_status;
	u32 spm_cpu_pwr_status_2nd;
	u32 spm_mp2_cpusys_pwr_con;
	u32 spm_mp2_cpu0_pwr_con;
	u32 spm_mp2_cpu1_pwr_con;
	u32 spm_cpu_ext_buck_iso;
	u32 mp2_sync_dcm;
	u32 cci_mp2_port_control;
	u32 cci_status_before;
	u32 cci_status_after;
	bool pwrap_reset_asserted;
	bool valid;
};

#if IS_ENABLED(CONFIG_MTK_MT6797_A72_PLATFORM_STATE)
int mt6797_a72_platform_state_snapshot(
	struct device *dev, struct mt6797_a72_platform_state *snapshot);
#else
static inline int mt6797_a72_platform_state_snapshot(
	struct device *dev, struct mt6797_a72_platform_state *snapshot)
{
	(void)dev;
	if (snapshot)
		*snapshot = (struct mt6797_a72_platform_state){};
	return -EOPNOTSUPP;
}
#endif

#endif
