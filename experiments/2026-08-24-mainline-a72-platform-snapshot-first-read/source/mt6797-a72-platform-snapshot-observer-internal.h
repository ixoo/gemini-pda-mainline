/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER_INTERNAL_H
#define __MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER_INTERNAL_H

#include <linux/soc/mediatek/mt6797-a72-platform-state.h>

struct device;

struct mt6797_a72_platform_snapshot_observer_ops {
	bool (*checkpoint)(void *context, unsigned int checkpoint);
	int (*snapshot)(void *context, struct device *dev,
			struct mt6797_a72_platform_state *snapshot);
};

int mt6797_a72_platform_snapshot_capture(
	struct device *platform,
	const struct mt6797_a72_platform_snapshot_observer_ops *ops,
	void *context, struct mt6797_a72_platform_state *snapshot);

#endif /* __MT6797_A72_PLATFORM_SNAPSHOT_OBSERVER_INTERNAL_H */
