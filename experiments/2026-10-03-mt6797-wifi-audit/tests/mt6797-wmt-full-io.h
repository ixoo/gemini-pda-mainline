/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MT6797_WMT_FULL_IO_H
#define MT6797_WMT_FULL_IO_H
#include <linux/completion.h>
#include <linux/errno.h>
#include <linux/interrupt.h>
#include <linux/io.h>
#include <linux/jiffies.h>
#include <linux/spinlock.h>
#include <linux/string.h>
#include "wmt-full-stp-state.h"
#include "wmt-full-stp-stream.h"
#include "wmt-full-stp-tx.h"

#define WMT_FULL_IO_SERVICES 512U
#define WMT_FULL_IO_RX_QUOTA 8U
#define WMT_FULL_IO_FRAMES 8U
#define WMT_FULL_IO_RX_BYTES (WMT_FULL_MAX_FRAME + 32U)

/* CONSYS-owned persistent storage, never stack allocated. Caller establishes
 * full mode, clocks, DMA exclusion, normal bank and exclusive registered IRQ.
 * This draft supplies no such setup or admission and has no kernel caller.
 */
struct mt6797_wmt_full_io {
	void __iomem *btif;
	struct wmt_full_state *link;
	struct wmt_full_stream stream;
	struct wmt_full_tx tx;
	unsigned char command[WMT_FULL_MAX_FRAME], ack[4];
	unsigned char received[WMT_FULL_IO_RX_BYTES];
	const unsigned char *expected;
	unsigned int expected_length, rx_count, consumed, frames, services, tx_count;
	unsigned long deadline;
	spinlock_t lock;
	struct completion done;
	int irq, ack_phase, sent, terminal, result, prepared;
};

/* No effects; caller provides fresh/synchronized storage and an inactive link.
 * Expected event storage remains immutable throughout this command lifetime.
 */
static int mt6797_wmt_full_prepare(struct mt6797_wmt_full_io *io,
		void __iomem *btif, int irq, struct wmt_full_state *link,
		const unsigned char *command, unsigned int length,
		const unsigned char *expected, unsigned int expected_length,
		unsigned long deadline)
{
	int bytes;

	if (!io || !btif || irq <= 0 || !link || link->active || !command || !length ||
	    length > WMT_FULL_MAX_PAYLOAD || !expected || !expected_length ||
	    expected_length > WMT_FULL_MAX_PAYLOAD)
		return -EINVAL;
	if (io->prepared && (!io->terminal || io->result))
		return -EBUSY;
	memset(io, 0, sizeof(*io));
	io->prepared = 1;
	io->btif = btif;
	io->irq = irq;
	io->link = link;
	io->expected = expected;
	io->expected_length = expected_length;
	io->deadline = deadline;
	init_completion(&io->done);
	spin_lock_init(&io->lock);
	wmt_full_stream_init(&io->stream);
	bytes = wmt_full_encode(io->command, sizeof(io->command), command, length,
			       link->tx_next, link->local_ack);
	if (bytes < 0)
		return -EINVAL;
	return wmt_full_tx_init(&io->tx, io->command, bytes) ? -EINVAL : 0;
}

/* Caller holds the same lock used by IRQ progress. Resources remain retained;
 * caller synchronizes/frees the IRQ only after evidence and terminal state.
 */
static void mt6797_wmt_full_retire(struct mt6797_wmt_full_io *io, int result)
{
	if (io->terminal)
		return;
	writel(0, io->btif + 4);
	io->result = result;
	io->terminal = 1;
	disable_irq_nosync(io->irq);
	complete(&io->done);
}

static int mt6797_wmt_full_tx_progress(struct mt6797_wmt_full_io *io)
{
	const unsigned char *bytes;
	unsigned int actual = 0, lsr;
	int offered;

	if (wmt_full_tx_done(&io->tx))
		return 0;
	if (time_after_eq(jiffies, io->deadline))
		return -ETIMEDOUT;
	lsr = readl(io->btif + 0x14);
	offered = wmt_full_tx_batch(&io->tx, lsr,
				  time_after_eq(jiffies, io->deadline), &bytes);
	if (offered < 0)
		return -ETIMEDOUT;
	while (actual < (unsigned int)offered) {
		if (time_after_eq(jiffies, io->deadline))
			break;
		writeb(bytes[actual++], io->btif);
		io->tx_count++;
	}
	if (offered && wmt_full_tx_commit(&io->tx, actual,
					time_after_eq(jiffies, io->deadline)))
		return -ETIMEDOUT;
	return 0;
}

/* One bounded service, caller holds lock. Initial kick occurs with CPU IRQ
 * disabled after reviewed empty-RX/setup checks. Subsequent calls are IRQs.
 * Per-service RX quota gives TX an opportunity despite continuously pending RX.
 */
static void mt6797_wmt_full_service(struct mt6797_wmt_full_io *io, int initial)
{
	struct wmt_full_frame frame;
	unsigned int iir, quota = 0;
	int ret, parsed;

	if (io->terminal)
		return;
	if (time_after_eq(jiffies, io->deadline) ||
	    io->services == WMT_FULL_IO_SERVICES) {
		mt6797_wmt_full_retire(io, -ETIMEDOUT);
		return;
	}
	if (initial && io->services) {
		mt6797_wmt_full_retire(io, -EPROTO);
		return;
	}
	io->services++;
	iir = readl(io->btif + 8);
	if ((initial && (iir & 0x44)) || (!initial && !(iir & 0x46))) {
		mt6797_wmt_full_retire(io, -EPROTO);
		return;
	}
	while ((iir & 0x44) && quota < WMT_FULL_IO_RX_QUOTA) {
		if (io->rx_count == sizeof(io->received)) {
			mt6797_wmt_full_retire(io, -EOVERFLOW);
			return;
		}
		if (time_after_eq(jiffies, io->deadline)) {
			mt6797_wmt_full_retire(io, -ETIMEDOUT);
			return;
		}
		io->received[io->rx_count++] = readb(io->btif);
		quota++;
		iir = readl(io->btif + 8);
	}
	ret = mt6797_wmt_full_tx_progress(io);
	if (ret)
		goto fail;
	if (!io->sent && wmt_full_tx_done(&io->tx)) {
		if (wmt_full_sent(io->link, (io->command[0] >> 3) & 7)) {
			ret = -EPROTO;
			goto fail;
		}
		io->sent = 1;
		writel(1, io->btif + 4);
	}
	if (!io->sent)
		return;
	while (io->consumed < io->rx_count) {
		if (time_after_eq(jiffies, io->deadline)) {
			ret = -ETIMEDOUT;
			goto fail;
		}
		parsed = wmt_full_stream_byte(&io->stream,
				io->received[io->consumed++], &frame);
		if (parsed < 0 || (parsed && io->frames == WMT_FULL_IO_FRAMES)) {
			ret = -EPROTO;
			goto fail;
		}
		if (!parsed)
			continue;
		io->frames++;
		if (wmt_full_receive(io->link, io->stream.frame, io->stream.used,
				     io->expected, io->expected_length) < 0) {
			ret = -EPROTO;
			goto fail;
		}
		wmt_full_stream_init(&io->stream);
	}
	/* Once both reply and peer credit are known, further input is unexpected.
	 * Refuse it before adding host ACK writes to a failed lifetime.
	 */
	if (io->link->acknowledged && io->link->event_seen &&
	    (io->stream.used || (readl(io->btif + 8) & 0x44))) {
		ret = -EPROTO;
		goto fail;
	}
	if (io->link->ack_owed && !io->ack_phase) {
		if (wmt_full_ack(io->ack, sizeof(io->ack), io->link->local_ack) != 4 ||
		    wmt_full_tx_init(&io->tx, io->ack, sizeof(io->ack))) {
			ret = -EPROTO;
			goto fail;
		}
		io->ack_phase = 1;
		writel(3, io->btif + 4);
	}
	if (io->ack_phase && io->link->ack_owed) {
		ret = mt6797_wmt_full_tx_progress(io);
		if (ret)
			goto fail;
		if (wmt_full_tx_done(&io->tx)) {
			if (wmt_full_ack_sent(io->link, io->link->local_ack)) {
				ret = -EPROTO;
				goto fail;
			}
			writel(1, io->btif + 4);
		}
	}
	if (io->link->acknowledged && io->link->event_seen && !io->link->ack_owed) {
		/* Refuse queued or partial extra data before successful retirement. */
		if (io->stream.used || (readl(io->btif + 8) & 0x44)) {
			ret = -EPROTO;
			goto fail;
		}
		if (time_after_eq(jiffies, io->deadline)) {
			ret = -ETIMEDOUT;
			goto fail;
		}
		ret = wmt_full_finish(io->link) ? -EPROTO : 0;
		mt6797_wmt_full_retire(io, ret);
	}
	return;
fail:
	mt6797_wmt_full_retire(io, ret);
}

static irqreturn_t mt6797_wmt_full_irq(int irq, void *data)
{
	struct mt6797_wmt_full_io *io = data;
	unsigned long flags;

	if (irq != io->irq)
		return IRQ_NONE;
	spin_lock_irqsave(&io->lock, flags);
	mt6797_wmt_full_service(io, 0);
	spin_unlock_irqrestore(&io->lock, flags);
	return IRQ_HANDLED;
}
#endif
