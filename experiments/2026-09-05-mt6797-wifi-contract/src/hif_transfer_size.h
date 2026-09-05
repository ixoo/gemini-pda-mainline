/* SPDX-License-Identifier: GPL-2.0-only */
/* Original arithmetic only; see HIF_DMA_CONTRACT.md for admission limits. */
#ifndef GEMINI_HIF_TRANSFER_SIZE_H
#define GEMINI_HIF_TRANSFER_SIZE_H

#ifdef __KERNEL__
#include <linux/errno.h>
#include <linux/types.h>
#else
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#endif

struct mt6797_hif_transfer_size {
	size_t dma_bytes;
	unsigned int command_count;
	bool block_mode;
};

/*
 * Selected 512-byte block contract. No address, mapping, port or MMIO action.
 * A zero command count is deliberately refused: its special meaning on this
 * private SDIO-like HIF has not been established. TX padding must be initialized
 * by the caller; RX storage must cover dma_bytes, not just payload_bytes.
 */
static inline int
mt6797_hif_transfer_size(size_t payload_bytes, size_t capacity, bool receive,
			 struct mt6797_hif_transfer_size *result)
{
	size_t bytes, count;
	bool blocks;

	if (!result)
		return -EINVAL;
	*result = (struct mt6797_hif_transfer_size) { 0 };
	/* This bound also makes every following round-up overflow-safe. */
	if (!payload_bytes || payload_bytes > 511U * 512U)
		return -EMSGSIZE;

	bytes = (payload_bytes + 3U) & ~(size_t)3U;
	blocks = bytes >= 512U;
	if (blocks) {
		count = (bytes + 511U) / 512U;
		bytes = count * 512U;
	} else {
		if (receive)
			bytes = (payload_bytes + 7U) & ~(size_t)7U;
		count = bytes;
	}
	if (!count || count > 511U || bytes > 0xfffffU || bytes > capacity)
		return -EMSGSIZE;

	result->dma_bytes = bytes;
	result->command_count = (unsigned int)count;
	result->block_mode = blocks;
	return 0;
}

#endif
