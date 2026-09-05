/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

#include "hif_transfer_size.h"

struct test_case {
	size_t payload, capacity, bytes;
	unsigned int count;
	bool receive, blocks;
	int error;
};

int main(void)
{
	/* Explicit boundary oracles, including the source's byte/block split. */
	const struct test_case cases[] = {
		{ 0, 512, 0, 0, false, false, -EMSGSIZE },
		{ 1, 4, 4, 4, false, false, 0 },
		{ 1, 8, 8, 8, true, false, 0 },
		{ 4, 4, 4, 4, false, false, 0 },
		{ 4, 4, 0, 0, true, false, -EMSGSIZE },
		{ 5, 8, 8, 8, false, false, 0 },
		{ 8, 8, 8, 8, true, false, 0 },
		{ 9, 12, 12, 12, false, false, 0 },
		{ 9, 16, 16, 16, true, false, 0 },
		{ 504, 504, 504, 504, true, false, 0 },
		{ 505, 512, 0, 0, true, false, -EMSGSIZE },
		{ 506, 512, 0, 0, true, false, -EMSGSIZE },
		{ 507, 512, 0, 0, true, false, -EMSGSIZE },
		{ 508, 512, 0, 0, true, false, -EMSGSIZE },
		{ 505, 508, 508, 508, false, false, 0 },
		{ 508, 508, 508, 508, false, false, 0 },
		{ 509, 512, 512, 1, true, true, 0 },
		{ 509, 512, 512, 1, false, true, 0 },
		{ 512, 512, 512, 1, true, true, 0 },
		{ 513, 1024, 1024, 2, false, true, 0 },
		{ 513, 513, 0, 0, false, false, -EMSGSIZE },
		{ 1024, 1024, 1024, 2, true, true, 0 },
		{ 261631, 261632, 261632, 511, true, true, 0 },
		{ 261632, 261632, 261632, 511, false, true, 0 },
		{ 261632, 261631, 0, 0, false, false, -EMSGSIZE },
		{ 261633, SIZE_MAX, 0, 0, false, false, -EMSGSIZE },
		{ 262144, SIZE_MAX, 0, 0, true, false, -EMSGSIZE },
		{ 0xfffff, SIZE_MAX, 0, 0, false, false, -EMSGSIZE },
		{ SIZE_MAX - 3, SIZE_MAX, 0, 0, true, false, -EMSGSIZE },
		{ SIZE_MAX, SIZE_MAX, 0, 0, false, false, -EMSGSIZE },
	};
	struct mt6797_hif_transfer_size out;
	size_t i;

	assert(mt6797_hif_transfer_size(1, 8, true, NULL) == -EINVAL);
	for (i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
		const struct test_case *c = &cases[i];

		out = (struct mt6797_hif_transfer_size) { 7, 7, true };
		assert(mt6797_hif_transfer_size(c->payload, c->capacity,
					      c->receive, &out) == c->error);
		assert(out.dma_bytes == c->bytes);
		assert(out.command_count == c->count);
		assert(out.block_mode == c->blocks);
	}
	printf("transfer_size_cases=%zu null_output_refused=1 result=pass\n",
	       sizeof(cases) / sizeof(cases[0]));
	return 0;
}
