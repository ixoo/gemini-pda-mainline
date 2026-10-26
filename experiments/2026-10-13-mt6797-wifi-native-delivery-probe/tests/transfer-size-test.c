/* SPDX-License-Identifier: GPL-2.0-only */
/* The actual mt6797_hif_transfer_size() over every payload a receive batch
 * aggregate or a transmit can have (0310). Built by run-transfer-size-test.py,
 * once on the parent (-DPARENT: the 508-byte refusal of boots AA5 and AA6
 * reproduced) and once on the change.
 */
#include <assert.h>
#include <stdio.h>
#include "hif_transfer_size.h"

#define CAPACITY 37888U	/* the receive batch's per-queue buffer (0307) */

static void sweep(bool receive)
{
	struct mt6797_hif_transfer_size r;

	for (size_t n = 1; n <= 16 * 2356; n++) {
		int error = mt6797_hif_transfer_size(n, CAPACITY, receive, &r);

#ifdef PARENT
		if (receive && n >= 505 && n <= 508) {
			assert(error == -EMSGSIZE);
			continue;
		}
#endif
		assert(!error);
		assert(r.dma_bytes >= n && r.dma_bytes <= CAPACITY);
		assert(r.command_count >= 1 && r.command_count <= 511);
		assert(r.block_mode == (r.dma_bytes >= 512));
		if (r.block_mode)
			assert(r.dma_bytes == 512 * r.command_count && r.dma_bytes - n < 512);
		else
			assert(r.command_count == r.dma_bytes &&
			       r.dma_bytes % (receive ? 8 : 4) == 0 &&
			       r.dma_bytes - n < (receive ? 8 : 4));
	}
}

int main(void)
{
	sweep(true);
	sweep(false);
#ifdef PARENT
	printf("parent: DMA receive of 505-508 bytes refused (-EMSGSIZE), boots AA5 and AA6 reproduced\n");
#else
	printf("transfer size: PASS; every receive and transmit payload up to 37,696 bytes transfers, byte mode below 512, whole blocks from 512\n");
#endif
	return 0;
}
