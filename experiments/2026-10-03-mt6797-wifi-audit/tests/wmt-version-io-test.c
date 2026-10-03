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
#define msecs_to_jiffies(ms) ((unsigned long)(ms))
static uint32_t registers[32];
static unsigned char incoming[33], outgoing[26];
static unsigned int written, read_count, input_length, fifo_used, ier;
static unsigned int irq_depth, requested, enabled, disabled, joined, freed;
static unsigned int expire_at, expire_read, stuck, early, preset_rx, expire_enable;
static unsigned int rx_step, rx_available, expire_final_iir;
static int request_error;
static irqreturn_t (*handler)(int, void *);
static void *handler_data;
static int request_irq(int irq, irqreturn_t (*fn)(int, void *),
	unsigned long flags, const char *name, void *data)
{
	assert(irq == 130 && flags == IRQF_NO_AUTOEN && fn && name && data);
	requested++;
	if (request_error)
		return request_error;
	irq_depth = 1;
	handler = fn;
	handler_data = data;
	return 0;
}
static void disable_irq_nosync(int irq)
{
	assert(irq == 130 && irq_depth == 0);
	irq_depth++;
	disabled++;
}
static void enable_irq(int irq)
{
	assert(irq == 130 && irq_depth == 1);
	irq_depth--;
	enabled++;
	if (expire_enable) {
		jiffies = 500;
		handler(irq, handler_data);
	}
}
static void synchronize_irq(int irq)
{
	assert(irq == 130 && irq_depth == 1);
	joined++;
}
static void free_irq(int irq, void *data)
{
	assert(irq == 130 && data && irq_depth == 1 && joined == 1);
	freed++;
}
static unsigned long wait_for_completion_timeout(struct completion *, unsigned long);
static uint32_t readl(const void *p)
{
	if (p == (unsigned char *)registers + 8) {
		if (expire_final_iir && read_count == 22)
			jiffies = 500;
		return (read_count < (rx_step ? rx_available : input_length) && (ier & 1) &&
		       (preset_rx || written == 26 || (early && written)) ? 4 : 0) |
		       ((ier & 2) && (fifo_used <= 8 || stuck) ? 2 : 0);
	}
	assert(p == (unsigned char *)registers + 0x14);
	if (stuck && written)
		return 0;
	return !fifo_used ? 0x60 : fifo_used <= 8 ? 0x20 : 0;
}
static void writel(uint32_t value, void *p)
{
	assert(p == (unsigned char *)registers + 4 && value <= 3);
	ier = value;
}
static unsigned char readb(const void *p)
{
	assert(p == registers && read_count < input_length);
	if (expire_read && read_count + 1 == expire_read)
		jiffies = 500;
	return incoming[read_count++];
}
static void writeb(unsigned char value, void *p)
{
	assert(p == registers && fifo_used < 16 && written < sizeof(outgoing));
	outgoing[written++] = value;
	fifo_used++;
	if (expire_at && written == expire_at)
		jiffies = 500;
}
#include "mt6797-wmt-version-io.h"
static struct mt6797_wmt_version_io io;
static unsigned long wait_for_completion_timeout(struct completion *done,
	unsigned long remaining)
{
	unsigned int iterations = 0, before;

	assert(done == &io.done && remaining <= 500);
	while (!done->complete && ++iterations < 70) {
		fifo_used = fifo_used > 8 ? fifo_used - 8 : 0;
		jiffies++;
		if (rx_step && written == 26) {
			rx_available += rx_step;
			if (rx_available > input_length)
				rx_available = input_length;
		}
		if (!(readl((unsigned char *)registers + 8) & 0x46))
			break;
		assert(irq_depth == 0);
		before = read_count;
		assert(handler(130, handler_data) == IRQ_HANDLED);
		assert(read_count - before <= 8);
	}
	assert(iterations < 70);
	if (!done->complete)
		jiffies = 500;
	return done->complete;
}
static void fresh(unsigned int ordinal)
{
	memset(&io, 0, sizeof(io));
	memset(outgoing, 0, sizeof(outgoing));
	written = read_count = input_length = fifo_used = ier = 0;
	irq_depth = requested = enabled = disabled = joined = freed = 0;
	expire_at = expire_read = stuck = early = preset_rx = expire_enable = 0;
	request_error = 0;
	rx_step = rx_available = expire_final_iir = 0;
	jiffies = 0;
	assert(mt6797_wmt_version_prepare(&io, registers, 130, ordinal, 500) == 0);
}
static int capture(void)
{
	int result = mt6797_wmt_version_exchange(&io);
	unsigned int writes = written, reads = read_count;

	assert(io.terminal && io.attempted && io.done.complete);
	assert(io.rx_count == read_count && io.tx_count == written);
	assert(io.tx.written == written);
	assert(written <= 26 && read_count <= 22 && io.services <= 64);
	if (!request_error)
		assert(!ier && joined == 1 && freed == 1 && irq_depth == 1);
	assert(mt6797_wmt_version_exchange(&io) == -EINVAL);
	mt6797_wmt_version_service(&io, 0);
	assert(written == writes && read_count == reads);
	return result;
}
static void reply(unsigned int ordinal)
{
	memset(incoming, 0, sizeof(incoming));
	incoming[0] = 0x80; incoming[1] = 0x40; incoming[2] = 16;
	incoming[4] = 2; incoming[5] = 8; incoming[6] = 12;
	incoming[11] = 1; incoming[12] = ordinal == 0 ? 8 : ordinal == 1 ? 0 : 4;
	incoming[15] = 0x80;
	incoming[16] = ordinal == 0 ? 0x79 : 0;
	incoming[17] = ordinal == 0 ? 2 : 0x8a;
	input_length = 22;
}

int main(void)
{
	unsigned int i, byte, ordinal, refusals = 0;
	unsigned char expected[26], original;

	for (ordinal = 0; ordinal < 3; ordinal++) {
		fresh(ordinal);
		assert(wmt_identity_read(ordinal, expected, sizeof(expected)) == 26);
		reply(ordinal);
		assert(capture() == 0 && written == 26 && read_count == 22 && disabled == 1);
		assert(!memcmp(outgoing, expected, sizeof(expected)));
		/* Corrupt each byte independently through the actual IRQ/MMIO path. */
		for (i = 0; i < 22; i++)
			for (byte = 0; byte < 256; byte++) {
				fresh(ordinal);
				reply(ordinal); original = incoming[i];
				if (byte == original)
					continue;
				incoming[i] = (unsigned char)byte;
				assert(capture() == -EPROTO && read_count == 22);
				refusals++;
			}
	}
	for (i = 1; i <= 22; i++) {
		fresh(0); reply(0); rx_step = i;
		assert(capture() == 0 && read_count == 22);
	}
	/* Last reply byte at quota boundary, with a queued trailing byte. */
	fresh(0); reply(0); input_length = 23; rx_step = 7;
	assert(capture() == -EPROTO && read_count == 22);
	fresh(0); reply(0); expire_final_iir = 1;
	assert(capture() == -ETIMEDOUT && read_count == 22);
	for (i = 1; i <= 26; i++) {
		fresh(0); reply(0); expire_at = i;
		assert(capture() == -ETIMEDOUT && written == i && !read_count);
	}
	for (i = 1; i <= 22; i++) {
		fresh(0); reply(0); expire_read = i;
		assert(capture() == -ETIMEDOUT && written == 26 && read_count == i);
	}
	for (i = 0; i < 22; i++) {
		fresh(0); reply(0); input_length = i;
		assert(capture() == -ETIMEDOUT && read_count == i);
	}
	fresh(0); reply(0); input_length = 23;
	assert(capture() == -EPROTO && read_count == 22);
	fresh(0); jiffies = 500;
	assert(capture() == -ETIMEDOUT && !written && !read_count && !enabled);
	fresh(0); early = 1; reply(0);
	assert(capture() == -EPROTO && written == 16 && !read_count);
	fresh(0); preset_rx = 1; reply(0);
	assert(capture() == -EPROTO && !written && !read_count && !enabled);
	fresh(0); stuck = 1;
	assert(capture() == -ETIMEDOUT && io.services == 64 && written == 16);
	fresh(0); expire_enable = 1;
	assert(capture() == -ETIMEDOUT && written == 16 && disabled == 1);
	fresh(0); request_error = -EBUSY;
	assert(capture() == -EBUSY && !written && !ier && !joined && !freed);
	fresh(0); fifo_used = 1;
	assert(capture() == -EBUSY && !written && !read_count);
	fresh(0);
	assert(mt6797_wmt_version_irq(129, &io) == IRQ_NONE && !io.services);
	assert(mt6797_wmt_version_prepare(&io, registers, 130, 0, 500) == -EBUSY);
	memset(&io, 0, sizeof(io));
	assert(mt6797_wmt_version_prepare(&io, registers, 130, 0, 501) == -EINVAL);
	assert(mt6797_wmt_version_prepare(&io, registers, 130, 0, 0) == -EINVAL);
	assert(mt6797_wmt_version_prepare(&io, NULL, 130, 0, 500) == -EINVAL);
	assert(mt6797_wmt_version_prepare(&io, registers, 130, 3, 500) == -EINVAL);
	printf("checked version IO: 3 variants; %u corruptions; finite TX/RX/IRQ failure fixtures pass\n", refusals);
	return 0;
}
