/* SPDX-License-Identifier: GPL-2.0-only */
/* The pairwise receive check's status word (0319): with
 * CONFIG_MT6797_RX_AMPDU a block-ack sub-frame, (status & 0xffbf) == 0, is
 * admitted beside 0xc000; every error flag, and a single A-MPDU bit, stays
 * refused; the strict per-TID PN applies to sub-frames unchanged. Built by
 * run-ccmp-ba-status-test.py on the frozen PTK fixture, with the option
 * (BA_ADMITTED 1) and without it (BA_ADMITTED 0, the parent's behaviour).
 */
#include "ptk-baseline.inc"

static void status(unsigned char *p, unsigned int s)
{
	p[10] = s;
	p[11] = s >> 8;
}

/* An admitted sub-frame is decided exactly as the same frame with status
 * 0xc000: the same Ethernet view and the same committed PN; a refused one
 * changes nothing (the fixture's own check).
 */
static void sub_frame(unsigned char *p, size_t n, struct mt6797_ccmp_rx_context *c,
		      bool accepted)
{
	struct mt6797_ccmp_rx_context reference = *c;
	struct mt6797_ccmp_rx out, expected;
	unsigned char q[256];

	if (!accepted) {
		check(p, n, c, false);
		return;
	}
	memcpy(q, p, n);
	status(q, 0xc000);
	assert(mt6797_ccmp_rx_check(q, n, &reference, &expected));
	assert(mt6797_ccmp_rx_check(p, n, c, &out));
	assert(out.offset == expected.offset && out.bytes == expected.bytes);
	assert(!memcmp(c, &reference, sizeof(reference)));
	/* the committed PN refuses a replay of the same sub-frame */
	assert(!mt6797_ccmp_rx_check(p, n, c, &out));
}

int main(void)
{
	static const unsigned int refused[] = {
		0x0002, 0x0004, 0x0008, 0x0010, 0x0020, 0x0080, 0x0100, 0x0200,
		0x0400, 0x0800, 0x1000, 0x2000, 0x4000, 0x8000, 0x4040, 0xc040,
	};
	struct mt6797_ccmp_rx_context c = context();
	unsigned char p[256];
	uint64_t pn = 11;
	size_t n;

	(void)ptk_baseline_tests; /* the baseline runs on its own */
	seed(&c, 10);
	n = frame(p, 9, false, pn++);
	check(p, n, &c, true);
	/* a block-ack sub-frame, and one with LEN_MISMATCH (bit 6) */
	n = frame(p, 9, false, pn);
	status(p, 0x0000);
	sub_frame(p, n, &c, BA_ADMITTED);
	pn += BA_ADMITTED;
	n = frame(p, 9, false, pn);
	status(p, 0x0040);
	sub_frame(p, n, &c, BA_ADMITTED);
	pn += BA_ADMITTED;
	/* any other flag, or one inverted A-MPDU bit alone, stays refused */
	for (unsigned int i = 0; i < sizeof(refused) / sizeof(refused[0]); i++) {
		n = frame(p, 9, false, pn);
		status(p, refused[i]);
		check(p, n, &c, false);
	}
	/* the strict PN holds for sub-frames: a lower one is refused */
	n = frame(p, 9, false, pn - 2);
	status(p, 0x0000);
	check(p, n, &c, false);
	printf("block-ack status word: PASS with admission=%d; error flags and lone A-MPDU bits refused, strict PN unchanged\n",
	       BA_ADMITTED);
	return 0;
}
