/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdint.h>
#include <stdlib.h>
#define main translated_baseline_main
#include "../../2026-10-07-mt6797-wifi-phase-b-join/tests/data-rx-test.c"
#undef main
#include "ccmp-rx.h"

/* All addresses and PN values here are neutral synthetic fixture constants. */
static struct mt6797_ccmp_rx_context context(void)
{
	struct mt6797_ccmp_rx_context c = {0};

	c.authorized = c.active = c.seeded = c.pairwise = true;
	c.cipher = 0x000fac04U;
	c.key_bytes = 16;
	c.wlan_index = c.rxd_bssid = 1;
	c.channel = 40;
	memcpy(c.own, own, 6);
	memcpy(c.ap, ap, 6);
	return c;
}

static void seed(struct mt6797_ccmp_rx_context *c, uint64_t pn)
{
	for (unsigned int i = 0; i < 6; i++) c->pn[5 - i] = pn >> (8 * i);
}

static size_t frame(unsigned char *p, unsigned int groups, bool pad, uint64_t pn)
{
	unsigned char base[256];
	size_t n = build(base, false, false, 20), at = 16;
	unsigned int type = (2U << 13) | (groups << 9);

	memset(p, 0, 256);
	memcpy(p, base, 16);
	p[2] = type; p[3] = type >> 8;
	if (groups & 8) { memcpy(p + at, base + 16, 16); at += 16; }
	if (groups & 1) {
		for (unsigned int i = 0; i < 6; i++) p[at + i] = pn >> (8 * i);
		at += 16;
	}
	if (groups & 2) at += 8;
	if (groups & 4) at += 24;
	if (pad) { p[6] |= 0x40; at += 2; }
	memcpy(p + at, base + 32, n - 32);
	n = at + n - 32;
	p[0] = n; p[1] = n >> 8;
	return n;
}

static void check(unsigned char *p, size_t n, struct mt6797_ccmp_rx_context *c,
		  bool accepted)
{
	struct mt6797_ccmp_rx_context before = *c, expected = *c;
	struct mt6797_ccmp_rx out, saved;
	unsigned char *exact = malloc(n ? n : 1);
	size_t off;

	assert(exact);
	memcpy(exact, p, n);
	memset(&out, 0xa5, sizeof(out)); saved = out;
	assert(mt6797_ccmp_rx_check(exact, n, c, &out) == accepted);
	assert(!memcmp(exact, p, n));
	if (!accepted) {
		assert(!memcmp(c, &before, sizeof(before)));
		assert(!memcmp(&out, &saved, sizeof(out)));
	} else {
		struct mt6797_data_rx legacy;
		assert(mt6797_data_rx(exact, n, c->channel, c->own, c->ap, 2, &legacy));
		off = legacy.offset - 14;
		assert(out.offset == off && out.bytes == n - off);
		for (unsigned int i = 0; i < 6; i++) expected.pn[i] = p[37 - i];
		assert(!memcmp(c, &expected, sizeof(expected)));
		/* Decision unit has no delivery API. A repeated call is rejected and
		 * cannot change the already committed replay state. */
		saved = out;
		assert(!mt6797_ccmp_rx_check(exact, n, c, &out));
		assert(!memcmp(c, &expected, sizeof(expected)));
		assert(!memcmp(&out, &saved, sizeof(out)));
	}
	free(exact);
}

int main(void)
{
	unsigned char p[256];
	struct mt6797_ccmp_rx_context c;
	struct mt6797_ccmp_rx out;
	size_t n;

	translated_baseline_main();
#define BASE() do { c = context(); n = frame(p, 9, false, 1); } while (0)
	BASE(); assert(!mt6797_ccmp_rx_check(NULL, n, &c, &out));
	assert(!mt6797_ccmp_rx_check(p, n, NULL, &out));
	assert(!mt6797_ccmp_rx_check(p, n, &c, NULL));
	assert(!mt6797_ccmp_rx_check(p, 2353, &c, &out));
	{
		unsigned char *maximum = calloc(1, 2352);
		assert(maximum);
		memcpy(maximum, p, n); maximum[0] = 2352 & 255; maximum[1] = 2352 >> 8;
		check(maximum, 2352, &c, true);
		free(maximum);
	}
	for (unsigned int g = 0; g < 16; g++)
		for (unsigned int pad = 0; pad < 2; pad++) {
			c = context(); n = frame(p, g, pad, 1);
			check(p, n, &c, (g & 9) == 9);
		}
	/* Every truncation ends at an ASan allocation boundary, not a large
	 * backing buffer; declared length is adjusted to reach later checks. */
	for (unsigned int g = 9; g < 16; g += 2) {
		BASE(); n = frame(p, g, true, 1);
		for (size_t len = 0; len < n; len++) {
			c = context(); p[0] = len; p[1] = len >> 8;
			/* Cutting only payload can leave a legitimate shorter frame. */
			check(p, len, &c, len > n - 20);
		}
	}
	for (unsigned int bit = 0; bit < 16; bit++) {
		BASE(); p[10 + bit / 8] ^= 1U << (bit % 8); check(p, n, &c, false);
	}
	for (unsigned int bit = 0; bit < 8; bit++) {
		BASE(); p[4] ^= 1U << bit; check(p, n, &c, false);
	}
	for (unsigned int bit = 0; bit < 16; bit++) {
		BASE(); p[16 + bit / 8] ^= 1U << (bit % 8);
		check(p, n, &c, bit == 11 || bit == 13); /* Retry/MoreData allowed */
	}
	for (unsigned int field = 0; field < 17; field++) {
		BASE();
		switch (field) {
		case 0: p[0]--; break;
		case 1: p[3] = (p[3] & 31) | (7U << 5); break;
		case 2: p[4] = 0x04; break; /* GTK/MC */
		case 3: p[4] = 0x08; break; /* GTK/BC */
		case 4: p[4] |= 0x40; break; /* other keyID */
		case 5: p[5]++; break;
		case 6: p[6] &= ~0x80; break;
		case 7: p[6]--; break;
		case 8: p[7] |= 1; break; /* AMSDU payload */
		case 9: p[7] += 4; break; /* other RXD BSSID */
		case 10: p[8]++; break;
		case 11: p[9]++; break; /* nonzero TID outside non-QoS scope */
		case 12: p[9] = 0; break; /* not CCMP */
		case 13: p[18] ^= 4; break;
		case 14: p[24] |= 1; break; /* fragment number */
		case 15: p[26] = 1; break; /* QoS metadata */
		case 16: p[28] = 1; break; /* HTC */
		}
		check(p, n, &c, false);
	}
	BASE(); c.rxd_bssid = 64; check(p, n, &c, false);
	BASE(); c.channel = 0; check(p, n, &c, false);
	BASE(); c.ap[0] |= 1; check(p, n, &c, false);
	for (unsigned int field = 0; field < 6; field++) {
		BASE();
		switch (field) {
		case 0: p[48] ^= 4; break;
		case 1: p[54] |= 1; break;
		case 2: memset(p + 54, 0, 6); break;
		case 3: p[60] = 0; p[61] = 20; break; /* length, not EtherType */
		case 4: p[60] = 0x88; p[61] = 0x8e; break; /* control port */
		case 5: p[48] |= 1; break; /* group destination with UC match */
		}
		check(p, n, &c, false);
	}
	for (unsigned int field = 0; field < 15; field++) {
		BASE();
		switch (field) {
		case 0: c.authorized = false; break;
		case 1: c.active = false; break; /* host removal gate */
		case 2: c.seeded = false; break;
		case 3: c.pairwise = false; break; /* GTK context excluded */
		case 4: c.cipher++; break;
		case 5: c.key_bytes++; break;
		case 6: c.key_id++; break;
		case 7: c.wlan_index++; break;
		case 8: c.rxd_bssid++; break;
		case 9: c.channel++; break;
		case 10: c.own[5]++; break;
		case 11: c.ap[5]++; break;
		case 12: memset(c.own, 0, 6); break;
		case 13: memset(c.ap, 0, 6); break;
		case 14: c.own[0] |= 1; break;
		}
		check(p, n, &c, false);
	}
	/* Strict seeded ordering, little-endian decode and every byte carry. */
	for (unsigned int byte = 0; byte < 6; byte++) {
		uint64_t boundary = UINT64_C(1) << (8 * byte);
		c = context(); seed(&c, boundary - 1);
		n = frame(p, 9, false, boundary); check(p, n, &c, true);
		n = frame(p, 9, false, boundary - 1); check(p, n, &c, false);
		n = frame(p, 9, false, boundary); check(p, n, &c, false);
	}
	BASE(); n = frame(p, 9, false, 0); check(p, n, &c, false);
	c = context(); seed(&c, UINT64_C(0xfffffffffffe));
	n = frame(p, 9, false, UINT64_C(0xffffffffffff)); check(p, n, &c, true);
	n = frame(p, 9, false, 0); check(p, n, &c, false); /* no wrap */
	/* Same-key host reinstall must retain the existing seed. Deliberately no
	 * caller generation field or same-slot new-epoch success test: neither
	 * would detect old firmware-queued frames. */
	BASE(); seed(&c, 1); check(p, n, &c, false);
	c.active = false; n = frame(p, 9, false, 2); check(p, n, &c, false);
	c.active = true; check(p, n, &c, true); /* host state only, not firmware rekey */
	puts("CCMP offline decision: PASS bounds/context/errors/PTK-only/strict PN; no delivery or epoch claim");
	return 0;
}
