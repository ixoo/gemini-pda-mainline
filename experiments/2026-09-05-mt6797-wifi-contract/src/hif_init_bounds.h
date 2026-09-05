/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef GEMINI_HIF_INIT_BOUNDS_H
#define GEMINI_HIF_INIT_BOUNDS_H
#include "hif_command.h"

/* Selected boot INIT seed only: 8 * ceil((28 + 1532) / 128) = 104.
 * Caller establishes the fresh boot phase; this function never seeds/refunds.
 * Frame length already includes INIT header, excludes bus padding.
 */
static inline int
mt6797_init_debit(size_t frame_bytes, unsigned int *free_pages)
{
	unsigned int cost;
	if (!free_pages || *free_pages > 104U)
		return -EINVAL;
	if (!frame_bytes || frame_bytes > 104U * 128U)
		return -EMSGSIZE;
	cost = (unsigned int)((frame_bytes + 127U) / 128U);
	if (cost > *free_pages)
		return -ENOSPC;
	*free_pages -= cost;
	return 0;
}

/* Selected MT6797 CMD_RESULT is 28 logical bytes. Extra-read policy is +4,
 * with RX aggregation/coalescing enabled. Read 32 into staging, decode 28.
 * A pending length of zero is distinct from an unexpected nonzero event.
 */
static inline int
mt6797_init_result_span(unsigned int reported_length, size_t staging_capacity,
			struct mt6797_hif_command *result)
{
	if (!result)
		return -EINVAL;
	*result = (struct mt6797_hif_command) { 0 };
	if (!reported_length)
		return -EAGAIN;
	if (reported_length != 28U)
		return -EMSGSIZE;
	return mt6797_hif_encode_command(0x50U, MT6797_HIF_READ,
		MT6797_HIF_PIO_ONLY, 32U, staging_capacity, result);
}
#endif
