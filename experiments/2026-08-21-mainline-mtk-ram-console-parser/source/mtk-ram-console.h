/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _LINUX_SOC_MEDIATEK_MTK_RAM_CONSOLE_H
#define _LINUX_SOC_MEDIATEK_MTK_RAM_CONSOLE_H

#include <linux/errno.h>
#include <linux/kconfig.h>
#include <linux/types.h>

struct mtk_ram_console_snapshot {
	u32 preloader_status;
	bool valid;
};

#if IS_ENABLED(CONFIG_MTK_RAM_CONSOLE_PARSER)
int mtk_ram_console_parse(const void *buffer, size_t buffer_size,
			  struct mtk_ram_console_snapshot *snapshot);
#else
static inline int
mtk_ram_console_parse(const void *buffer, size_t buffer_size,
			  struct mtk_ram_console_snapshot *snapshot)
{
	(void)buffer;
	(void)buffer_size;
	if (snapshot)
		*snapshot = (struct mtk_ram_console_snapshot){};

	return -EOPNOTSUPP;
}
#endif

#endif
