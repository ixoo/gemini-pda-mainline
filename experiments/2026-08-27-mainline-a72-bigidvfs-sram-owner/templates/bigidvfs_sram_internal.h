/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_BIGIDVFS_SRAM_INTERNAL_H
#define __MT6797_BIGIDVFS_SRAM_INTERNAL_H

#include <linux/soc/mediatek/mt6797-bigidvfs-backend.h>

enum mt6797_bigidvfs_sram_owner_state {
	MT6797_BIGIDVFS_SRAM_OWNER_UNUSED,
	MT6797_BIGIDVFS_SRAM_OWNER_INFLIGHT,
	MT6797_BIGIDVFS_SRAM_OWNER_VERIFIED,
	MT6797_BIGIDVFS_SRAM_OWNER_FAULTED,
};

struct mt6797_bigidvfs_sram_ops {
	int (*set)(void *context, u32 mv_x100);
	int (*read)(void *context, u32 address, u32 *value);
	void (*delay)(void *context, unsigned int min_us, unsigned int max_us);
};

struct mt6797_bigidvfs_sram_owner {
	enum mt6797_bigidvfs_sram_owner_state state;
	struct mt6797_bigidvfs_sram_request request;
	struct mt6797_bigidvfs_sram_result result;
};

int
mt6797_bigidvfs_sram_owner_execute(struct mt6797_bigidvfs_sram_owner *owner,
				   const struct mt6797_bigidvfs_sram_ops *ops,
				   void *context,
				   const struct mt6797_bigidvfs_sram_request *request,
				   struct mt6797_bigidvfs_sram_result *result);

#endif /* __MT6797_BIGIDVFS_SRAM_INTERNAL_H */
