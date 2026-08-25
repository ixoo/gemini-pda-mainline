/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER_INTERNAL_H
#define __MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER_INTERNAL_H

#include <linux/mt6797-a72-provider.h>
#include <linux/soc/mediatek/mt6797-a72-platform-state.h>

struct device;

struct mt6797_a72_platform_provider_snapshot {
	struct mt6797_a72_platform_state platform;
	struct mt6797_a72_provider_snapshot provider;
	bool valid;
};

struct mt6797_a72_platform_provider_observer_ops {
	int (*platform)(void *context, struct device *dev,
			struct mt6797_a72_platform_state *snapshot);
	bool (*checkpoint)(void *context, unsigned int checkpoint);
	int (*provider)(void *context,
			struct mt6797_a72_provider_snapshot *snapshot);
};

int mt6797_a72_pp_capture(struct device *platform,
			  const struct mt6797_a72_platform_provider_observer_ops *ops,
			  void *context,
			  struct mt6797_a72_platform_provider_snapshot *snapshot);

#endif /* __MT6797_A72_PLATFORM_PROVIDER_SNAPSHOT_OBSERVER_INTERNAL_H */
