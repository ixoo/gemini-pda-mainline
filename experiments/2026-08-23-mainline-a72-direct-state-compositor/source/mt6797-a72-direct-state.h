/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __LINUX_MT6797_A72_DIRECT_STATE_H
#define __LINUX_MT6797_A72_DIRECT_STATE_H

#include <linux/mt6797-a72-provider.h>
#include <linux/soc/mediatek/mt6797-a72-platform-state.h>
#include <linux/soc/mediatek/mt6797-bigidvfs-backend.h>
#include <linux/soc/mediatek/mt6797-dvfsp-clock-backend.h>
#include <linux/types.h>

#define MT6797_A72_DIRECT_SOURCE_ABI	1

/* Hardware-only raw composition; this record is not an A34 decision. */
struct mt6797_a72_direct_source_snapshot {
	u32 abi;
	u32 valid;
	u32 reserved[2];
	struct mt6797_a72_provider_snapshot provider;
	struct mt6797_a72_platform_state platform;
	struct mt6797_dvfsp_clock_readback clock;
	struct mt6797_bigidvfs_readback bigidvfs;
};

struct mt6797_a72_direct_source_ops {
	int (*snapshot)(void *context,
			struct mt6797_a72_direct_source_snapshot *snapshot);
};

#endif /* __LINUX_MT6797_A72_DIRECT_STATE_H */
