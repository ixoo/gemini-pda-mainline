// SPDX-License-Identifier: GPL-2.0-only
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define __iomem
#define BIT(n) (1U << (n))
#define IRQF_NO_AUTOEN 1
#define IRQ_HANDLED 1
#define IRQ_NONE 0
typedef int irqreturn_t;
typedef int spinlock_t;
struct completion { int complete; };
struct clk { int unused; };
static unsigned long jiffies_value, waited;
static int drift, time_reads;
static unsigned long read_jiffies(void)
{
	if (drift && ++time_reads >= 3)
		return 499 + 2 * (unsigned long)(time_reads - 3);
	return jiffies_value;
}
#define jiffies read_jiffies()
#define msecs_to_jiffies(n) (n)
#define time_after_eq(a, b) ((long)((a) - (b)) >= 0)
#define time_before(a, b) (!time_after_eq(a, b))
#define spin_lock_init(p) (*(p) = 0)
#define spin_lock_irqsave(p, f) ((void)(p), (f) = 0)
#define spin_unlock_irqrestore(p, f) ((void)(p), (void)(f))
static void init_completion(struct completion *c) { c->complete = 0; }
static void complete(struct completion *c) { c->complete = 1; }
static uint32_t btif[64], tx[32], rx[32];
static unsigned char sent[11], response[17];
static unsigned int sent_count, cursor, length, clocks, writes, freed;
static int fail_clock, fail_irq, early_irq, spurious, expire_before_tx;
static irqreturn_t (*handler)(int, void *);
static void *irq_data;
static uint32_t readl(const void *p)
{
	if (p == (unsigned char *)btif + 8)
		return btif[1] && sent_count == 11 && cursor < length ? 4 : 1;
	return *(const uint32_t *)p;
}
static void writel(uint32_t v, void *p)
{
	writes++;
	if (p != (unsigned char *)btif + 8)
		*(uint32_t *)p = v;
}
static unsigned char readb(const void *p)
{
	assert(p == btif && cursor < length);
	return response[cursor++];
}
static void writeb(unsigned char v, void *p)
{
	assert(p == btif && sent_count < 11);
	sent[sent_count++] = v;
	writes++;
}
static int clk_prepare_enable(struct clk *c)
{
	(void)c;
	return ++clocks == (unsigned int)fail_clock ? -EIO : 0;
}
static int request_irq(int irq, irqreturn_t (*fn)(int, void *),
		       int flags, const char *name, void *data)
{
	assert(irq == 130 && flags == IRQF_NO_AUTOEN);
	(void)name;
	handler = fn;
	irq_data = data;
	return fail_irq ? -EBUSY : 0;
}
static void disable_irq_nosync(int irq) { assert(irq == 130); }
static void disable_irq(int irq) { assert(irq == 130); }
static void enable_irq(int irq)
{
	if (early_irq)
		handler(irq, irq_data);
	if (expire_before_tx)
		jiffies_value = 500;
}
static void free_irq(int irq, void *data)
{
	assert(irq == 130 && data == irq_data);
	freed++;
}
static unsigned long wait_for_completion_timeout(struct completion *c,
						 unsigned long timeout)
{
	waited = timeout;
	if (length || spurious)
		handler(130, irq_data);
	if (!c->complete)
		jiffies_value += timeout;
	return c->complete;
}
#include "mt6797-wmt-query.h"
static struct mt6797_wmt_query fresh(void)
{
	static const unsigned char event[] = {
		128, 64, 10, 0, 2, 4, 6, 0, 0, 4, 17, 0, 0, 0, 0, 0
	};
	memset(btif, 0, sizeof(btif));
	memset(tx, 0, sizeof(tx));
	memset(rx, 0, sizeof(rx));
	memcpy(response, event, sizeof(event));
	btif[5] = 0x60;
	sent_count = cursor = clocks = writes = freed = 0;
	fail_clock = fail_irq = early_irq = spurious = expire_before_tx = 0;
	length = sizeof(event);
	jiffies_value = waited = 0;
	drift = time_reads = 0;
	return (struct mt6797_wmt_query) {
		.btif = btif, .dma_tx = tx, .dma_rx = rx, .irq = 130
	};
}
int main(void)
{
	struct mt6797_wmt_query q;
	const unsigned int idle_offsets[] = { 8, 16, 20, 56, 60 };
	unsigned int i, j, before;

	q = fresh();
	assert(!mt6797_wmt_query_once(&q));
	assert(sent_count == 11 && !memcmp(sent, wmt_default_query, 11));
	assert(cursor == 16 && freed == 1 && !btif[1]);
	before = writes;
	assert(mt6797_wmt_query_once(&q) == -EALREADY && writes == before);
	q = fresh();
	q.deadline_supplied = true;
	q.deadline = 0;
	assert(mt6797_wmt_query_once(&q) == -ETIMEDOUT);
	assert(!clocks && !writes && !sent_count && q.attempted);
	q = fresh();
	q.deadline_supplied = true;
	q.deadline = 100;
	assert(mt6797_wmt_query_once(&q) == 0 && q.deadline == 100);
	for (i = 0; i < 2; i++) {
		for (j = 0; j < 5; j++) {
			q = fresh();
			(i ? rx : tx)[idle_offsets[j] / 4] = 1;
			assert(mt6797_wmt_query_once(&q) == -EBUSY);
			assert(!writes && !sent_count);
		}
	}
	for (i = 1; i <= 2; i++) {
		q = fresh();
		fail_clock = i;
		assert(mt6797_wmt_query_once(&q) == -EIO && !writes);
	}
	q = fresh(); btif[5] |= 1;
	assert(mt6797_wmt_query_once(&q) == -EBUSY && writes == 1);
	q = fresh(); btif[19] = 1;
	assert(mt6797_wmt_query_once(&q) == -EBUSY && writes == 1);
	q = fresh(); fail_irq = 1;
	assert(mt6797_wmt_query_once(&q) == -EBUSY && !sent_count);
	q = fresh(); early_irq = 1;
	assert(mt6797_wmt_query_once(&q) == -EBUSY && !sent_count && freed);
	q = fresh(); length = 0;
	assert(mt6797_wmt_query_once(&q) == -ETIMEDOUT && !btif[1] && freed);
	q = fresh(); length = 8;
	assert(mt6797_wmt_query_once(&q) == -ETIMEDOUT && cursor == 8 && freed);
	q = fresh(); response[4] = 3;
	assert(mt6797_wmt_query_once(&q) == -EPROTO && cursor == 5 && freed);
	q = fresh(); length = 17;
	assert(mt6797_wmt_query_once(&q) == -EOVERFLOW && cursor == 16 && freed);
	q = fresh(); length = 0; spurious = 1;
	assert(mt6797_wmt_query_once(&q) == -EPROTO && !cursor && freed);
	q = fresh(); expire_before_tx = 1;
	assert(mt6797_wmt_query_once(&q) == -ETIMEDOUT && !sent_count && freed);
	q = fresh(); q.tx_written = true; q.deadline = 1000; q.irq_count = 31;
	mt6797_wmt_query_irq(130, &q);
	assert(q.terminal && q.result == -ETIMEDOUT && q.irq_count == 32);
	q = fresh(); q.tx_written = true; q.deadline = 1; jiffies_value = 1;
	mt6797_wmt_query_irq(130, &q);
	assert(q.terminal && q.result == -ETIMEDOUT && !cursor);
	q = fresh(); length = 0; drift = 1;
	assert(mt6797_wmt_query_once(&q) == -ETIMEDOUT && waited == 1);
	puts("WMT transport fixtures pass; IRQ concurrency and MMIO semantics not modeled");
}
