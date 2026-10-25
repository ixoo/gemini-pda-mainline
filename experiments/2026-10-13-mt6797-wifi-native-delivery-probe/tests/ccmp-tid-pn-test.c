/* SPDX-License-Identifier: GPL-2.0-only */
/* One CCMP replay counter per TID in both receive checks (0292). Built with
 * CONFIG_MT6797_WMM_QOS_DATA, on the frozen PTK and GTK fixtures:
 *   sed 's/^int main(void)/static int ptk_baseline_tests(void)/' ccmp-rx-test.c > ptk-baseline.inc
 *   sed 's/^int main(void)/static int gtk_baseline_tests(void)/' ccmp-gtk-rx-test.c > gtk-baseline.inc
 *   cc -DCONFIG_MT6797_WMM_QOS_DATA -I. -I<driver> ccmp-tid-pn-test.c
 */
#include "gtk-baseline.inc"

typedef bool (*checker)(const unsigned char *, size_t, struct mt6797_ccmp_rx_context *,
			struct mt6797_ccmp_rx *);

/* The fixture frame as QoS data on tid (group 4 frame control and QoS
 * control, descriptor byte 9's TID nibble), or left non-QoS when tid < 0.
 */
static size_t qos(unsigned char *p, size_t n, int tid)
{
	if (tid >= 0) {
		p[16] |= 0x80;
		p[26] = tid;
		p[27] = 0;
		p[9] = 0x40 | tid;
	}
	return n;
}

static bool admit(checker check, unsigned char *p, size_t n,
		  struct mt6797_ccmp_rx_context *c)
{
	struct mt6797_ccmp_rx_context before = *c;
	struct mt6797_ccmp_rx out;
	bool ok = check(p, n, c, &out);

	if (!ok)
		assert(!memcmp(c, &before, sizeof(before)));
	return ok;
}

static uint64_t last(const struct mt6797_ccmp_rx_context *c, unsigned int tid)
{
	const unsigned char *pn = tid ? c->tid_pn[tid - 1] : c->pn;
	uint64_t v = 0;

	for (unsigned int i = 0; i < 6; i++)
		v = (v << 8) | pn[i];
	return v;
}

static void per_tid(checker check, struct mt6797_ccmp_rx_context c, bool group)
{
	unsigned char p[256];
#define F(pn, tid) qos(p, group ? group_frame(p, 9, false, pn, 1, false) : \
		       frame(p, 9, false, pn), tid)
	/* TID 3 ahead; then TID 0 below it but above its own counter: boot S's case */
	assert(admit(check, p, F(100, 3), &c) && last(&c, 3) == 100 && last(&c, 0) == 0);
	assert(admit(check, p, F(50, 0), &c) && last(&c, 0) == 50 && last(&c, 3) == 100);
	/* each counter stays strict: equal and lower refused on the same TID */
	assert(!admit(check, p, F(50, 0), &c) && !admit(check, p, F(49, 0), &c));
	assert(!admit(check, p, F(100, 3), &c) && !admit(check, p, F(99, 3), &c));
	/* a non-QoS data frame shares TID 0's counter, as in mac80211 */
	assert(!admit(check, p, F(50, -1), &c) && admit(check, p, F(51, -1), &c));
	assert(last(&c, 0) == 51 && last(&c, 3) == 100);
	/* the other TIDs start from their own seeds; a TSPEC TID is refused */
	for (int tid = 1; tid < 8; tid++)
		if (tid != 3)
			assert(admit(check, p, F(1, tid), &c) && last(&c, tid) == 1);
	assert(!admit(check, p, F(1000, 8), &c) && !admit(check, p, F(1000, 15), &c));
	/* a TID whose QoS control and descriptor disagree is refused */
	{
		size_t n = F(200, 5);

		p[9] = 0x46;
		assert(!admit(check, p, n, &c) && last(&c, 5) == 1 && last(&c, 6) == 1);
	}
#undef F
}

int main(void)
{
	(void)gtk_baseline_tests; /* the non-WMM baselines run on their own */
	per_tid(mt6797_ccmp_rx_check, context(), false);
	per_tid(mt6797_ccmp_gtk_rx_check, group_context(1), true);
	printf("per-TID replay counters: PASS pairwise and group; strict per TID, non-QoS on TID 0, TSPEC refused\n");
	return 0;
}
