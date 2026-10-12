/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "data-rx.h"

/* Strict native (untranslated, encrypted) decoder mt6797_data_rx_native (0181).
 * A synthetic native protected-CCMP data frame is accepted and the ORIGINAL MPDU
 * offset/length returned (IV/MIC preserved, verbatim); every non-native, legacy
 * or malformed shape is withheld. Offsets follow nicRxFillRFB (16 + the present
 * groups in 4/1/2/3 order + the BIT6 pad). Covers all optional group masks, both
 * header lengths, the MSDU0/AMSDU, MoreFragments/Order/fragment, CCMP-shape and
 * bad-FCS gates. No reference packet is replayed. */
static const unsigned char own[6] = {2, 0, 0, 0, 0, 1}, ap[6] = {2, 0, 0, 0, 0, 2};

/* Build a native frame with the given GROUP_VLD mask, BIT6 pad, and QoS flag;
 * returns the total byte count and the MPDU offset in *off. */
static size_t build_g(unsigned char p[512], unsigned int groups, int pad, int qos, size_t *off)
{
	size_t o = 16, hdr = qos ? 26 : 24, total;
	memset(p, 0, 512);
	if (groups & 8) o += 16;        /* group 4 */
	if (groups & 1) o += 16;        /* group 1 */
	if (groups & 2) o += 8;         /* group 2 */
	if (groups & 4) o += 24;        /* group 3 */
	if (pad) o += 2;
	total = o + hdr + 8 + 8;        /* MPDU: hdr + CCMP(8) + MIC(8) */
	p[0] = total & 0xff; p[1] = total >> 8;
	{ unsigned int t = (2u << 13) | ((groups & 15u) << 9); p[2] = t & 0xff; p[3] = t >> 8; }
	p[5] = 40;
	p[6] = (unsigned char)(hdr | (pad ? 0x40 : 0));   /* hdrlen, BIT6 pad, BIT7 clear (native) */
	p[o + 0] = 0x08;                                  /* ver0 type data */
	p[o + 0] |= qos ? 0x80 : 0;                       /* subtype 8 (QoS-data) */
	p[o + 1] = 0x42;                                  /* FromDS + Protected */
	memcpy(p + o + 4, own, 6);
	memcpy(p + o + 10, ap, 6);
	p[o + hdr + 3] = 0x20;                            /* CCMP Ext-IV, reserved clear */
	*off = o;
	return total;
}

static bool dec(unsigned char *p, size_t n, size_t *mo, size_t *ml)
{
	return mt6797_data_rx_native(p, n, 40, own, ap, mo, ml);
}

int main(void)
{
	unsigned char p[512];
	size_t n, o, mo = 0, ml = 0;

	/* Every optional group combination (group 4 present with HDR_TRAN=false is
	 * skipped by size, not treated as translated), both header lengths, both pads. */
	for (unsigned int g = 0; g < 16; g++)
		for (int pad = 0; pad <= 1; pad++)
			for (int qos = 0; qos <= 1; qos++) {
				n = build_g(p, g, pad, qos, &o);
				assert(dec(p, n, &mo, &ml));
				assert(mo == o && ml == n - o);   /* original MPDU, verbatim length */
			}

	/* Group-addressed (addr1 multicast) accepted. */
	n = build_g(p, 0x5, 0, 0, &o); p[o + 4] |= 1;
	assert(dec(p, n, &mo, &ml));

	/* Withheld shapes (base = group1+group3, no pad, non-QoS). */
	n = build_g(p, 0x5, 0, 0, &o); p[6] |= 0x80;            /* HDR_TRAN set (translated) */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 0, &o); p[7] |= 1;               /* AMSDU sub-frame (not MSDU0) */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 0, &o); p[o + 1] &= ~0x40;       /* not Protected */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 0, &o); p[o + 1] |= 0x04;        /* More Fragments */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 0, &o); p[o + 1] |= 0x80;        /* Order / +HTC */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 0, &o); p[o + 22] |= 1;          /* fragment number != 0 */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 0, &o); p[o + 1] = (p[o + 1] & ~0x02) | 0x01; /* ToDS not FromDS */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 0, &o); p[o + 0] &= ~0x0c;       /* management (not data) */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 0, &o); p[o + 10] ^= 0xff;       /* addr2 (TA) != AP */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 0, &o); p[o + 5] = 9;            /* unicast addr1 != own */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 0, &o); p[o + 24 + 2] = 1;       /* CCMP reserved byte2 != 0 */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 0, &o); p[o + 24 + 3] |= 0x01;   /* CCMP byte3 reserved low bit */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 0, &o); p[o + 24 + 3] &= ~0x20;  /* CCMP Ext-IV clear */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 0, &o); p[10] |= 0x02;           /* bad-FCS report (u2StatusFlag bit1) */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 0, &o); p[6] = 26;               /* non-QoS FC but hdrlen 26 => mismatch */
	assert(!dec(p, n, &mo, &ml));
	n = build_g(p, 0x5, 0, 1, &o); p[6] = (p[6] & 0xc0) | 24; /* QoS FC but hdrlen 24 => mismatch */
	assert(!dec(p, n, &mo, &ml));
	/* Too short for header + CCMP + MIC (shrink the declared count by 1). */
	n = build_g(p, 0x5, 0, 0, &o); n -= 1; p[0] = n & 0xff; p[1] = n >> 8;
	assert(!dec(p, n, &mo, &ml));
	/* Wrong channel. */
	n = build_g(p, 0x5, 0, 0, &o);
	assert(!mt6797_data_rx_native(p, n, 36, own, ap, &mo, &ml));

	printf("native-rx: PASS (all 16 group masks x pad x QoS accepted at source offsets, IV/MIC verbatim; HDR_TRAN/AMSDU/unprotected/MoreFrag/Order/fragnum/ToDS/non-data/non-peer/CCMP-shape/bad-FCS/len-mismatch/short/wrong-channel withheld)\n");
	return 0;
}
