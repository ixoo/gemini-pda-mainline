// SPDX-License-Identifier: GPL-2.0-only
#include <assert.h>
#include <errno.h>
#include <limits.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "wmt-full-stp-state.h"
#include "wmt-stp-options.h"

/* Real orchestration with mocked leaf exchanges. Actual FIFO/IRQ leaves are
 * independently exercised by wmt-full-io-test and wmt-query-transport-test.
 */
#define MT6797_WMT_QUERY_H
#define MT6797_WMT_FULL_IO_H
struct mt6797_wmt_query {
	void *btif, *dma_tx, *dma_rx, *btif_clk, *dma_clk;
	int irq, attempted, clocks_held;
	unsigned int rx_count, irq_count;
	unsigned long deadline;
	bool deadline_supplied;
};
struct mt6797_wmt_full_io { int prepared; unsigned long deadline; };
static unsigned long jiffies, durations[3];
static unsigned int calls, sleeps, bad_observation;
static int failed_step;
#define msecs_to_jiffies(n) (n)
#define time_after_eq(a, b) ((long)((a) - (b)) >= 0)
#define time_before(a, b) (!time_after_eq(a, b))
static int mt6797_wmt_query_once(struct mt6797_wmt_query *q)
{
	assert(!calls && !q->attempted && q->deadline_supplied);
	assert(time_before(jiffies, q->deadline));
	q->attempted = 1;
	calls++;
	q->clocks_held = 1;
	q->rx_count = bad_observation ? 15 : 16;
	q->irq_count = 2;
	jiffies += durations[0];
	return failed_step == 1 ? -EIO : 0;
}
static int mt6797_wmt_set_prepare(struct mt6797_wmt_full_io *io,
		void *btif, int irq, unsigned long deadline)
{
	assert(calls == 1 && !io->prepared && btif && irq == 130);
	io->prepared = 1;
	io->deadline = deadline;
	return 0;
}
static int mt6797_wmt_full_prepare(struct mt6797_wmt_full_io *io,
		void *btif, int irq, struct wmt_full_state *link,
		const unsigned char *command, unsigned int length,
		const unsigned char *event, unsigned int event_length,
		unsigned long deadline)
{
	assert(calls == 2 && sleeps == 1 && !io->prepared && btif && irq == 130);
	assert(!link->tx_next && !link->rx_next && !link->active);
	assert(link->peer_ack == 7 && link->local_ack == 7);
	assert(length == 5 && event_length == 10);
	assert(!memcmp(command, wmt_stp_full_query, length));
	assert(!memcmp(event, wmt_stp_full_options, event_length));
	io->prepared = 1;
	io->deadline = deadline;
	return 0;
}
static int mt6797_wmt_full_exchange(struct mt6797_wmt_full_io *io)
{
	assert(io->prepared && calls >= 1 && calls < 3);
	assert(time_before(jiffies, io->deadline));
	jiffies += durations[calls];
	calls++;
	return failed_step == (int)calls ? -EIO : 0;
}
static void usleep_range(unsigned long minimum, unsigned long maximum)
{
	assert(calls == 2 && minimum == 10000 && maximum == 11000);
	sleeps++;
	jiffies += 10;
}
#include "mt6797-wmt-negotiate.h"
static struct mt6797_wmt_negotiate owner;
static unsigned char mappings;
static void fresh(void)
{
	memset(&owner, 0, sizeof(owner));
	owner.first.btif = owner.first.dma_tx = owner.first.dma_rx = &mappings;
	owner.first.btif_clk = owner.first.dma_clk = &mappings;
	owner.first.irq = 130;
	jiffies = calls = sleeps = bad_observation = failed_step = 0;
	durations[0] = durations[1] = durations[2] = 20;
}
int main(void)
{
	unsigned int i;

	fresh();
	assert(mt6797_wmt_negotiate_once(&owner) == 0);
	assert(calls == 3 && sleeps == 1 && owner.phase == WMT_PHASE_DONE);
	assert(owner.full_initialized && owner.set.prepared && owner.full.prepared);
	assert(mt6797_wmt_negotiate_once(&owner) == -EALREADY && calls == 3);
	for (i = 1; i <= 3; i++) {
		fresh();
		failed_step = i;
		assert(mt6797_wmt_negotiate_once(&owner) == -EIO);
		assert(calls == i && sleeps == (i == 3));
		assert(owner.phase == (i == 1 ? WMT_PHASE_DEFAULT :
				      i == 2 ? WMT_PHASE_SET : WMT_PHASE_FULL));
		assert(owner.full_initialized == (i == 3));
		assert(mt6797_wmt_negotiate_once(&owner) == -EALREADY && calls == i);
	}
	fresh();
	bad_observation = 1;
	assert(mt6797_wmt_negotiate_once(&owner) == -EPROTO && calls == 1);
	assert(!sleeps && !owner.set.prepared && !owner.full_initialized);
	fresh();
	durations[0] = 1600;
	assert(mt6797_wmt_negotiate_once(&owner) == -ETIMEDOUT && calls == 1);
	fresh();
	durations[1] = 1580;
	assert(mt6797_wmt_negotiate_once(&owner) == -ETIMEDOUT && calls == 2);
	assert(!sleeps && !owner.full_initialized);
	fresh();
	durations[1] = 1575;
	assert(mt6797_wmt_negotiate_once(&owner) == -ETIMEDOUT && calls == 2);
	assert(sleeps == 1 && owner.phase == WMT_PHASE_SWITCH);
	fresh();
	durations[2] = 1550;
	assert(mt6797_wmt_negotiate_once(&owner) == -ETIMEDOUT && calls == 3);
	assert(owner.phase == WMT_PHASE_FULL);
	fresh();
	jiffies = ULONG_MAX - 20;
	assert(mt6797_wmt_negotiate_once(&owner) == 0 && calls == 3);
	fresh();
	owner.first.btif = NULL;
	assert(mt6797_wmt_negotiate_once(&owner) == -EINVAL && !calls);
	assert(!owner.attempted);
	puts("negotiation_order_budget_failure_retention=pass; leaf_transport=mocked");
	return 0;
}
