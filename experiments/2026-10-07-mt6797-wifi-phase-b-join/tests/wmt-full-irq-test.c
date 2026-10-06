/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define __iomem
#define IRQ_NONE 0
#define IRQ_HANDLED 1
#define IRQF_NO_AUTOEN 1
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
static unsigned int irq_depth, requested, enabled, synchronized, freed, wait_mode;
static int request_result, expire_on_enable, set_mutation, set_extra;
static int forced_iir = -1;
static irqreturn_t (*registered_handler)(int, void *);
static void *registered_data;
static int request_irq(int irq, irqreturn_t (*handler)(int, void *),
	unsigned long flags, const char *name, void *data)
{
	assert(irq == 130 && handler && flags == IRQF_NO_AUTOEN && name && data);
	requested++;
	registered_handler = handler;
	registered_data = data;
	if (!request_result)
		irq_depth = 1;
	return request_result;
}
static void disable_irq_nosync(int irq)
{
	assert(irq == 130);
	disabled++;
	irq_depth++;
}
static void enable_irq(int irq)
{
	assert(irq == 130 && irq_depth == 1);
	irq_depth--;
	enabled++;
	if (expire_on_enable) {
		jiffies = 1000;
		registered_handler(irq, registered_data);
	}
}
static void synchronize_irq(int irq)
{
	assert(irq == 130 && irq_depth == 1);
	synchronized++;
}
static void free_irq(int irq, void *data)
{
	assert(irq == 130 && data && irq_depth == 1);
	freed++;
}
static unsigned long wait_for_completion_timeout(struct completion *, unsigned long);
static uint32_t readl(const void *p)
{
	if (p == (unsigned char *)registers + 8 && forced_iir >= 0)
		return (unsigned int)forced_iir;
	if (p == (unsigned char *)registers + 8 && expire_on_empty &&
	    ((expire_on_empty == 1 && written == 1015) ||
	     (expire_on_empty == 2 && written == 15)) && read_count == input_length)
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
static const unsigned char set_response[12] = {
	0x80, 0x40, 0x06, 0x00, 0x02, 0x04, 0x02, 0x00,
	0x00, 0x03, 0x00, 0x00
};

static void fresh(void)
{
	unsigned int i;

	memset(&io, 0, sizeof(io));
	for (i = 0; i < sizeof(command); i++)
		command[i] = i;
	written = read_count = input_length = fifo_used = disabled = expire_at = stuck = expire_on_empty = 0;
	service_calls = 0;
	irq_depth = requested = enabled = synchronized = freed = wait_mode = 0;
	request_result = expire_on_enable = set_mutation = set_extra = 0;
	forced_iir = -1;
	jiffies = 0;
	ier = 3;
	wmt_full_state_init(&link);
	assert(mt6797_wmt_full_prepare(&io, registers, 130, &link,
		command, sizeof(command), event, sizeof(event), 1000) == 0);
}

static void fresh_set(void)
{
	fresh();
	memset(&io, 0, sizeof(io));
	assert(mt6797_wmt_set_prepare(&io, registers, 130, 1000) == 0);
}

static void service(void)
{
	unsigned int before = read_count;

	assert(++service_calls <= 1024);
	/* Independently modeled hardware drains eight bytes between services. */
	fifo_used = fifo_used > 8 ? fifo_used - 8 : 0;
	jiffies++;
	if (!io.terminal)
		io.irq_armed = 1;
	assert(mt6797_wmt_full_irq(130, &io) == IRQ_HANDLED);
	assert(read_count - before <= WMT_FULL_IO_RX_QUOTA);
}

static unsigned long wait_for_completion_timeout(struct completion *done,
	unsigned long remaining)
{
	assert(done == &io.done && remaining <= io.deadline);
	if (done->complete) {
		assert(irq_depth == 1);
		return 1;
	}
	assert(irq_depth == 0);
	if (!wait_mode) {
		jiffies = io.deadline;
		return 0;
	}
	while (!io.sent && !io.terminal)
		service();
	if (io.mandatory_set) {
		memcpy(incoming, set_response, sizeof(set_response));
		input_length = sizeof(set_response);
		if (set_mutation)
			incoming[8] = 1;
		if (set_extra)
			incoming[input_length++] = 0;
	} else {
		input_length = wmt_full_encode(incoming, sizeof(incoming),
			event, sizeof(event), 0, 0);
	}
	while (!io.terminal)
		service();
	return io.done.complete ? 1 : 0;
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

	/* Already-delivered no-source IRQ cannot transmit a suffix or retire. */
	fresh();
	mt6797_wmt_full_service(&io, 1);
	assert(written == 16 && !io.sent && !link.active);
	forced_iir = 1;
	service();
	assert(!io.terminal && io.services == 2 && io.no_source_services == 1);
	assert(io.last_iir == 1 && written == 16 && !read_count && !link.active);
	forced_iir = -1;
	while (!io.sent && !io.terminal)
		service();
	assert(io.sent && written == 1011 && link.active);
	/* Same race after command submission, while awaiting the reply. */
	forced_iir = 1;
	before = written;
	service();
	assert(!io.terminal && written == before && !read_count);
	assert(io.no_source_services == 2 && !link.acknowledged && !link.event_seen);
	forced_iir = -1;
	input_length = wmt_full_encode(incoming, sizeof(incoming), event, sizeof(event), 0, 0);
	while (!io.terminal)
		service();
	assert(io.result == 0 && written == 1015 && io.rx_count == 11);
	assert(io.no_source_services == 2 && !link.active);
	/* A pending unsupported cause is still a protocol refusal. */
	fresh();
	mt6797_wmt_full_service(&io, 1);
	forced_iir = 0;
	service();
	assert(io.result == -EPROTO && written == 16 && !read_count);
	assert(io.last_iir == 0 && !io.no_source_services && !io.sent);
	/* No-source storms retain the original total service budget. */
	fresh();
	mt6797_wmt_full_service(&io, 1);
	forced_iir = 1;
	while (!io.terminal)
		service();
	assert(io.result == -ETIMEDOUT && written == 16 && !read_count);
	assert(io.services == WMT_FULL_IO_SERVICES &&
	       io.no_source_services == WMT_FULL_IO_SERVICES - 1 && !io.sent);
	/* Expiry is checked before another no-source observation or FIFO write. */
	fresh();
	mt6797_wmt_full_service(&io, 1);
	forced_iir = 1;
	jiffies = io.deadline;
	service();
	assert(io.result == -ETIMEDOUT && written == 16 && !read_count);
	assert(!io.no_source_services && io.services == 1);
	forced_iir = -1;
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
	/* Actual caller joins/frees once, with balanced CPU IRQ depth. */
	fresh();
	wait_mode = 1;
	assert(mt6797_wmt_full_exchange(&io) == 0);
	assert(requested == 1 && enabled == 1 && disabled == 1);
	assert(synchronized == 1 && freed == 1 && irq_depth == 1);
	assert(io.terminal && !io.irq_armed && !link.active && written == 1015);
	assert(mt6797_wmt_full_exchange(&io) == -EINVAL && requested == 1);
	fresh();
	assert(mt6797_wmt_full_exchange(&io) == -ETIMEDOUT);
	assert(enabled == 1 && disabled == 1 && synchronized == 1 && freed == 1);
	assert(io.terminal && written == 16 && io.tx.written == 16);
	fresh();
	expire_at = 7;
	assert(mt6797_wmt_full_exchange(&io) == -ETIMEDOUT);
	assert(!enabled && !disabled && irq_depth == 1);
	assert(synchronized == 1 && freed == 1 && written == 7);
	fresh();
	input_length = 1;
	assert(mt6797_wmt_full_exchange(&io) == -EPROTO);
	assert(!enabled && !disabled && !written && !read_count && freed == 1);
	fresh();
	expire_on_enable = 1;
	assert(mt6797_wmt_full_exchange(&io) == -ETIMEDOUT);
	assert(enabled == 1 && disabled == 1 && synchronized == 1 && freed == 1);
	assert(io.terminal && written == 16 && !io.irq_armed);
	fresh();
	request_result = -EBUSY;
	assert(mt6797_wmt_full_exchange(&io) == -EBUSY);
	assert(requested == 1 && !enabled && !disabled && !synchronized && !freed);
	assert(!io.services && !written && ier == 3);
	/* Full-mode query after a separately checked set uses the existing ACK path. */
	fresh();
	memset(&io, 0, sizeof(io));
	assert(mt6797_wmt_full_prepare(&io, registers, 130, &link,
		wmt_stp_full_query, sizeof(wmt_stp_full_query), wmt_stp_full_options,
		sizeof(wmt_stp_full_options), 1000) == 0);
	mt6797_wmt_full_service(&io, 1);
	input_length = wmt_full_encode(incoming, sizeof(incoming), wmt_stp_full_options,
		sizeof(wmt_stp_full_options), 0, 0);
	while (!io.terminal)
		service();
	assert(io.result == 0 && written == 15 && io.rx_count == 16);
	assert(link.transport.tx_next == 1 && link.transport.rx_next == 1 && !link.active);
	/* Fixed mandatory set uses the same bounded FIFO/IRQ owner, no host ACK. */
	fresh_set();
	wait_mode = 1;
	assert(mt6797_wmt_full_exchange(&io) == 0);
	assert(io.tx_count == 15 && io.rx_count == 12 && io.frames == 1);
	assert(written == 15 && !memcmp(outgoing, wmt_stp_set_options, 15));
	assert(!io.ack_phase && !link.active && io.set_reply.received == 12);
	assert(enabled == 1 && disabled == 1 && synchronized == 1 && freed == 1);
	assert(mt6797_wmt_set_prepare(&io, registers, 130, 2000) == -EBUSY);
	assert(mt6797_wmt_full_exchange(&io) == -EINVAL && requested == 1);
	fresh_set();
	wait_mode = set_mutation = 1;
	assert(mt6797_wmt_full_exchange(&io) == -EPROTO);
	assert(written == 15 && io.set_reply.failed && irq_depth == 1);
	fresh_set();
	wait_mode = set_extra = 1;
	assert(mt6797_wmt_full_exchange(&io) == -EPROTO && written == 15);
	assert(!io.ack_phase && synchronized == 1 && freed == 1);
	fresh_set();
	expire_at = 7;
	assert(mt6797_wmt_full_exchange(&io) == -ETIMEDOUT);
	assert(written == 7 && !enabled && !disabled && irq_depth == 1);
	fresh_set();
	assert(mt6797_wmt_full_exchange(&io) == -ETIMEDOUT);
	assert(written == 15 && !read_count && irq_depth == 1);
	fresh_set();
	input_length = 1;
	assert(mt6797_wmt_full_exchange(&io) == -EPROTO);
	assert(!written && !read_count && !enabled && !disabled);
	fresh_set();
	wait_mode = 1;
	expire_on_empty = 2;
	assert(mt6797_wmt_full_exchange(&io) == -ETIMEDOUT);
	assert(io.rx_count == 12 && written == 15 && !io.frames);
	fresh_set();
	mt6797_wmt_full_service(&io, 1);
	memset(incoming, 0, sizeof(incoming));
	memcpy(incoming, set_response, sizeof(set_response));
	input_length = 32;
	while (!io.terminal)
		service();
	assert(io.rx_count == WMT_SET_IO_RX_BYTES && written == 15);
	assert(io.result == -EOVERFLOW && !io.ack_phase);
	fresh_set();
	fifo_used = 1;
	assert(mt6797_wmt_full_exchange(&io) == -EBUSY);
	assert(!written && !enabled && !disabled && freed == 1);
	fresh_set();
	io.services = WMT_SET_IO_SERVICES;
	mt6797_wmt_full_service(&io, 0);
	assert(io.result == -ETIMEDOUT && !written && !read_count);
	fresh_set();
	request_result = -EBUSY;
	assert(mt6797_wmt_full_exchange(&io) == -EBUSY);
	assert(!written && !io.services && !synchronized && !freed);
	puts("full_stp_io_draft=pass; irq_lifecycle=pass; hardware_actions=none");
	return 0;
}
