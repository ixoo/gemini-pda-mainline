/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _LINUX_MTK_WDT_H
#define _LINUX_MTK_WDT_H

#include <linux/errno.h>
#include <linux/types.h>

struct device;

struct mtk_wdt_boot_status {
	u32 raw;
	bool valid;
};

#ifdef CONFIG_MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE
int mtk_wdt_boot_status_snapshot(struct device *dev,
				 struct mtk_wdt_boot_status *snapshot);
#else
static inline int
mtk_wdt_boot_status_snapshot(struct device *dev,
			     struct mtk_wdt_boot_status *snapshot)
{
	(void)dev;
	if (snapshot)
		*snapshot = (struct mtk_wdt_boot_status){};
	return -EOPNOTSUPP;
}
#endif

#endif
