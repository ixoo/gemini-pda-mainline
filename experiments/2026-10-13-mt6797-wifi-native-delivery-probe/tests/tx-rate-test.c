/* SPDX-License-Identifier: GPL-2.0-only */
/* mac80211's rate for an ordinary data frame as the descriptor carries it:
 * the actual tx-rate.h. Every HT MCS of one stream at both widths and both
 * guard intervals, every legacy code of the driver's bitrate table checked
 * against the vendor's transmit mode and PHY rate values, the refusals, and
 * the four descriptor bytes the rate writes. Built by run-testcfg-test.py.
 */
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include "tx-rate.h"

int main(void)
{
	static const unsigned short codes[] = MT6797_LEGACY_RATE_CODES;
	/* TX_MODE_CCK 0x00 | PHY_RATE_1M/2M/5_5M/11M, TX_MODE_OFDM 0x40 |
	 * PHY_RATE_6M 0xb, 9M 0xf, 12M 0xa, 18M 0xe, 24M 0x9, 36M 0xd, 48M 0x8,
	 * 54M 0xc, in the bitrate table's order 10..540 (100 kbit/s).
	 */
	static const unsigned short vendor[] = {
		0x0, 0x1, 0x2, 0x3, 0x40 | 0xb, 0x40 | 0xf, 0x40 | 0xa, 0x40 | 0xe,
		0x40 | 0x9, 0x40 | 0xd, 0x40 | 0x8, 0x40 | 0xc,
	};
	struct mt6797_tx_rate r;
	unsigned char d[28];
	int mcs, w, g;
	unsigned int i;

	assert(sizeof(codes) == sizeof(vendor));
	for (i = 0; i < sizeof(codes) / sizeof(codes[0]); i++) {
		assert(codes[i] == vendor[i]);
		assert(mt6797_tx_rate_map(i, false, false, false, false, codes[i], &r));
		assert(r.code == vendor[i] && !r.bw40 && !r.sgi);
	}
	for (mcs = 0; mcs < 8; mcs++)
		for (w = 0; w < 2; w++)
			for (g = 0; g < 2; g++) {
				assert(mt6797_tx_rate_map(mcs, true, false, w, g, -1, &r));
				assert(r.code == (0x80 | mcs) && r.bw40 == w && r.sgi == g);
			}
	/* No rate, a second stream, VHT, a legacy index outside the band, a
	 * legacy rate at 40 MHz or short GI: the frame takes the fixed rate.
	 */
	assert(!mt6797_tx_rate_map(-1, true, false, false, false, -1, &r));
	assert(!mt6797_tx_rate_map(8, true, false, false, false, -1, &r));
	assert(!mt6797_tx_rate_map(15, true, false, true, false, -1, &r));
	assert(!mt6797_tx_rate_map(0, false, true, false, false, -1, &r));
	assert(!mt6797_tx_rate_map(12, false, false, false, false, -1, &r));
	assert(!mt6797_tx_rate_map(4, false, false, true, false, 0x4b, &r));
	assert(!mt6797_tx_rate_map(4, false, false, false, true, 0x4b, &r));
	/* Bytes 11, 25, 26 and 27 only. */
	memset(d, 0xee, sizeof(d));
	r = (struct mt6797_tx_rate){ .code = 0x85, .bw40 = true, .sgi = true };
	mt6797_tx_rate_descriptor(&r, d);
	for (i = 0; i < sizeof(d); i++)
		assert(i == 11 ? d[i] == 0x80 : i == 25 ? d[i] == 5 :
		       i == 26 ? d[i] == ((0x85 << 2) & 255) :
		       i == 27 ? d[i] == (((0x85 << 2) >> 8) | 0x80) : d[i] == 0xee);
	r = (struct mt6797_tx_rate){ .code = 0x4c };
	mt6797_tx_rate_descriptor(&r, d);
	assert(d[11] == 0x80 && d[25] == 0 && d[26] == ((0x4c << 2) & 255) &&
	       d[27] == ((0x4c << 2) >> 8));
	printf("tx-rate-test: PASS\n");
	return 0;
}
