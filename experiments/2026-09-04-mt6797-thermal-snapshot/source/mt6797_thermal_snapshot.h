/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __MT6797_THERMAL_SNAPSHOT_H
#define __MT6797_THERMAL_SNAPSHOT_H

#include <linux/errno.h>
#include <linux/limits.h>
#include <linux/types.h>

#define MT6797_THERMAL_SNAPSHOT_ABI 1U
#define MT6797_THERMAL_SNAPSHOT_SAMPLES 7U
#define MT6797_THERMAL_SNAPSHOT_ATTEMPTS 3U
#define MT6797_THERMAL_SNAPSHOT_VALID_MASK 0x7fU

/* The caller must serialize this budget independently of normal polling. */
struct mt6797_thermal_snapshot_budget {
	u32 attempts;
};

struct mt6797_thermal_snapshot_sample {
	u32 bank;
	u32 sensor;
	int temperature;
	bool valid;
};

struct mt6797_thermal_snapshot {
	u32 abi;
	u32 attempt;
	u32 count;
	u32 valid_mask;
	u32 winner;
	int maximum;
	int error;
	u64 start_ns;
	u64 end_ns;
	bool active;
	bool complete;
	struct mt6797_thermal_snapshot_sample samples[MT6797_THERMAL_SNAPSHOT_SAMPLES];
};

static inline int
mt6797_thermal_snapshot_begin(struct mt6797_thermal_snapshot_budget *budget,
			      struct mt6797_thermal_snapshot *snapshot,
			      u64 start_ns)
{
	if (!budget || !snapshot)
		return -EINVAL;

	/* A new attempt cannot overwrite an unfinished invocation. */
	if (snapshot->active)
		return -EBUSY;

	*snapshot = (struct mt6797_thermal_snapshot) {
		.abi = MT6797_THERMAL_SNAPSHOT_ABI,
		.attempt = budget->attempts,
		.winner = MT6797_THERMAL_SNAPSHOT_SAMPLES,
		.maximum = INT_MIN,
	};
	if (budget->attempts >= MT6797_THERMAL_SNAPSHOT_ATTEMPTS) {
		snapshot->error = -ENOSPC;
		return snapshot->error;
	}

	/* Consume before the caller starts any sensor scan, including failure. */
	snapshot->attempt = ++budget->attempts;
	snapshot->start_ns = start_ns;
	snapshot->active = true;
	return 0;
}

static inline int
mt6797_thermal_snapshot_append(struct mt6797_thermal_snapshot *snapshot,
			       u32 bank, u32 sensor, int temperature,
			       bool valid)
{
	static const u32 banks[MT6797_THERMAL_SNAPSHOT_SAMPLES] = {
		0, 1, 2, 2, 3, 4, 5,
	};
	static const u32 sensors[MT6797_THERMAL_SNAPSHOT_SAMPLES] = {
		0, 3, 1, 2, 1, 1, 1,
	};
	u32 slot;

	if (!snapshot || !snapshot->active)
		return -EINVAL;
	if (snapshot->error)
		return snapshot->error;

	slot = snapshot->count;
	if (slot >= MT6797_THERMAL_SNAPSHOT_SAMPLES ||
	    bank != banks[slot] || sensor != sensors[slot]) {
		snapshot->error = -EINVAL;
		return snapshot->error;
	}

	snapshot->samples[slot] = (struct mt6797_thermal_snapshot_sample) {
		.bank = bank,
		.sensor = sensor,
		.temperature = temperature,
		.valid = valid,
	};
	if (valid) {
		snapshot->valid_mask |= 1U << slot;
		/* Ties retain the first observed winning slot. */
		if (snapshot->winner == MT6797_THERMAL_SNAPSHOT_SAMPLES ||
		    temperature > snapshot->maximum) {
			snapshot->maximum = temperature;
			snapshot->winner = slot;
		}
	}
	snapshot->count++;
	return 0;
}

static inline int
mt6797_thermal_snapshot_finish(struct mt6797_thermal_snapshot *snapshot,
			       u64 end_ns, int aggregate)
{
	if (!snapshot || !snapshot->active)
		return -EINVAL;

	snapshot->active = false;
	snapshot->end_ns = end_ns;
	if (!snapshot->error &&
	    (end_ns < snapshot->start_ns ||
	     snapshot->count != MT6797_THERMAL_SNAPSHOT_SAMPLES))
		snapshot->error = -EINVAL;
	if (!snapshot->error && snapshot->maximum != aggregate)
		snapshot->error = -EBADMSG;
	if (!snapshot->error &&
	    snapshot->valid_mask != MT6797_THERMAL_SNAPSHOT_VALID_MASK)
		snapshot->error = -ENODATA;

	snapshot->complete = !snapshot->error;
	return snapshot->error;
}

#endif /* __MT6797_THERMAL_SNAPSHOT_H */
