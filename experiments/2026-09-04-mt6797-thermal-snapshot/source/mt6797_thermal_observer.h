/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_THERMAL_OBSERVER_H
#define __MT6797_THERMAL_OBSERVER_H

#include <linux/mutex.h>

#include "mt6797_thermal_snapshot.h"

struct mt6797_thermal_observer {
	struct mutex lock;
	struct mt6797_thermal_snapshot_budget budget;
};

struct mt6797_thermal_observer_ops {
	u64 (*time_ns)(void *context);
	int (*scan)(void *context, struct mt6797_thermal_snapshot *snapshot,
		    int *aggregate);
};

static inline void
mt6797_thermal_observer_init(struct mt6797_thermal_observer *observer)
{
	mutex_init(&observer->lock);
	observer->budget.attempts = 0;
}

static inline int
mt6797_thermal_observer_capture(struct mt6797_thermal_observer *observer,
			       const struct mt6797_thermal_observer_ops *ops,
			       void *context,
			       struct mt6797_thermal_snapshot *snapshot)
{
	int aggregate = INT_MIN;
	int ret;

	if (!observer || !ops || !ops->time_ns || !ops->scan || !snapshot)
		return -EINVAL;

	mutex_lock(&observer->lock);
	/* Admission precedes even the clock callback. Failures spend attempts. */
	ret = mt6797_thermal_snapshot_begin(&observer->budget, snapshot, 0);
	if (ret)
		goto unlock;

	snapshot->start_ns = ops->time_ns(context);
	ret = ops->scan(context, snapshot, &aggregate);
	if (ret && !snapshot->error)
		snapshot->error = ret;
	ret = mt6797_thermal_snapshot_finish(snapshot, ops->time_ns(context),
					     aggregate);
unlock:
	mutex_unlock(&observer->lock);
	return ret;
}

#endif /* __MT6797_THERMAL_OBSERVER_H */
