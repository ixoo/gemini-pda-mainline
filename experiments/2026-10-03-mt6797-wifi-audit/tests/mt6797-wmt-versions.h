/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MT6797_WMT_VERSIONS_H
#define MT6797_WMT_VERSIONS_H
#include "mt6797-wmt-version-io.h"

#define WMT_VERSIONS_BUDGET_MS 1500U

/* Persistent caller-owned storage, with shared CONSYS mutex held and the
 * reviewed BTIF setup complete. Three separate exclusive IRQ lifetimes;
 * no setup repetition, clock acquisition, reset, negotiation or continuation.
 */
struct mt6797_wmt_versions {
	struct mt6797_wmt_version_io reads[3];
	void __iomem *btif;
	unsigned long deadline;
	unsigned int completed;
	int irq, clocks_held, attempted, result;
};

static int mt6797_wmt_versions_once(struct mt6797_wmt_versions *owner)
{
	unsigned long end;
	unsigned int ordinal;
	int ret;

	if (!owner || !owner->btif || owner->irq <= 0 || !owner->clocks_held)
		return -EINVAL;
	if (owner->attempted || owner->completed || owner->reads[0].prepared ||
	    owner->reads[1].prepared || owner->reads[2].prepared)
		return -EALREADY;
	owner->attempted = 1;
	owner->deadline = jiffies + msecs_to_jiffies(WMT_VERSIONS_BUDGET_MS);
	for (ordinal = 0; ordinal < 3; ordinal++) {
		if (time_after_eq(jiffies, owner->deadline)) {
			ret = -ETIMEDOUT;
			goto out;
		}
		end = jiffies + msecs_to_jiffies(500);
		if (time_before(owner->deadline, end))
			end = owner->deadline;
		ret = mt6797_wmt_version_prepare(&owner->reads[ordinal], owner->btif,
						 owner->irq, ordinal, end);
		if (!ret)
			ret = mt6797_wmt_version_exchange(&owner->reads[ordinal]);
		if (ret)
			goto out;
		if (time_after_eq(jiffies, owner->deadline)) {
			ret = -ETIMEDOUT;
			goto out;
		}
		owner->completed++;
	}
	ret = 0;
out:
	owner->result = ret;
	return ret;
}

#endif
