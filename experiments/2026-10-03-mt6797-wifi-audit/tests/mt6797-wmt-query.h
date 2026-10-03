/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef MT6797_WMT_QUERY_H
#define MT6797_WMT_QUERY_H

#include <linux/clk.h>
#include <linux/completion.h>
#include <linux/errno.h>
#include <linux/interrupt.h>
#include <linux/io.h>
#include <linux/jiffies.h>
#include <linux/spinlock.h>

#include "wmt-default-query.h"

#define WMT_BTIF_IER		0x04
#define WMT_BTIF_IIR		0x08
#define WMT_BTIF_FAKELCR		0x0c
#define WMT_BTIF_LSR		0x14
#define WMT_BTIF_DMA_EN		0x4c
#define WMT_BTIF_TRI_LVL		0x60
#define WMT_BTIF_HANDSHAKE	0x6c
#define WMT_BTIF_RX_CAUSE	0x44
#define WMT_BTIF_IRQ_BUDGET	32
#define WMT_BTIF_RX_BUDGET	17

/* Zero-initialized CONSYS storage; never stack allocated or reused. */
struct mt6797_wmt_query {
	void __iomem *btif;
	void __iomem *dma_tx;
	void __iomem *dma_rx;
	struct clk *btif_clk;
	struct clk *dma_clk;
	struct completion done;
	/* Serializes TX commit, RX terminal state and timeout retirement. */
	spinlock_t lock;
	struct wmt_default_reply reply;
	unsigned int irq_count;
	unsigned int rx_count;
	unsigned long deadline;
	int irq;
	int result;
	bool attempted;
	bool tx_written;
	bool terminal;
	bool clocks_held;
};

/* No reset, stop, flush, descriptor, interrupt-ack or DMA-enable writes. */
static bool mt6797_wmt_dma_idle(void __iomem *base)
{
	return !readl(base + 0x08) && !readl(base + 0x10) &&
	       !readl(base + 0x14) && !readl(base + 0x38) &&
	       !readl(base + 0x3c);
}

/* Called with the lock held and an installed, enabled exclusive IRQ. */
static void mt6797_wmt_query_finish(struct mt6797_wmt_query *query, int result)
{
	writel(0, query->btif + WMT_BTIF_IER);
	query->result = result;
	query->terminal = true;
	disable_irq_nosync(query->irq);
	complete(&query->done);
}

static irqreturn_t mt6797_wmt_query_irq(int irq, void *data)
{
	struct mt6797_wmt_query *query = data;
	unsigned long flags;
	unsigned int iir;
	int parsed;

	if (irq != query->irq)
		return IRQ_NONE;
	spin_lock_irqsave(&query->lock, flags);
	if (query->terminal)
		goto out;
	if (!query->tx_written) {
		mt6797_wmt_query_finish(query, -EBUSY);
		goto out;
	}
	if (++query->irq_count >= WMT_BTIF_IRQ_BUDGET ||
	    time_after_eq(jiffies, query->deadline)) {
		mt6797_wmt_query_finish(query, -ETIMEDOUT);
		goto out;
	}
	iir = readl(query->btif + WMT_BTIF_IIR);
	if (!(iir & WMT_BTIF_RX_CAUSE)) {
		mt6797_wmt_query_finish(query, -EPROTO);
		goto out;
	}
	while (iir & WMT_BTIF_RX_CAUSE) {
		if (query->rx_count == WMT_BTIF_RX_BUDGET) {
			mt6797_wmt_query_finish(query, -EOVERFLOW);
			goto out;
		}
		query->rx_count++;
		parsed = wmt_default_reply_byte(&query->reply, readb(query->btif));
		if (parsed < 0) {
			mt6797_wmt_query_finish(query, -EPROTO);
			goto out;
		}
		iir = readl(query->btif + WMT_BTIF_IIR);
		if (parsed) {
			/* A queued extra byte is a failure; never consume or resync it. */
			parsed = iir & WMT_BTIF_RX_CAUSE ? -EOVERFLOW : 0;
			mt6797_wmt_query_finish(query, parsed);
			goto out;
		}
	}
out:
	spin_unlock_irqrestore(&query->lock, flags);
	return IRQ_HANDLED;
}

/*
 * Reproduce the selected source's four aliased IIR/FIFOCTRL operations.
 * These reads are interrupt identifiers, never control-value readbacks.
 * Register-table bit assignments conflict; this needs explicit admission.
 */
static void mt6797_wmt_fifo_clear(void __iomem *base)
{
	writel(readl(base + WMT_BTIF_IIR) | BIT(1), base + WMT_BTIF_IIR);
	writel(readl(base + WMT_BTIF_IIR) & ~BIT(1), base + WMT_BTIF_IIR);
	writel(readl(base + WMT_BTIF_IIR) | BIT(2), base + WMT_BTIF_IIR);
	writel(readl(base + WMT_BTIF_IIR) & ~BIT(2), base + WMT_BTIF_IIR);
}

/*
 * Caller holds the shared CONSYS lock, after fresh power/reset release and
 * before HIF or a sleep command. No transport retry or shutdown is attempted.
 * After any clock enable, retain acquired clocks for reviewed system recovery.
 */
static int mt6797_wmt_query_once(struct mt6797_wmt_query *query)
{
	unsigned long flags;
	unsigned int i, dma;
	unsigned long remaining;
	int ret;

	if (query->attempted)
		return -EALREADY;
	query->attempted = true;
	init_completion(&query->done);
	spin_lock_init(&query->lock);
	query->result = -ETIMEDOUT;

	ret = clk_prepare_enable(query->dma_clk);
	if (ret)
		return ret;
	query->clocks_held = true;
	if (!mt6797_wmt_dma_idle(query->dma_tx) ||
	    !mt6797_wmt_dma_idle(query->dma_rx))
		return -EBUSY;
	ret = clk_prepare_enable(query->btif_clk);
	if (ret)
		return ret;

	/* Normal bank first; reject nonempty FIFOs before any clear. */
	writel(0, query->btif + WMT_BTIF_FAKELCR);
	if ((readl(query->btif + WMT_BTIF_LSR) & 0x41) != 0x40)
		return -EBUSY;
	/* One admitted timeout acknowledgment if auto-reset was off. */
	dma = readl(query->btif + WMT_BTIF_DMA_EN);
	if (dma & (BIT(0) | BIT(1)))
		return -EBUSY;
	writel(0, query->btif + WMT_BTIF_IER);
	writel(readl(query->btif + WMT_BTIF_HANDSHAKE) | BIT(0),
	       query->btif + WMT_BTIF_HANDSHAKE);
	mt6797_wmt_fifo_clear(query->btif);
	writel(0x18, query->btif + WMT_BTIF_TRI_LVL);
	/* Preserve other fields; requests already proved off. */
	writel(dma | BIT(2), query->btif + WMT_BTIF_DMA_EN);
	if ((readl(query->btif + WMT_BTIF_LSR) & 0x61) != 0x60)
		return -EBUSY;

	ret = request_irq(query->irq, mt6797_wmt_query_irq, IRQF_NO_AUTOEN,
			  "mt6797-wmt-query", query);
	if (ret)
		return ret;
	query->deadline = jiffies + msecs_to_jiffies(500);
	/* RX only, as in the revision-matched PIO path. */
	writel(BIT(0), query->btif + WMT_BTIF_IER);
	if (readl(query->btif + WMT_BTIF_IIR) & WMT_BTIF_RX_CAUSE) {
		ret = -EBUSY;
		goto stop;
	}

	/* Arm RX first. The full 11-byte request fits the empty 16-byte TX FIFO. */
	enable_irq(query->irq);
	spin_lock_irqsave(&query->lock, flags);
	if (!query->terminal && time_after_eq(jiffies, query->deadline))
		mt6797_wmt_query_finish(query, -ETIMEDOUT);
	if (!query->terminal) {
		for (i = 0; i < sizeof(wmt_default_query); i++)
			writeb(wmt_default_query[i], query->btif);
		query->tx_written = true;
	}
	spin_unlock_irqrestore(&query->lock, flags);
	remaining = time_before(jiffies, query->deadline) ?
		    query->deadline - jiffies : 0;
	wait_for_completion_timeout(&query->done, remaining);
	/* Synchronize before reading result or releasing handler storage. */
	disable_irq(query->irq);
	spin_lock_irqsave(&query->lock, flags);
	ret = query->terminal ? query->result : -ETIMEDOUT;
	query->terminal = true;
	spin_unlock_irqrestore(&query->lock, flags);
stop:
	writel(0, query->btif + WMT_BTIF_IER);
	free_irq(query->irq, query);
	return ret;
}

#endif
