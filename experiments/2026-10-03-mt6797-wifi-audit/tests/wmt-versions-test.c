/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#define __iomem
#define MT6797_WMT_VERSION_IO_H
#define time_after_eq(a, b) ((long)((a) - (b)) >= 0)
#define time_before(a, b) ((long)((a) - (b)) < 0)
#define msecs_to_jiffies(ms) ((unsigned long)(ms))
static unsigned long jiffies;
struct mt6797_wmt_version_io { int prepared; unsigned int ordinal; };
static unsigned int preparations, exchanges, fail_prepare, fail_exchange;
static unsigned long duration, pause_before_exchange;
static int fail_result;

static int mt6797_wmt_version_prepare(struct mt6797_wmt_version_io *io,
	void *btif, int irq, unsigned int ordinal, unsigned long deadline)
{
	assert(btif && irq == 130 && ordinal == preparations && ordinal < 3);
	assert(deadline > jiffies && deadline - jiffies <= 500 && deadline <= 1500);
	preparations++;
	if (ordinal == fail_prepare)
		return -EINVAL;
	assert(!io->prepared);
	io->prepared = 1;
	io->ordinal = ordinal;
	return 0;
}
static int mt6797_wmt_version_exchange(struct mt6797_wmt_version_io *io)
{
	assert(io->prepared && io->ordinal == exchanges);
	exchanges++;
	jiffies += pause_before_exchange;
	if (io->ordinal == fail_exchange)
		return fail_result;
	jiffies += duration;
	return 0;
}
#include "mt6797-wmt-versions.h"
static struct mt6797_wmt_versions owner;
static int mapping;
static void fresh(void)
{
	memset(&owner, 0, sizeof(owner));
	owner.btif = &mapping; owner.irq = 130; owner.clocks_held = 1;
	jiffies = preparations = exchanges = 0;
	fail_prepare = fail_exchange = 3;
	fail_result = -EPROTO;
	duration = 100; pause_before_exchange = 0;
}
static int run(void)
{
	int ret = mt6797_wmt_versions_once(&owner);
	unsigned int before = exchanges;

	assert(owner.attempted && owner.result == ret && owner.clocks_held);
	assert(mt6797_wmt_versions_once(&owner) == -EALREADY);
	assert(exchanges == before);
	return ret;
}
int main(void)
{
	unsigned int i;

	fresh(); assert(run() == 0 && preparations == 3 && exchanges == 3 && owner.completed == 3);
	for (i = 0; i < 3; i++) {
		fresh(); fail_prepare = i;
		assert(run() == -EINVAL && owner.completed == i && preparations == i + 1 && exchanges == i);
		fresh(); fail_exchange = i;
		assert(run() == -EPROTO && owner.completed == i && exchanges == i + 1);
		fresh(); fail_exchange = i; fail_result = -ETIMEDOUT;
		assert(run() == -ETIMEDOUT && owner.completed == i && exchanges == i + 1);
	}
	fresh(); duration = 499;
	assert(run() == 0 && jiffies == 1497 && owner.completed == 3);
	/* Simulate process scheduling delay after a successfully checked leaf. */
	fresh(); duration = 500;
	assert(run() == -ETIMEDOUT && owner.completed == 2 && jiffies == 1500);
	fresh(); duration = 501;
	assert(run() == -ETIMEDOUT && owner.completed == 2 && jiffies == 1503);
	fresh(); duration = 1500;
	assert(run() == -ETIMEDOUT && owner.completed == 0 && exchanges == 1);
	fresh(); owner.reads[1].prepared = 1;
	assert(mt6797_wmt_versions_once(&owner) == -EALREADY && !exchanges);
	fresh(); owner.clocks_held = 0;
	assert(mt6797_wmt_versions_once(&owner) == -EINVAL && !owner.attempted && !exchanges);
	fresh(); owner.irq = 0;
	assert(mt6797_wmt_versions_once(&owner) == -EINVAL && !exchanges);
	fresh(); owner.btif = NULL;
	assert(mt6797_wmt_versions_once(&owner) == -EINVAL && !exchanges);
	assert(mt6797_wmt_versions_once(NULL) == -EINVAL);
	puts("version owner: order, first-error stop, retained lifetime, deadlines and no retry pass; leaves mocked");
	return 0;
}
