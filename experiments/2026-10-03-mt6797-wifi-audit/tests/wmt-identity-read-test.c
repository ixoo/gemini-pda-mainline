/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include "wmt-identity-read.h"

static unsigned int le32(const unsigned char *p)
{
	return (unsigned int)p[0] | (unsigned int)p[1] << 8 |
	       (unsigned int)p[2] << 16 | (unsigned int)p[3] << 24;
}

int main(void)
{
	const unsigned int addresses[3] = { 0x80000008, 0x80000000, 0x80000004 };
	unsigned char out[28], before[28];
	unsigned int i, capacity;

	for (i = 0; i < 3; i++) {
		memset(out, 0xa5, sizeof(out));
		assert(wmt_identity_read(i, out, 26) == 26);
		/* Decode independent protocol fields, including read-only operation. */
		assert(out[0] == 0x80 && out[1] == 0x40 && out[2] == 20 && !out[3]);
		assert(out[4] == 1 && out[5] == 8 && out[6] == 16 && !out[7]);
		assert(out[8] == 2 && out[9] == 1 && !out[10] && out[11] == 1);
		assert(le32(out + 12) == addresses[i]);
		assert(le32(out + 16) == 0); /* deterministic, unlike vendor HW/ROM */
		assert(le32(out + 20) == 0xffff);
		assert(!out[24] && !out[25]);
		assert(out[26] == 0xa5 && out[27] == 0xa5);
	}
	/* Reject every insufficient capacity without even partial request bytes. */
	memset(out, 0xa5, sizeof(out));
	memcpy(before, out, sizeof(out));
	for (capacity = 0; capacity < 26; capacity++) {
		assert(wmt_identity_read(0, out, capacity) == -1);
		assert(!memcmp(out, before, sizeof(out)));
	}
	assert(wmt_identity_read(3, out, sizeof(out)) == -1);
	assert(wmt_identity_read(UINT_MAX, out, sizeof(out)) == -1);
	assert(!memcmp(out, before, sizeof(out)));
	assert(wmt_identity_read(0, NULL, 26) == -1);
	puts("identity-read construction: 3 requests; 29 refusal cases; no I/O");
	return 0;
}
