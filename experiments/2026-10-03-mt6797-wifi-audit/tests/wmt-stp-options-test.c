// SPDX-License-Identifier: GPL-2.0-only
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "wmt-stp-options.h"
#include "wmt-full-stp-state.h"

static const unsigned char reply[12] = {
	0x80, 0x40, 0x06, 0x00, 0x02, 0x04, 0x02, 0x00, 0x00, 0x03, 0x00, 0x00
};

int main(void)
{
	struct wmt_stp_set_reply parser;
	struct wmt_full_state link;
	unsigned char frame[32], ack[4], mutated[12];
	unsigned int split, i, value;
	int bytes;

	/* Every chunk boundary and truncated prefix; completion requires byte 12. */
	for (split = 0; split <= sizeof(reply); split++) {
		memset(&parser, 0, sizeof(parser));
		for (i = 0; i < split; i++)
			assert(wmt_stp_set_reply_byte(&parser, reply[i]) == (i == 11));
		assert(parser.received == split);
		for (; i < sizeof(reply); i++)
			assert(wmt_stp_set_reply_byte(&parser, reply[i]) == (i == 11));
		assert(wmt_stp_set_reply_byte(&parser, 0) == -1 && parser.failed);
		assert(wmt_stp_set_reply_byte(&parser, 0x80) == -1);
	}
	/* All source-permitted sync variants; all other byte mutations fail. */
	for (i = 0; i < sizeof(reply); i++) {
		for (value = 0; value < 256; value++) {
			unsigned int j;
			int result = 0;

			memcpy(mutated, reply, sizeof(reply));
			mutated[i] = value;
			memset(&parser, 0, sizeof(parser));
			for (j = 0; j < sizeof(reply) && result >= 0; j++)
				result = wmt_stp_set_reply_byte(&parser, mutated[j]);
			if (i == 0 ? value & 0x80 : value == reply[i]) {
				assert(result == 1);
			} else {
				assert(result == -1 && parser.failed);
				assert(wmt_stp_set_reply_byte(&parser, reply[j - 1]) == -1);
			}
		}
	}
	assert(wmt_stp_set_reply_byte(NULL, 0x80) == -1);
	/* The existing full owner must require peer credit and host ACK completion.
	 * These synthetic exchanges prove composition, never physical negotiation.
	 */
	wmt_full_state_init(&link);
	bytes = wmt_full_encode(frame, sizeof(frame), wmt_stp_full_query,
				sizeof(wmt_stp_full_query), link.tx_next, link.local_ack);
	assert(bytes == 11 && frame[0] == 0x87);
	assert(wmt_full_sent(&link, 0) == 0);
	bytes = wmt_full_encode(frame, sizeof(frame), wmt_stp_full_options,
				sizeof(wmt_stp_full_options), 0, 0);
	assert(bytes == 16);
	assert(wmt_full_receive(&link, frame, bytes, wmt_stp_full_options,
				sizeof(wmt_stp_full_options)) == 1);
	assert(wmt_full_finish(&link) == -1);
	assert(wmt_full_ack(ack, sizeof(ack), link.local_ack) == 4);
	assert(wmt_full_ack_sent(&link, 0) == 0 && wmt_full_finish(&link) == 0);
	assert(link.tx_next == 1 && link.rx_next == 1);
	printf("set-options split/mutation and full-query composition tests passed\n");
	return 0;
}
