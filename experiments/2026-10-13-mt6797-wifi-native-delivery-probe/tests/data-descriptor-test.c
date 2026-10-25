// SPDX-License-Identifier: GPL-2.0-only
/* Host fixture for 0271 and 0273's header changes: the data descriptor's
 * fixed rate code (the default, and a profile's value through the option)
 * beside the PID and report bytes it always carries, and the receive-vector
 * word helper (group 3 present after groups 4, 1 and 2; absent; truncated).
 */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "test-compat.h"
#include "join-tx.h"
#include "data-rx.h"

static void put16(unsigned char *p, unsigned int v) { p[0] = v; p[1] = v >> 8; }

int main(void)
{
	unsigned char frame[64] = {0}, d[MT6797_JOIN_TX_DESC_BYTES];
	unsigned int pages;
	unsigned char pkt[128];
	unsigned int word;

	/* a plausible Ethernet frame: unicast destination, a non-EAPOL type */
	frame[0] = 0x02; frame[12] = 0x08; frame[13] = 0x00;
	/* PID and "TX status to MCU" together, the fixed-rate bit, and the rate code
	 * the build chose (0x4b unless the option says otherwise)
	 */
	assert(mt6797_join_tx_data_descriptor(frame, sizeof(frame), 1, 5, 500, 3, d, &pages));
	assert(d[20] == 5 && d[21] == 2 && d[11] == 0x80 && pages);
	assert(d[26] == ((MT6797_DATA_FIXED_RATE_CODE << 2) & 255) && d[27] == (MT6797_DATA_FIXED_RATE_CODE << 2) >> 8);
#ifdef CONFIG_MT6797_DATA_FIXED_RATE_CODE
	assert(MT6797_DATA_FIXED_RATE_CODE == CONFIG_MT6797_DATA_FIXED_RATE_CODE);
#else
	assert(MT6797_DATA_FIXED_RATE_CODE == 0x4bU && d[26] == 0x2c && d[27] == 1);
#endif

	/* receive vector: groups 4, 1, 2, 3 present -> word at 16+16+16+8 */
	memset(pkt, 0, sizeof(pkt));
	put16(pkt + 2, 15U << 9);
	put16(pkt + 56, 0x104b); put16(pkt + 58, 0x0000);	/* mode 1, rate 0x4b */
	assert(mt6797_rx_vector_word(pkt, sizeof(pkt), &word) && word == 0x104b);
	/* only group 3 -> word at 16 */
	put16(pkt + 2, 4U << 9); put16(pkt + 16, 0x2007);
	assert(mt6797_rx_vector_word(pkt, sizeof(pkt), &word) && word == 0x2007);
	/* group 3 absent -> false; truncated -> false */
	put16(pkt + 2, 11U << 9);
	assert(!mt6797_rx_vector_word(pkt, sizeof(pkt), &word));
	put16(pkt + 2, 15U << 9);
	assert(!mt6797_rx_vector_word(pkt, 58, &word));
	printf("data-descriptor-test: PASS (rate code 0x%02x; vector word)\n", MT6797_DATA_FIXED_RATE_CODE);
	return 0;
}
