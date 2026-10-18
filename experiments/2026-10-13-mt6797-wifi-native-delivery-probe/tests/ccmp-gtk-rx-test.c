/* SPDX-License-Identifier: GPL-2.0-only */
/* Reuse the actual PTK fixture/layout builder; no firmware or delivery model. */
#include "ptk-baseline.inc"
#include "ccmp-gtk-rx.h"

static unsigned int gtk_cases;
static struct mt6797_ccmp_rx_context group_context(unsigned int key)
{
	struct mt6797_ccmp_rx_context c = context();

	c.pairwise = false;
	c.key_id = key;
	c.wlan_index = 2;
	return c;
}

static size_t group_frame(unsigned char *p, unsigned int groups, bool pad,
			  uint64_t pn, unsigned int key, bool multicast)
{
	size_t n = frame(p, groups, pad, pn), offset = 16;

	if (groups & 8) offset += 16;
	if (groups & 1) offset += 16;
	if (groups & 2) offset += 8;
	if (groups & 4) offset += 24;
	if (pad) offset += 2;
	p[4] = (key << 6) | (multicast ? 4 : 8);
	p[8] = 2;
	memset(p + offset, multicast ? 1 : 255, 6);
	return n;
}

static void group_check(unsigned char *p, size_t n,
			struct mt6797_ccmp_rx_context *c, bool accepted)
{
	struct mt6797_ccmp_rx_context before = *c, expected = *c;
	struct mt6797_ccmp_rx out, saved;
	unsigned char *exact = malloc(n ? n : 1);

	assert(exact);
	memcpy(exact, p, n);
	memset(&out, 0xa5, sizeof(out)); saved = out;
	assert(mt6797_ccmp_gtk_rx_check(exact, n, c, &out) == accepted);
	assert(!memcmp(exact, p, n));
	if (!accepted) {
		assert(!memcmp(c, &before, sizeof(before)));
		assert(!memcmp(&out, &saved, sizeof(saved)));
	} else {
		struct mt6797_data_rx metadata;

		assert(mt6797_data_rx(exact, n, c->channel, c->own, c->ap, 2, &metadata));
		assert(metadata.group && metadata.key_id == c->key_id);
		assert(out.offset == metadata.offset - 14 && out.bytes == n - out.offset);
		for (unsigned int i = 0; i < 6; i++) expected.pn[i] = p[37 - i];
		assert(!memcmp(c, &expected, sizeof(expected)));
		saved = out;
		assert(!mt6797_ccmp_gtk_rx_check(exact, n, c, &out));
		assert(!memcmp(c, &expected, sizeof(expected)));
		assert(!memcmp(&out, &saved, sizeof(saved)));
	}
	free(exact);
	gtk_cases++;
}

int main(void)
{
	unsigned char p[256], saved[256];
	struct mt6797_ccmp_rx_context c, ptk;
	struct mt6797_ccmp_rx out;
	size_t n;

	assert(ptk_baseline_tests() == 0);
	for (unsigned int key = 0; key < 4; key++)
		for (unsigned int groups = 0; groups < 16; groups++)
			for (unsigned int pad = 0; pad < 2; pad++) {
				n = group_frame(p, groups, pad, 1, key, key & 1);
				c = group_context(key);
				group_check(p, n, &c, (groups & 9) == 9);
				for (size_t cut = 0; cut < n; cut++) {
					c = group_context(key);
					group_check(p, cut, &c, false);
				}
				/* Also reach span checks with a matching short length:
				 * this builder has a 20-byte body, and at least one body
				 * byte is mandatory after the complete Ethernet header.
				 */
				for (size_t cut = 0; cut <= n - 20; cut++) {
					p[0] = cut; p[1] = cut >> 8;
					c = group_context(key); group_check(p, cut, &c, false);
				}
			}
	for (unsigned int key = 0; key < 4; key++) {
		n = group_frame(p, 15, true, 0x010203040501ULL, key, true);
		c = group_context(key); seed(&c, 0x010203040500ULL);
		group_check(p, n, &c, true);
		n = group_frame(p, 15, true, 0x010203040500ULL, key, true);
		group_check(p, n, &c, false);
		seed(&c, 0xffffffffffffULL);
		n = group_frame(p, 15, true, 0, key, true);
		group_check(p, n, &c, false);
	}
	n = group_frame(p, 9, false, 1, 1, false); memcpy(saved, p, n);
	for (unsigned int bit = 0; bit < 16; bit++) {
		memcpy(p, saved, n); p[10 + bit / 8] ^= 1U << (bit % 8);
		c = group_context(1); group_check(p, n, &c, false);
	}
	for (unsigned int key = 0; key < 4; key++) {
		memcpy(p, saved, n); c = group_context(key);
		group_check(p, n, &c, key == 1);
	}
	memcpy(p, saved, n); p[8] = 1;
	c = group_context(1); group_check(p, n, &c, false);
	memcpy(p, saved, n); memcpy(p + 48, own, 6);
	c = group_context(1); group_check(p, n, &c, false);
	memcpy(p, saved, n); p[18] ^= 2;
	c = group_context(1); group_check(p, n, &c, false);
	for (unsigned int field = 0; field < 13; field++) {
		memcpy(p, saved, n);
		if (field == 0) p[5] = 36;
		if (field == 1) p[6] ^= 0x80;
		if (field == 2) p[6] ^= 1;
		if (field == 3) p[9] ^= 0x10;
		if (field == 4) p[9] |= 1;
		if (field == 5) p[7] ^= 1;
		if (field == 6) p[17] |= 1;
		if (field == 7) p[16] |= 0x80;
		if (field == 8) p[24] |= 1;
		if (field == 9) p[26] |= 1;
		if (field == 10) p[3] ^= 0x20;
		if (field == 11) p[54] |= 1;
		if (field == 12) { p[60] = 0x88; p[61] = 0x8e; }
		c = group_context(1); group_check(p, n, &c, false);
	}
	for (unsigned int field = 0; field < 14; field++) {
		memcpy(p, saved, n); c = group_context(1);
		if (field == 0) c.active = false;
		if (field == 1) c.authorized = false;
		if (field == 2) c.seeded = false;
		if (field == 3) c.pairwise = true;
		if (field == 4) c.wlan_index = 1;
		if (field == 5) c.key_id = 4;
		if (field == 6) c.cipher = 0x000fac02U;
		if (field == 7) c.key_bytes = 15;
		if (field == 8) c.channel = 0;
		if (field == 9) c.rxd_bssid = 64;
		if (field == 10) memset(c.own, 0, sizeof(c.own));
		if (field == 11) memset(c.ap, 0, sizeof(c.ap));
		if (field == 12) c.own[0] |= 1;
		if (field == 13) c.ap[0] |= 1;
		group_check(p, n, &c, false);
	}
	/* Both actual checkers reject the other key class without PN mutation. */
	memcpy(p, saved, n); ptk = context(); c = ptk;
	assert(!mt6797_ccmp_rx_check(p, n, &ptk, &out));
	assert(!memcmp(&ptk, &c, sizeof(c)));
	n = frame(p, 9, false, 1); c = group_context(1);
	group_check(p, n, &c, false);
	n = group_frame(p, 9, false, 1, 1, false); c = group_context(1);
	assert(!mt6797_ccmp_gtk_rx_check(NULL, n, &c, &out));
	assert(!mt6797_ccmp_gtk_rx_check(p, n, NULL, &out));
	assert(!mt6797_ccmp_gtk_rx_check(p, n, &c, NULL));
	{
		unsigned char large[2353] = {0};

		memcpy(large, p, n); large[0] = 2353 & 255; large[1] = 2353 >> 8;
		assert(!mt6797_ccmp_gtk_rx_check(large, sizeof(large), &c, &out));
		large[0] = 2352 & 255; large[1] = 2352 >> 8;
		assert(mt6797_ccmp_gtk_rx_check(large, sizeof(large) - 1, &c, &out));
		assert(out.bytes == 2352 - 48 && c.pn[5] == 1);
	}
	printf("GTK checker: PASS %u exact-allocation/layout/key/PN/RA/status cases; PTK unchanged\n", gtk_cases);
	return 0;
}
