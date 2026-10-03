/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MT6797_WMT_NEGOTIATE_H
#define MT6797_WMT_NEGOTIATE_H

#include <linux/delay.h>
#include "mt6797-wmt-query.h"
#include "mt6797-wmt-full-io.h"
#include "wmt-stp-options.h"

#define WMT_NEGOTIATE_BUDGET_MS 1600U
#define WMT_NEGOTIATE_EXCHANGE_MS 500U

enum mt6797_wmt_phase {
	WMT_PHASE_UNUSED,
	WMT_PHASE_DEFAULT,
	WMT_PHASE_SET,
	WMT_PHASE_SWITCH,
	WMT_PHASE_FULL,
	WMT_PHASE_DONE,
};

/* Zeroed persistent CONSYS-owned storage. Caller fills the first query's exact
 * mappings, clock handles and exclusive IRQ, after fresh power/reset release.
 * Its shared owner lock serializes this entire lifetime. All records/resources
 * survive failure for preservation and reviewed recovery, never stack allocated.
 */
struct mt6797_wmt_negotiate {
	struct mt6797_wmt_query first;
	struct mt6797_wmt_full_io set, full;
	struct wmt_full_state link;
	unsigned long deadline;
	enum mt6797_wmt_phase phase;
	int attempted, full_initialized, result;
};

static unsigned long mt6797_wmt_phase_deadline(struct mt6797_wmt_negotiate *owner)
{
	unsigned long end = jiffies + msecs_to_jiffies(WMT_NEGOTIATE_EXCHANGE_MS);

	return time_before(owner->deadline, end) ? owner->deadline : end;
}

/* Software framing changes only at the checked set event. There is no mode
 * register write, repeated FIFO clear, wake, patch, calibration or WLAN start.
 */
static int mt6797_wmt_negotiate_once(struct mt6797_wmt_negotiate *owner)
{
	int ret;

	if (!owner || !owner->first.btif || !owner->first.dma_tx ||
	    !owner->first.dma_rx || !owner->first.btif_clk ||
	    !owner->first.dma_clk || owner->first.irq <= 0)
		return -EINVAL;
	if (owner->attempted || owner->first.attempted || owner->set.prepared ||
	    owner->full.prepared)
		return -EALREADY;
	owner->attempted = 1;
	owner->deadline = jiffies + msecs_to_jiffies(WMT_NEGOTIATE_BUDGET_MS);
	owner->phase = WMT_PHASE_DEFAULT;
	owner->first.deadline = mt6797_wmt_phase_deadline(owner);
	owner->first.deadline_supplied = true;
	ret = mt6797_wmt_query_once(&owner->first);
	if (ret)
		goto out;
	if (!owner->first.clocks_held || owner->first.rx_count != 16 ||
	    !owner->first.irq_count || owner->first.irq_count >= 32) {
		ret = -EPROTO;
		goto out;
	}
	if (time_after_eq(jiffies, owner->deadline)) {
		ret = -ETIMEDOUT;
		goto out;
	}
	owner->phase = WMT_PHASE_SET;
	ret = mt6797_wmt_set_prepare(&owner->set, owner->first.btif,
				     owner->first.irq, mt6797_wmt_phase_deadline(owner));
	if (!ret)
		ret = mt6797_wmt_full_exchange(&owner->set);
	if (ret)
		goto out;
	if (time_after_eq(jiffies, owner->deadline)) {
		ret = -ETIMEDOUT;
		goto out;
	}
	owner->phase = WMT_PHASE_SWITCH;
	wmt_full_state_init(&owner->link);
	owner->full_initialized = 1;
	/* Selected source delay, not a measured peer timing guarantee. */
	usleep_range(10000, 11000);
	if (time_after_eq(jiffies, owner->deadline)) {
		ret = -ETIMEDOUT;
		goto out;
	}
	owner->phase = WMT_PHASE_FULL;
	ret = mt6797_wmt_full_prepare(&owner->full, owner->first.btif,
				      owner->first.irq, &owner->link,
				      wmt_stp_full_query, sizeof(wmt_stp_full_query),
				      wmt_stp_full_options, sizeof(wmt_stp_full_options),
				      mt6797_wmt_phase_deadline(owner));
	if (!ret)
		ret = mt6797_wmt_full_exchange(&owner->full);
	if (!ret && time_after_eq(jiffies, owner->deadline))
		ret = -ETIMEDOUT;
	if (!ret)
		owner->phase = WMT_PHASE_DONE;
out:
	owner->result = ret;
	return ret;
}

#endif
