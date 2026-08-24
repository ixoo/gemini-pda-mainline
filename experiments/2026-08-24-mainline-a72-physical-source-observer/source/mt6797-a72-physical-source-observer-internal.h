/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_A72_PHYSICAL_SOURCE_OBSERVER_INTERNAL_H
#define __MT6797_A72_PHYSICAL_SOURCE_OBSERVER_INTERNAL_H

#include <linux/mt6797-a72-direct-state.h>

struct device;
struct mt6797_a72_direct_state_snapshot;

struct mt6797_a72_physical_source_reader_ops {
	int (*platform)(struct device *dev,
			struct mt6797_a72_platform_state *snapshot);
	int (*provider)(struct mt6797_a72_provider_snapshot *snapshot);
	int (*clock)(struct device *dev,
		     struct mt6797_dvfsp_clock_readback *snapshot);
	bool (*checkpoint)(unsigned int checkpoint);
	int (*bigidvfs)(struct device *dev,
			struct mt6797_bigidvfs_readback *snapshot);
};

struct mt6797_a72_physical_source_context {
	struct device *platform;
	struct device *clock;
	struct device *bigidvfs;
	const struct mt6797_a72_physical_source_reader_ops *readers;
};

struct mt6797_a72_physical_source_runtime_ops {
	int (*register_source)(const struct mt6797_a72_direct_source_ops *ops,
			       void *context);
	int (*snapshot)(struct mt6797_a72_direct_state_snapshot *snapshot);
	void (*unregister_source)(const struct mt6797_a72_direct_source_ops *ops,
				  void *context);
};

int
mt6797_a72_physical_source_capture(void *context,
				   struct mt6797_a72_direct_source_snapshot *snapshot);
int
mt6797_a72_physical_source_run(struct mt6797_a72_physical_source_context *context,
			       const struct mt6797_a72_physical_source_runtime_ops *runtime,
			       struct mt6797_a72_direct_state_snapshot *snapshot);

#endif /* __MT6797_A72_PHYSICAL_SOURCE_OBSERVER_INTERNAL_H */
