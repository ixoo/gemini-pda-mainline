/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define __iomem
#define IRQ_NONE 0
#define IRQ_HANDLED 1
typedef int irqreturn_t;
typedef int spinlock_t;
struct completion { int complete; };
#define spin_lock_init(p) (*(p) = 0)
#define spin_lock_irqsave(p, f) ((void)(p), (f) = 0)
#define spin_unlock_irqrestore(p, f) ((void)(p), (void)(f))
static void init_completion(struct completion *c) { c->complete = 0; }
static void complete(struct completion *c) { c->complete = 1; }
static unsigned long jiffies;
#define time_after_eq(a, b) ((long)((a) - (b)) >= 0)
static uint32_t registers[32];
static unsigned char outgoing[1200], incoming[1200];
static unsigned int written, read_count, input_length, fifo_used, disabled, ier;
static unsigned int expire_at, stuck, expire_on_empty, service_calls;
static void disable_irq_nosync(int irq) { assert(irq == 130); disabled++; }
static uint32_t readl(const void *p)
{
	if (p == (unsigned char *)registers + 8 && expire_on_empty &&
	    written == 1015 && read_count == input_length)
		jiffies = 1000;
	if (p == (unsigned char *)registers + 8)
		return (read_count < input_length && (ier & 1) ? 4 : 0) |
		       ((ier & 2) && fifo_used <= 8 ? 2 : 0) |
		       (read_count >= input_length && !(ier & 2) ? 1 : 0);
	assert(p == (unsigned char *)registers + 0x14);
	return stuck ? 0 : !fifo_used ? 0x60 : fifo_used <= 8 ? 0x20 : 0;
}
static void writel(uint32_t value, void *p)
{
	assert(p == (unsigned char *)registers + 4 && value <= 3);
	ier = value;
}
static unsigned char readb(const void *p)
{
	assert(p == registers && read_count < input_length);
	return incoming[read_count++];
}
static void writeb(unsigned char value, void *p)
{
	assert(p == registers && fifo_used < 16 && written < sizeof(outgoing));
	outgoing[written++] = value;
	fifo_used++;
	if (expire_at && written == expire_at)
		jiffies = 1000;
}
#include "mt6797-wmt-full-io.h"
static struct mt6797_wmt_full_io io;
static struct wmt_full_state link;
static unsigned char command[1005];
static const unsigned char event[] = { 2, 1, 1, 0, 0 };

static void fresh(void)
{
	unsigned int i;

	memset(&io, 0, sizeof(io));
	for (i = 0; i < sizeof(command); i++)
		command[i] = i;
	written = read_count = input_length = fifo_used = disabled = expire_at = stuck = expire_on_empty = 0;
	service_calls = 0;
	jiffies = 0;
	ier = 3;
	wmt_full_state_init(&link);
	assert(mt6797_wmt_full_prepare(&io, registers, 130, &link,
		command, sizeof(command), event, sizeof(event), 1000) == 0);
}

static void service(void)
{
	unsigned int before = read_count;

	assert(++service_calls <= 1024);
	/* Independently modeled hardware drains eight bytes between services. */
	fifo_used = fifo_used > 8 ? fifo_used - 8 : 0;
	jiffies++;
	assert(mt6797_wmt_full_irq(130, &io) == IRQ_HANDLED);
	assert(read_count - before <= WMT_FULL_IO_RX_QUOTA);
}

int main(void)
{
	unsigned int i, before;
	int length;

	fresh();
	assert(mt6797_wmt_full_irq(129, &io) == IRQ_NONE && !io.services);
	mt6797_wmt_full_service(&io, 1);
	assert(written == 16 && !link.active);
	while (!io.sent && !io.terminal)
		service();
	assert(io.sent && written == 1011 && link.active);
	assert(!memcmp(outgoing, io.command, 1011));
	/* Exact event with old ACK, then separately arriving command ACK. */
	length = wmt_full_encode(incoming, sizeof(incoming), event, sizeof(event), 0, 7);
	input_length = length;
	while (!link.event_seen && !io.terminal)
		service();
	assert(link.event_seen && !io.terminal && !link.acknowledged);
	assert(wmt_full_ack(incoming + input_length, sizeof(incoming) - input_length, 0) == 4);
	input_length += 4;
	while (!io.terminal)
		service();
	assert(io.result == 0 && io.done.complete && disabled == 1);
	assert(io.tx_count == 1015 && io.rx_count == 15 && io.frames == 2);
	assert(written == 1015 && !link.active);
	assert(!memcmp(outgoing + 1011, io.ack, 4));
	before = written;
	service();
	assert(written == before && disabled == 1);

	/* RX stays pending, but a bounded drain still lets TX progress. */
	fresh();
	mt6797_wmt_full_service(&io, 1);
	memset(incoming, 0, sizeof(incoming));
	input_length = sizeof(incoming);
	while (!io.terminal)
		service();
	assert(written == 1011 && io.result == -EPROTO && io.rx_count > 8);
	/* RX total exhaustion stops before an out-of-bounds read. */
	fresh();
	mt6797_wmt_full_service(&io, 1);
	stuck = 1;
	input_length = sizeof(incoming);
	while (!io.terminal)
		service();
	assert(io.result == -EOVERFLOW && io.rx_count == WMT_FULL_IO_RX_BYTES);
	/* Deadline during a batch preserves exact partial-write evidence. */
	fresh();
	expire_at = 7;
	mt6797_wmt_full_service(&io, 1);
	assert(io.result == -ETIMEDOUT && written == 7 && io.tx.written == 7);
	assert(!io.sent && !link.active && !read_count);
	assert(mt6797_wmt_full_prepare(&io, registers, 130, &link,
		command, sizeof(command), event, sizeof(event), 2000) == -EBUSY);
	assert(written == 7 && io.tx.written == 7);
	/* Timeout after submission cannot fabricate an event or credit. */
	fresh();
	mt6797_wmt_full_service(&io, 1);
	while (!io.sent && !io.terminal)
		service();
	assert(io.sent);
	jiffies = io.deadline;
	mt6797_wmt_full_service(&io, 0);
	assert(io.result == -ETIMEDOUT && link.active && !link.event_seen);
	/* Expiry at the final FIFO check cannot turn a late exchange into success. */
	fresh();
	mt6797_wmt_full_service(&io, 1);
	while (!io.sent && !io.terminal)
		service();
	assert(io.sent);
	input_length = wmt_full_encode(incoming, sizeof(incoming), event, sizeof(event), 0, 0);
	expire_on_empty = 1;
	while (!io.terminal)
		service();
	assert(io.result == -ETIMEDOUT && link.active && link.event_seen);
	/* Queued extra byte after a matched event prevents successful retirement. */
	fresh();
	mt6797_wmt_full_service(&io, 1);
	while (!io.sent && !io.terminal)
		service();
	assert(io.sent);
	input_length = wmt_full_encode(incoming, sizeof(incoming), event, sizeof(event), 0, 0);
	incoming[input_length++] = 0;
	while (!io.terminal)
		service();
	assert(io.result == -EPROTO && written == 1011);
	for (i = 0; i < 3; i++) {
		before = written;
		service();
		assert(written == before);
	}
	/* Preexisting RX refuses the initial kick before any THR write. */
	fresh();
	input_length = 1;
	mt6797_wmt_full_service(&io, 1);
	assert(io.result == -EPROTO && !written && !read_count);
	/* Aggregate service budget retires before another read or write. */
	fresh();
	io.services = WMT_FULL_IO_SERVICES;
	mt6797_wmt_full_service(&io, 0);
	assert(io.result == -ETIMEDOUT && !written && !read_count);
	puts("full_stp_io_draft=pass; hardware_actions=none");
	return 0;
}
