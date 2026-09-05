// SPDX-License-Identifier: GPL-2.0-only
/* Independent interval oracle for the selected packet-DMA sizing contract. */
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include "hif_transfer_size.h"

static unsigned long checks;
static int check(size_t payload, size_t capacity, bool receive)
{
	struct mt6797_hif_transfer_size out = {13, 17, true};
	bool admitted = payload > 0 && payload <= 261632 &&
		!(receive && payload >= 505 && payload <= 508);
	bool block = payload >= 509;
	size_t expected = 0;
	unsigned int count = 0;
	if (admitted) {
		size_t unit = block ? 512 : receive ? 8 : 4;
		expected = payload + (unit - payload % unit) % unit;
		count = (unsigned int)(block ? expected / 512 : expected);
		admitted = expected <= capacity;
	}
	int ret = mt6797_hif_transfer_size(payload, capacity, receive, &out);
	++checks;
	if (!admitted)
		return ret == -EMSGSIZE && !out.dma_bytes &&
			!out.command_count && !out.block_mode;
	return ret == 0 && out.dma_bytes == expected &&
		out.command_count == count && out.block_mode == block &&
		out.dma_bytes >= payload && out.dma_bytes <= capacity &&
		out.dma_bytes <= 0xfffff && count > 0 && count <= 511;
}

int main(void)
{
	for (size_t payload = 0; payload <= 262144; ++payload) {
		for (int rx = 0; rx < 2; ++rx) {
			size_t unit = payload >= 509 ? 512 : rx ? 8 : 4;
			size_t padded = payload + (unit - payload % unit) % unit;
			size_t capacities[] = {0, payload ? payload - 1 : 0,
				payload, padded ? padded - 1 : 0, padded, padded + 1, SIZE_MAX};
			for (unsigned int i = 0; i < sizeof(capacities) / sizeof(capacities[0]); ++i)
				if (!check(payload, capacities[i], rx)) {
					printf("failure payload=%zu capacity=%zu rx=%d\n", payload, capacities[i], rx);
					return 1;
				}
		}
	}
	for (size_t delta = 0; delta <= 1024; ++delta)
		for (int rx = 0; rx < 2; ++rx)
			if (!check(SIZE_MAX - delta, SIZE_MAX, rx)) return 1;
	if (mt6797_hif_transfer_size(1, SIZE_MAX, false, NULL) != -EINVAL) return 1;
	printf("checks=%lu size_t_bits=%zu null_output_refused=1 result=pass\n", checks, sizeof(size_t) * CHAR_BIT);
	return 0;
}
