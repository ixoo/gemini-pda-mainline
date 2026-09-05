/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "hif_init_bounds.h"

int main(void)
{
	static const struct { size_t bytes; unsigned int free, after; int error; } cases[] = {
		{16,104,103,0}, {20,1,0,0}, {1,104,103,0}, {127,2,1,0},
		{128,2,1,0}, {129,2,0,0}, {129,1,1,-ENOSPC},
		{13312,104,0,0}, {13313,104,104,-EMSGSIZE},
		{SIZE_MAX,104,104,-EMSGSIZE}, {0,104,104,-EMSGSIZE},
		{20,0,0,-ENOSPC}, {20,105,105,-EINVAL}, {20,0xffffffffU,0xffffffffU,-EINVAL},
	};
	size_t i;
	unsigned int pages = 104;
	struct mt6797_hif_command out;
	for (i = 0; i < sizeof(cases)/sizeof(cases[0]); i++) {
		pages = cases[i].free;
		assert(mt6797_init_debit(cases[i].bytes, &pages) == cases[i].error);
		assert(pages == cases[i].after);
	}
	assert(mt6797_init_debit(20, NULL) == -EINVAL);
	pages = 104;
	for (i = 0; i < 104; i++) assert(!mt6797_init_debit(20, &pages));
	assert(!pages && mt6797_init_debit(20, &pages) == -ENOSPC);
	/* No API can refund after uncertain submission; debit remains consumed. */
	for (i = 0; i <= 65535; i++) {
		out = (struct mt6797_hif_command){0xffffffffU, SIZE_MAX};
		assert(mt6797_init_result_span((unsigned int)i, 32, &out) ==
			(i == 28 ? 0 : i == 0 ? -EAGAIN : -EMSGSIZE));
		assert(out.word == (i == 28 ? 0x1000a020U : 0));
		assert(out.transfer_bytes == (i == 28 ? 32U : 0));
	}
	for (i = 0; i < 32; i++) {
		assert(mt6797_init_result_span(28, i, &out) == -EMSGSIZE);
		assert(!out.word && !out.transfer_bytes);
	}
	assert(mt6797_init_result_span(28, 32, NULL) == -EINVAL);
	assert(mt6797_init_result_span(0x1001c, 32, &out) == -EMSGSIZE);
	puts("init_debit_boundaries_exhaustion_and_all_u16_response_lengths=pass");
	return 0;
}
