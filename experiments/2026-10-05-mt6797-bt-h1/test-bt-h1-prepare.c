/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * Prepare-level check of the actual full-STP I/O header for both tasks.
 * C3-2 failed here: a task-0 HCI Reset was refused before any byte was sent.
 */
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
static uint32_t readl(const volatile void *p) { (void)p; return 0; }
static void writel(uint32_t v, volatile void *p) { (void)v; (void)p; }
static uint8_t readb(const volatile void *p) { (void)p; return 0; }
static void writeb(uint8_t v, volatile void *p) { (void)v; (void)p; }
static int request_irq(int irq, irqreturn_t (*h)(int, void *), unsigned long f,
		       const char *n, void *d)
{ (void)irq; (void)h; (void)f; (void)n; (void)d; return -1; }
static void free_irq(int irq, void *d) { (void)irq; (void)d; }
static void enable_irq(int irq) { (void)irq; }
static void disable_irq_nosync(int irq) { (void)irq; }
static void synchronize_irq(int irq) { (void)irq; }
static unsigned long wait_for_completion_timeout(struct completion *c, unsigned long t)
{ (void)c; return t; }
#include "mt6797-wmt-full-io.h"

static struct mt6797_wmt_full_io io;
static struct wmt_full_state link;
static unsigned char window[64];

int main(void)
{
	static const unsigned char reset[] = { 0x01, 0x03, 0x0c, 0x00 };
	static const unsigned char reset_event[] = { 0x04, 0x0e, 0x04, 0x01, 0x03, 0x0c, 0x00 };
	static const unsigned char bt_on[] = { 0x01, 0x06, 0x02, 0x00, 0x00, 0x01 };
	static const unsigned char func_event[] = { 0x02, 0x06, 0x01, 0x00, 0x00 };
	struct stp_full_frame frame;

	/* Link state after C3-2's successful BT-on: tx 2, rx 2, ACK 1/1. */
	wmt_full_state_init(&link);
	link.transport.tx_next = 2;
	link.transport.rx_next = 2;
	link.transport.peer_ack = 1;
	link.transport.local_ack = 1;

	assert(mt6797_stp_task_prepare(&io, window, 130, &link, STP_FULL_TASK_BT,
				       reset, sizeof(reset), reset_event,
				       sizeof(reset_event), sizeof(reset_event), 100) == 0);
	assert(io.tx.length == sizeof(reset) + 6);
	assert(stp_full_decode(io.command, io.tx.length, &frame) == 1);
	assert(frame.task == STP_FULL_TASK_BT && frame.sequence == 2 &&
	       frame.acknowledgement == 1 && frame.length == sizeof(reset) &&
	       !memcmp(frame.payload, reset, sizeof(reset)));

	/* The WMT path keeps working through the same prepare. */
	memset(&io, 0, sizeof(io));
	assert(mt6797_wmt_full_prepare(&io, window, 130, &link, bt_on, sizeof(bt_on),
				       func_event, sizeof(func_event), 100) == 0);
	assert(stp_full_decode(io.command, io.tx.length, &frame) == 1 &&
	       frame.task == STP_FULL_TASK_WMT);

	/* Unsupported tasks are still refused. */
	memset(&io, 0, sizeof(io));
	assert(mt6797_stp_task_prepare(&io, window, 130, &link, STP_FULL_TASK_GPS,
				       reset, sizeof(reset), reset_event,
				       sizeof(reset_event), sizeof(reset_event), 100) == -EINVAL);
	puts("bt-h1 prepare: task-0 and WMT frames prepare; GPS refused");
	return 0;
}
