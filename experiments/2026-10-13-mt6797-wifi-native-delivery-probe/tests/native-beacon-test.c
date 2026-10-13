/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include "native-beacon.h"
#include "scan-wire.h"
#include "action-frame.h"
#include "data-rx.h"

static const unsigned char ap[6] = {2, 0, 0, 0, 0, 2};
static const unsigned char own[6] = {2, 0, 0, 0, 0, 1};

static size_t build_beacon(unsigned char p[512], unsigned int groups, bool pad,
			   size_t *off)
{
	size_t o = 16, vector = 0, n;
	unsigned int type = (2U << 13) | (groups << 9);

	memset(p, 0, 512);
	if (groups & 8) o += 16;
	if (groups & 1) o += 16;
	if (groups & 2) o += 8;
	if (groups & 4) { vector = o; o += 24; }
	if (pad) o += 2;
	n = o + 40;
	p[0] = n; p[1] = n >> 8; p[2] = type; p[3] = type >> 8;
	p[5] = 40; p[6] = 24 | (pad ? 0x40 : 0);
	p[10] = 4; p[11] = 0xe0; /* no FCS/ICV error; no security inference */
	if (vector) p[vector + 9] = 110;
	p[o] = 0x80;
	memset(p + o + 4, 0xff, 6);
	memcpy(p + o + 10, ap, 6); memcpy(p + o + 16, ap, 6);
	p[o + 32] = 100; /* standard beacon interval, synthetic body */
	p[o + 36] = 0; p[o + 37] = 2; p[o + 38] = 't'; p[o + 39] = 's';
	*off = o;
	return n;
}

static void rejected(unsigned char *p, size_t n)
{
	struct mt6797_native_beacon b = {991, 992, 993};
	unsigned char saved[512];

	memcpy(saved, p, sizeof(saved));
	assert(!mt6797_native_beacon(p, n, 40, ap, &b));
	assert(b.offset == 991 && b.bytes == 992 && b.rcpi == 993);
	assert(!memcmp(saved, p, sizeof(saved)));
}

int main(void)
{
	unsigned char p[512];
	size_t n, off, mo = 991, ml = 992;
	struct mt6797_native_beacon b;
	struct mt6797_scan_frame s;
	struct mt6797_join_action_frame a;

	for (unsigned int g = 0; g < 16; g++)
		for (unsigned int pad = 0; pad < 2; pad++) {
			n = build_beacon(p, g, pad, &off);
			if (!(g & 4)) { rejected(p, n); continue; }
			assert(mt6797_native_beacon(p, n, 40, ap, &b));
			assert(b.offset == off && b.bytes == 40 && b.rcpi == 110);
			/* Actual old selectors reject the class2 format. The ordinary
			 * data predicate still refuses a management frame. */
			assert(mt6797_scan_frame(p, n, &s) != 0);
			assert(!mt6797_join_keyed_beacon(p, n, 40, ap, 2, &a));
			assert(mt6797_data_rx_native_gate(p, n, 40, own, ap, &mo, &ml) ==
			       MT6797_NATIVE_RX_FRAME_TYPE);
		}
#define BASE() (n = build_beacon(p, 15, true, &off))
	BASE(); rejected(p, 15);
	BASE(); p[0]--; rejected(p, n);
	BASE(); p[3] = 0xee; p[2] = 1; rejected(p, n); /* class7 unchanged */
	BASE(); p[5] = 36; rejected(p, n);
	BASE(); p[6] |= 0x80; rejected(p, n);
	BASE(); p[6] = (p[6] & 0xc0) | 26; rejected(p, n);
	BASE(); p[7] |= 1; rejected(p, n);
	BASE(); p[10] |= 2; rejected(p, n);
	BASE(); p[10] |= 16; rejected(p, n);
	BASE(); p[16 + 16 + 16 + 8 + 9] = 221; rejected(p, n);
	BASE(); p[off] = 0x50; rejected(p, n); /* probe response */
	BASE(); p[off] = 0x08; rejected(p, n); /* data */
	BASE(); p[off] |= 1; rejected(p, n); /* version */
	for (unsigned int bit = 0; bit < 8; bit++) {
		if (!((1U << bit) & 0xc7)) continue;
		BASE(); p[off + 1] |= 1U << bit; rejected(p, n);
	}
	BASE(); p[off + 22] = 1; rejected(p, n);
	for (unsigned int i = 4; i < 22; i++) {
		BASE(); p[off + i] ^= 2; rejected(p, n);
	}
	/* Every truncation before the end of the required fixed fields is refused,
	 * even when the reported byte count is adjusted to match the short buffer. */
	BASE();
	for (size_t short_n = 0; short_n < off + 36; short_n++) {
		p[0] = short_n; p[1] = short_n >> 8;
		rejected(p, short_n);
	}
	assert(!mt6797_native_beacon(NULL, n, 40, ap, &b));
	assert(!mt6797_native_beacon(p, n, 0, ap, &b));
	assert(!mt6797_native_beacon(p, n, 40, NULL, &b));
	assert(!mt6797_native_beacon(p, n, 40, ap, NULL));
	assert(!mt6797_native_beacon(p, 4097, 40, ap, &b));
	/* Exhaustive one-bit mutations of one synthetic frame: only a matching
	 * complete beacon may return a span, and failure cannot change outputs. */
	BASE();
	for (size_t pos = 0; pos < n; pos++)
		for (unsigned int bit = 0; bit < 8; bit++) {
			struct mt6797_native_beacon mutated = {991, 992, 993};
			unsigned char saved[512];
			bool ok;

			BASE(); p[pos] ^= 1U << bit;
			memcpy(saved, p, sizeof(saved));
			ok = mt6797_native_beacon(p, n, 40, ap, &mutated);
			assert(!memcmp(saved, p, sizeof(saved)));
			if (ok) {
				assert(mutated.offset <= n && mutated.bytes == n - mutated.offset);
				assert(mutated.bytes >= 36 && mutated.rcpi <= 220);
				assert((mt6797_join_le16(p + mutated.offset) & 0xc7ff) == 0x0080);
				assert(!memcmp(p + mutated.offset + 10, ap, 6));
				assert(!memcmp(p + mutated.offset + 16, ap, 6));
			} else {
				assert(mutated.offset == 991 && mutated.bytes == 992 && mutated.rcpi == 993);
			}
		}
	puts("native beacon layout: PASS all16 masks/pad, strict frame/address/bounds/errors; synthetic only");
	return 0;
}
