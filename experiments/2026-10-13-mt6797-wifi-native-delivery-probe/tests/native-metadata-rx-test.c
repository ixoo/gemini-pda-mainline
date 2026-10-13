/* SPDX-License-Identifier: GPL-2.0-only */
#define main baseline_main
#include "native-rx-test.c"
#undef main
#include "parent-native.h"

static void same(unsigned char *p, size_t n, enum mt6797_native_rx_gate gate)
{
	size_t po = 991, pl = 992, co = 991, cl = 992;
	unsigned char saved[512];
	bool parent;

	memcpy(saved, p, sizeof(saved));
	parent = parent_native(p, n, 40, own, ap, &po, &pl);
	assert(mt6797_data_rx_native_gate(p, n, 40, own, ap, &co, &cl) == gate);
	assert(parent == (gate == MT6797_NATIVE_RX_OK));
	assert(po == co && pl == cl && !memcmp(p, saved, sizeof(saved)));
}

int main(void)
{
	unsigned char p[512];
	size_t n, o, mo = 991, ml = 992;
	unsigned int seed = 1;

	baseline_main();
#define BASE() (n = build_g(p, 5, 0, 0, &o))
	BASE(); same(p, n, MT6797_NATIVE_RX_OK);
	BASE(); same(p, 15, MT6797_NATIVE_RX_INPUT);
	assert(mt6797_data_rx_native_gate(NULL, n, 40, own, ap, &mo, &ml) ==
	       MT6797_NATIVE_RX_INPUT);
	assert(mt6797_data_rx_native_gate(p, n, 0, own, ap, &mo, &ml) ==
	       MT6797_NATIVE_RX_INPUT);
	BASE(); p[0]--; same(p, n, MT6797_NATIVE_RX_LENGTH);
	BASE(); p[3] = 0xe0; same(p, n, MT6797_NATIVE_RX_TYPE);
	BASE(); p[5] = 36; same(p, n, MT6797_NATIVE_RX_CHANNEL);
	BASE(); p[6] |= 0x80; same(p, n, MT6797_NATIVE_RX_TRANSLATED);
	BASE(); p[7] = 1; same(p, n, MT6797_NATIVE_RX_MSDU);
	BASE(); p[10] = 2; same(p, n, MT6797_NATIVE_RX_FCS);
	BASE(); p[6] = 23; same(p, n, MT6797_NATIVE_RX_HEADER);
	BASE(); n--; p[0]--; same(p, n, MT6797_NATIVE_RX_SPAN);
	BASE(); p[o] = 0; same(p, n, MT6797_NATIVE_RX_FRAME_TYPE);
	BASE(); p[o + 1] &= ~0x40; same(p, n, MT6797_NATIVE_RX_UNPROTECTED);
	BASE(); p[o + 1] |= 1; same(p, n, MT6797_NATIVE_RX_DS);
	BASE(); p[o + 1] |= 4; same(p, n, MT6797_NATIVE_RX_FRAME_SHAPE);
	BASE(); p[o + 10] ^= 8; same(p, n, MT6797_NATIVE_RX_PEER);
	BASE(); p[o + 5] ^= 8; same(p, n, MT6797_NATIVE_RX_DESTINATION);
	BASE(); p[o + 26] = 1; same(p, n, MT6797_NATIVE_RX_CCMP_SHAPE);
	/* Multiple failures name only the FIRST gate, never all failed gates. */
	BASE(); p[5] = 36; p[6] |= 0x80;
	same(p, n, MT6797_NATIVE_RX_CHANNEL);
	BASE(); p[6] |= 0x80; p[o + 1] &= ~0x40;
	same(p, n, MT6797_NATIVE_RX_TRANSLATED);
	/* Deterministic synthetic mutations, not any retained traffic. */
	for (unsigned int k = 0; k < 20000; k++) {
		size_t po = 991, pl = 992, co = 991, cl = 992;
		bool parent, child;

		n = build_g(p, k & 15, (k >> 4) & 1, (k >> 5) & 1, &o);
		seed = seed * 1664525U + 1013904223U;
		p[seed % n] ^= (seed >> 24) | 1;
		if (k & 1) n = seed % (n + 1);
		parent = parent_native(p, n, 40, own, ap, &po, &pl);
		child = mt6797_data_rx_native(p, n, 40, own, ap, &co, &cl);
		assert(parent == child && po == co && pl == cl);
	}
	puts("native metadata RX: every first gate; unchanged decisions/outputs on 20000 mutations");
	return 0;
}
