/* SPDX-License-Identifier: GPL-2.0-only */
/* Original fixed-port command encoder; see HIF_COMMAND.md. */
#ifndef GEMINI_HIF_COMMAND_H
#define GEMINI_HIF_COMMAND_H

#include "hif_transfer_size.h"

enum mt6797_hif_direction {
	MT6797_HIF_READ = 0,
	MT6797_HIF_WRITE = 1,
};

/* Source use_dma policy, not a selection of the engine executing the command. */
enum mt6797_hif_rx_policy {
	MT6797_HIF_PIO_ONLY = 0,
	MT6797_HIF_DMA_ENABLED = 1,
};

struct mt6797_hif_command {
	unsigned int word;
	size_t transfer_bytes;
};

/*
 * Only INIT/data TX WTDR1 and response RX WRDR0/1 are admitted here.
 * Function 1 and fixed-port mode are constants, not unvalidated caller fields.
 * DMA_ENABLED preserves eight-byte RX alignment even for a PIO fallback.
 * The caller owns initialized TX padding, RX capacity and all runtime gates.
 */
static inline int mt6797_hif_encode_command(unsigned int port,
					    enum mt6797_hif_direction direction,
					    enum mt6797_hif_rx_policy policy,
					    size_t payload_bytes,
					    size_t capacity,
					    struct mt6797_hif_command *result)
{
	struct mt6797_hif_transfer_size size;
	int error;

	if (!result)
		return -EINVAL;
	*result = (struct mt6797_hif_command){0};
	if ((direction != MT6797_HIF_READ && direction != MT6797_HIF_WRITE) ||
	    (policy != MT6797_HIF_PIO_ONLY &&
	     policy != MT6797_HIF_DMA_ENABLED) ||
	    port > 0x1ffffU)
		return -EINVAL;
	if ((direction == MT6797_HIF_WRITE && port != 0x34U) ||
	    (direction == MT6797_HIF_READ && port != 0x50U && port != 0x54U))
		return -EINVAL;

	/* The helper's false branch supplies four-byte TX/PIO-only RX rounding. */
	error = mt6797_hif_transfer_size(payload_bytes, capacity,
					 direction == MT6797_HIF_READ &&
						 policy ==
							 MT6797_HIF_DMA_ENABLED,
					 &size);
	if (error)
		return error;
	if (!size.command_count || size.command_count > 0x1ffU)
		return -EMSGSIZE;
	result->word = size.command_count | (port << 9) |
		       (size.block_mode ? (1U << 27) : 0U) | (1U << 28) |
		       (direction == MT6797_HIF_WRITE ? (1U << 31) : 0U);
	result->transfer_bytes = size.dma_bytes;
	return 0;
}

#endif
