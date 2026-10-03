/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MT6797_WMT_VERSION_IO_H
#define MT6797_WMT_VERSION_IO_H
#include <linux/completion.h>
#include <linux/errno.h>
#include <linux/interrupt.h>
#include <linux/io.h>
#include <linux/jiffies.h>
#include <linux/spinlock.h>
#include <linux/string.h>
#include "wmt-identity-read.h"
#include "wmt-version-reply.h"
#include "wmt-full-stp-tx.h"

#define WMT_VERSION_SERVICES 64U
#define WMT_VERSION_RX_BYTES 22U
#define WMT_VERSION_RX_QUOTA 8U

/* Checked pre-negotiation register read. Persistent CONSYS-owned storage,
 * retained clocks, idle DMA, normal bank and empty FIFOs are caller gates.
 * No retry, reset, resynchronization, flush or power cleanup. A timeout never
 * establishes identity; only the exact complete reply can return success.
 */
struct mt6797_wmt_version_io {
	void __iomem *btif;
	unsigned char command[26], received[WMT_VERSION_RX_BYTES];
	struct wmt_full_tx tx;
	unsigned int rx_count, tx_count, services, ordinal;
	unsigned long deadline;
	/* Serializes FIFO progress, terminal state and timeout retirement. */
	spinlock_t lock;
	struct completion done;
	int irq, prepared, attempted, armed, terminal, result;
};

static int mt6797_wmt_version_prepare(struct mt6797_wmt_version_io *io,
				      void __iomem *btif, int irq, unsigned int ordinal,
				      unsigned long deadline)
{
	unsigned long now = jiffies;

	if (!io || !btif || irq <= 0 || ordinal >= 3 || time_after_eq(now, deadline) ||
	    deadline - now > msecs_to_jiffies(500))
		return -EINVAL;
	if (io->prepared)
		return -EBUSY;
	memset(io, 0, sizeof(*io));
	io->prepared = 1;
	io->btif = btif;
	io->irq = irq;
	io->ordinal = ordinal;
	io->deadline = deadline;
	init_completion(&io->done);
	spin_lock_init(&io->lock);
	wmt_identity_read(ordinal, io->command, sizeof(io->command));
	/* Reuse bounded byte accounting, not full-STP frame validation. */
	io->tx.frame = io->command;
	io->tx.length = sizeof(io->command);
	return 0;
}

/* Lock held. Resources/storage remain retained after IRQ retirement. */
static void mt6797_wmt_version_retire(struct mt6797_wmt_version_io *io, int result)
{
	if (io->terminal)
		return;
	writel(0, io->btif + 4);
	io->result = result;
	io->terminal = 1;
	if (io->armed) {
		disable_irq_nosync(io->irq);
		io->armed = 0;
	}
	complete(&io->done);
}

static void mt6797_wmt_version_service(struct mt6797_wmt_version_io *io, int initial)
{
	const unsigned char *bytes;
	unsigned int iir, quota = 0, actual = 0;
	int offered;

	if (io->terminal)
		return;
	if (time_after_eq(jiffies, io->deadline) ||
	    io->services == WMT_VERSION_SERVICES) {
		mt6797_wmt_version_retire(io, -ETIMEDOUT);
		return;
	}
	if (initial && (io->services ||
			(readl(io->btif + 0x14) & 0x61) != 0x60)) {
		mt6797_wmt_version_retire(io, -EBUSY);
		return;
	}
	io->services++;
	iir = readl(io->btif + 8);
	if ((initial && (iir & 0x44)) || (!initial && !(iir & 0x46)) ||
	    ((iir & 0x44) && !wmt_full_tx_done(&io->tx))) {
		mt6797_wmt_version_retire(io, -EPROTO);
		return;
	}
	while ((iir & 0x44) && quota < WMT_VERSION_RX_QUOTA) {
		if (io->rx_count == sizeof(io->received)) {
			mt6797_wmt_version_retire(io, -EPROTO);
			return;
		}
		if (time_after_eq(jiffies, io->deadline)) {
			mt6797_wmt_version_retire(io, -ETIMEDOUT);
			return;
		}
		io->received[io->rx_count++] = readb(io->btif);
		quota++;
		if (time_after_eq(jiffies, io->deadline)) {
			mt6797_wmt_version_retire(io, -ETIMEDOUT);
			return;
		}
		iir = readl(io->btif + 8);
	}
	if (time_after_eq(jiffies, io->deadline)) {
		mt6797_wmt_version_retire(io, -ETIMEDOUT);
		return;
	}
	/* The last IIR observation must show no queued trailing receive data. */
	if (io->rx_count == sizeof(io->received)) {
		if ((iir & 0x44) ||
		    !wmt_version_reply(io->ordinal, io->received, io->rx_count))
			mt6797_wmt_version_retire(io, -EPROTO);
		else
			mt6797_wmt_version_retire(io, 0);
		return;
	}
	if (!wmt_full_tx_done(&io->tx)) {
		offered = wmt_full_tx_batch(&io->tx, readl(io->btif + 0x14),
					    time_after_eq(jiffies, io->deadline), &bytes);
		if (offered < 0) {
			mt6797_wmt_version_retire(io, -ETIMEDOUT);
			return;
		}
		while (actual < (unsigned int)offered &&
		       !time_after_eq(jiffies, io->deadline)) {
			writeb(bytes[actual++], io->btif);
			io->tx_count++;
		}
		if (offered && wmt_full_tx_commit(&io->tx, actual,
						  time_after_eq(jiffies, io->deadline))) {
			mt6797_wmt_version_retire(io, -ETIMEDOUT);
			return;
		}
		if (wmt_full_tx_done(&io->tx))
			writel(1, io->btif + 4);
	}
}

static irqreturn_t mt6797_wmt_version_irq(int irq, void *data)
{
	struct mt6797_wmt_version_io *io = data;
	unsigned long flags;

	if (irq != io->irq)
		return IRQ_NONE;
	spin_lock_irqsave(&io->lock, flags);
	mt6797_wmt_version_service(io, 0);
	spin_unlock_irqrestore(&io->lock, flags);
	return IRQ_HANDLED;
}

/* Process context, one attempt even if IRQ registration fails. Only a zero
 * result admits the next selected read; every failure retains resources.
 */
static int mt6797_wmt_version_exchange(struct mt6797_wmt_version_io *io)
{
	unsigned long flags, now, remaining;
	int ret;

	if (!io || !io->prepared || io->attempted)
		return -EINVAL;
	io->attempted = 1;
	ret = request_irq(io->irq, mt6797_wmt_version_irq, IRQF_NO_AUTOEN,
			  "mt6797-wmt-version", io);
	if (ret) {
		io->result = ret;
		io->terminal = 1;
		complete(&io->done);
		return ret;
	}
	spin_lock_irqsave(&io->lock, flags);
	writel(3, io->btif + 4);
	mt6797_wmt_version_service(io, 1);
	if (!io->terminal)
		io->armed = 1;
	spin_unlock_irqrestore(&io->lock, flags);
	if (io->armed) {
		enable_irq(io->irq);
		now = jiffies;
		remaining = time_after_eq(now, io->deadline) ? 0 : io->deadline - now;
		wait_for_completion_timeout(&io->done, remaining);
		spin_lock_irqsave(&io->lock, flags);
		if (!io->terminal)
			mt6797_wmt_version_retire(io, -ETIMEDOUT);
		spin_unlock_irqrestore(&io->lock, flags);
	}
	synchronize_irq(io->irq);
	ret = io->result;
	free_irq(io->irq, io);
	return ret;
}
#endif
