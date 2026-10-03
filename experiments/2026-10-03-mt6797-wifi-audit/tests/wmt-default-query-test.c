// SPDX-License-Identifier: GPL-2.0-only
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "wmt-default-query.h"

int main(void)
{
	const unsigned char expected_query[] = {
		128, 64, 5, 0, 1, 4, 1, 0, 4, 0, 0
	};
	const unsigned char event[] = {
		128, 64, 10, 0, 2, 4, 6, 0, 0, 4, 17, 0, 0, 0, 0, 0
	};

	assert(sizeof(wmt_default_query) == sizeof(expected_query));
	assert(!memcmp(wmt_default_query, expected_query, sizeof(expected_query)));
	/* Every possible two-chunk split, including every incomplete prefix. */
	for (unsigned int split = 0; split <= sizeof(event); split++) {
		struct wmt_default_reply reply = {0};

		for (unsigned int i = 0; i < split; i++)
			assert(wmt_default_reply_byte(&reply, event[i]) == (i == 15));
		assert(reply.received == split && !reply.failed);
		for (unsigned int i = split; i < sizeof(event); i++)
			assert(wmt_default_reply_byte(&reply, event[i]) == (i == 15));
		assert(wmt_default_reply_byte(&reply, 0) == -1);
		assert(reply.received == 16);
	}
	/* All sync/sequence bytes: bit 7 required, lower bits not constrained. */
	for (unsigned int value = 0; value < 256; value++) {
		struct wmt_default_reply reply = {0};

		assert(wmt_default_reply_byte(&reply, value) == (value < 128 ? -1 : 0));
	}
	/* Reject every wrong task, length, opcode, status, option and trailer. */
	for (unsigned int index = 1; index < sizeof(event); index++) {
		for (unsigned int value = 0; value < 256; value++) {
			struct wmt_default_reply reply = {0};

			if (value == event[index])
				continue;
			for (unsigned int i = 0; i < index; i++)
				assert(!wmt_default_reply_byte(&reply, event[i]));
			assert(wmt_default_reply_byte(&reply, value) == -1);
			assert(reply.failed && reply.received == index);
			assert(wmt_default_reply_byte(&reply, event[index]) == -1);
		}
	}
	assert(wmt_default_reply_byte(NULL, 128) == -1);
	puts("fixed WMT default query: PASS (splits, truncation, mutations, retirement)");
	return 0;
}
