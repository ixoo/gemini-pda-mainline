/* SPDX-License-Identifier: GPL-2.0-only */
/* The receive reorder window (0321): the actual rx-reorder.h and the actual
 * mac.c glue around it (release, apply, expiry, drop and the routing in
 * mt6797_ccmp_queue_rx), in front of the actual strict pairwise PN check
 * on the frozen PTK fixture. Built by run-rx-reorder-test.py. The delivery
 * after the check is a stub that records the order; no HIF, worker or
 * mac80211.
 */
#define CONFIG_MT6797_WMM_QOS_DATA
#define CONFIG_MT6797_RX_AMPDU
#include "ptk-baseline.inc"
#include "rx-reorder.h"

typedef unsigned char u8;
typedef unsigned long long u64;
#define BIT(n) (1U << (n))
#define ENOMEM 12

struct sk_buff {
	unsigned int len;
	unsigned char *data;
	unsigned char buf[2400];
};
struct sk_buff_head { int unused; };
static unsigned int live, fail_alloc;
static struct sk_buff *dev_alloc_skb(unsigned int n)
{
	struct sk_buff *s;

	if (fail_alloc || n > sizeof(s->buf))
		return NULL;
	s = calloc(1, sizeof(*s));
	assert(s);
	s->data = s->buf;
	live++;
	return s;
}
static void skb_put_data(struct sk_buff *s, const void *d, unsigned int n)
{
	memcpy(s->data + s->len, d, n);
	s->len += n;
}
static void dev_kfree_skb(struct sk_buff *s)
{
	assert(live);
	live--;
	free(s);
}
static u64 now;
static u64 ktime_get_ns(void) { return now; }

struct mt6797_mac {
	unsigned char join_packet[2352];
	struct mt6797_ccmp_rx_context ccmp_rx;
	bool ready;
	unsigned char rx_ba_active;
	unsigned short rx_ba_window[8], rx_ba_ssn[8];
	struct mt6797_rx_reorder rx_reorder[MT6797_RX_REORDER_TIDS];
	unsigned char rx_reorder_pending;
	unsigned int rx_reorder_held, rx_reorder_released, rx_reorder_timeouts;
	unsigned int rx_reorder_duplicates, rx_reorder_behind, rx_reorder_dropped;
	unsigned int rx_reorder_plain, rx_reorder_max;
	unsigned int refused, delivered, order[512];
};
static bool mt6797_ccmp_rx_ready(struct mt6797_mac *mac) { return mac->ready; }

/* The checks the driver runs, then a record of the order. */
static int mt6797_ccmp_deliver_rx(struct mt6797_mac *mac, size_t bytes,
				  struct sk_buff_head *received)
{
	struct mt6797_ccmp_rx view;

	(void)received;
	if (!mt6797_ccmp_rx_ready(mac))
		return 0;
	if (!mt6797_ccmp_rx_check(mac->join_packet, bytes, &mac->ccmp_rx, &view)) {
		mac->refused++;
		return 0;
	}
	assert(mac->delivered < 512);
	mac->order[mac->delivered++] = mt6797_join_le16(mac->join_packet + 24) >> 4;
	return 0;
}
#include "rx-reorder-glue.inc"

static struct mt6797_mac m;
static struct sk_buff_head received;
static uint64_t pn_base = 1000;

/* A QoS data frame on TID 0, sequence seq, its PN given in sequence order
 * as the access point assigns it; status 0 is a block-ack sub-frame.
 */
static int arrive(unsigned int seq, uint64_t pn, unsigned int status)
{
	size_t n = frame(m.join_packet, 9, false, pn);

	m.join_packet[16] = 0x88;
	m.join_packet[24] = (seq << 4) & 0xff;
	m.join_packet[25] = seq >> 4;
	m.join_packet[10] = status;
	m.join_packet[11] = status >> 8;
	return mt6797_ccmp_queue_rx(&m, n, &received);
}

static void sub(unsigned int seq) { assert(!arrive(seq, pn_base + seq, 0)); }

static void session(unsigned int tid, unsigned int ssn, unsigned int window, bool start)
{
	if (start)
		m.rx_ba_active |= BIT(tid);
	else
		m.rx_ba_active &= ~BIT(tid);
	m.rx_ba_ssn[tid] = ssn;
	m.rx_ba_window[tid] = window;
	m.rx_reorder_pending |= BIT(tid);
	assert(!mt6797_rx_reorder_apply(&m, &received));
}

static void delivered(const unsigned int *seqs, unsigned int n)
{
	assert(m.delivered == n);
	for (unsigned int i = 0; i < n; i++)
		assert(m.order[i] == seqs[i]);
	m.delivered = 0;
}

static void reset(void)
{
	mt6797_rx_reorder_drop(&m);
	assert(!live);
	memset(&m, 0, sizeof(m));
	m.ccmp_rx = context();
	seed(&m.ccmp_rx, 1);
	m.ready = true;
	now = 1000000000ULL;
}

int main(void)
{
	(void)ptk_baseline_tests;
	/* Without a session (the parent's behaviour): boot AD's late hole is
	 * refused by the PN check.
	 */
	reset();
	sub(10); sub(11); sub(13); sub(14); sub(12);
	assert(m.refused == 1 && m.delivered == 4);

	/* With one: a late hole, here a plain (0xc000) retransmission, is
	 * delivered in sequence order and nothing is refused.
	 */
	reset();
	session(0, 100, 64, true);
	assert(m.rx_reorder[0].size == 68 && m.rx_reorder[0].waiting);
	sub(100); sub(101); sub(103); sub(104); sub(105);
	assert(!arrive(102, pn_base + 102, 0xc000));
	sub(106);
	delivered((const unsigned int[]){ 100, 101, 102, 103, 104, 105, 106 }, 7);
	assert(!m.refused && m.rx_reorder_held == 3 && m.rx_reorder_released == 3);
	assert(m.rx_reorder_plain == 1 && m.rx_reorder_max == 3 && !m.rx_reorder[0].has_bubble);

	/* A lost hole: released past at 200 ms, not before; the late copy is
	 * then behind the window and dropped, not refused.
	 */
	sub(107); sub(109); sub(110);
	assert(m.rx_reorder[0].has_bubble && m.rx_reorder[0].bubble == 108);
	now += 199 * 1000000ULL;
	assert(!mt6797_rx_reorder_expire_all(&m, &received) && m.delivered == 1);
	now += 1000000ULL;
	assert(!mt6797_rx_reorder_expire_all(&m, &received));
	delivered((const unsigned int[]){ 107, 109, 110 }, 3);
	assert(m.rx_reorder_timeouts == 1 && m.rx_reorder[0].holes == 1);
	assert(m.rx_reorder[0].start == 111 && !m.rx_reorder[0].has_bubble);
	sub(108);
	assert(m.rx_reorder_behind == 1 && !m.delivered && !m.refused);
	sub(111);
	delivered((const unsigned int[]){ 111 }, 1);

	/* A duplicate of a held frame is dropped once. */
	sub(113); sub(113);
	assert(m.rx_reorder_duplicates == 1);
	sub(112);
	delivered((const unsigned int[]){ 112, 113 }, 2);

	/* The first hole filled while another stays: the deadline restarts
	 * from the second (qmHandleEventCheckReorderBubble).
	 */
	sub(115); sub(117);		/* holes 114 and 116 */
	now += 100 * 1000000ULL;
	sub(114);
	delivered((const unsigned int[]){ 114, 115 }, 2);
	now += 100 * 1000000ULL;
	assert(!mt6797_rx_reorder_expire_all(&m, &received) && !m.delivered);
	assert(m.rx_reorder[0].bubble == 116);
	now += 199 * 1000000ULL;
	assert(!mt6797_rx_reorder_expire_all(&m, &received) && !m.delivered);
	now += 1000000ULL;
	assert(!mt6797_rx_reorder_expire_all(&m, &received));
	delivered((const unsigned int[]){ 117 }, 1);
	assert(m.rx_reorder[0].holes == 2);

	/* A frame ahead moves the window to end there: what falls out leaves
	 * (hole 118 skipped), then the window's frames in order.
	 */
	sub(119);
	sub(118 + 68 + 5);		/* the window now ends at 191 */
	delivered((const unsigned int[]){ 119 }, 1);
	assert(m.rx_reorder[0].start == 124 && m.rx_reorder[0].holes == 3);
	for (unsigned int s = 124; s < 191; s++)
		sub(s);
	assert(m.delivered == 68 && m.order[67] == 191 && !m.refused);
	m.delivered = 0;

	/* A full window held behind one hole: 68 frames, then the hole. */
	for (unsigned int s = 193; s < 193 + 67; s++)
		sub(s);
	assert(m.rx_reorder[0].count == 67 && !m.delivered && live == 67);
	sub(192);
	assert(m.delivered == 68 && !live && !m.refused);
	m.delivered = 0;

	/* A new ADDBA delivers what is held first, then starts again; the
	 * window wraps at 4096 with the PN continuing.
	 */
	sub(261);			/* held behind 260 */
	session(0, 4090, 64, true);
	delivered((const unsigned int[]){ 261 }, 1);
	pn_base = 5000;
	assert(!arrive(4090, pn_base, 0) && !arrive(4092, pn_base + 2, 0));
	assert(!arrive(4095, pn_base + 5, 0) && !arrive(0, pn_base + 6, 0));
	assert(!arrive(1, pn_base + 7, 0) && !arrive(4093, pn_base + 3, 0));
	assert(!arrive(4094, pn_base + 4, 0) && !arrive(4091, pn_base + 1, 0));
	delivered((const unsigned int[]){ 4090, 4091, 4092, 4093, 4094, 4095, 0, 1 }, 8);
	assert(!m.refused);

	/* DELBA: what is held is delivered and the TID's frames then go to
	 * the check directly.
	 */
	assert(!arrive(3, pn_base + 9, 0));	/* held behind 2 */
	session(0, 0, 0, false);
	delivered((const unsigned int[]){ 3 }, 1);
	assert(!m.rx_reorder[0].valid && !live);
	assert(!arrive(2, pn_base + 8, 0));
	assert(m.refused == 1 && !m.delivered);

	/* Waiting for the starting frame: one behind passes; the first in the
	 * window sets the start (the vendor's auto-advance), and earlier ones
	 * then fall behind.
	 */
	reset();
	session(0, 100, 64, true);
	sub(99);
	delivered((const unsigned int[]){ 99 }, 1);
	assert(m.rx_reorder[0].waiting);
	sub(102); sub(100);
	delivered((const unsigned int[]){ 102 }, 1);
	assert(m.rx_reorder_behind == 1 && !m.rx_reorder[0].waiting);

	/* Group, non-QoS, other-TID, error-status and closed-epoch frames
	 * bypass the window.
	 */
	{
		size_t n;

		sub(104);			/* held behind 103 */
		n = frame(m.join_packet, 9, false, pn_base + 105);
		m.join_packet[24] = (105 << 4) & 0xff; m.join_packet[25] = 105 >> 4;
		m.join_packet[10] = 0; m.join_packet[11] = 0;
		assert(!mt6797_ccmp_queue_rx(&m, n, &received));	/* non-QoS: direct */
		delivered((const unsigned int[]){ 105 }, 1);
		assert(!arrive(106, pn_base + 106, 0x0002));		/* FCS error: direct, refused */
		assert(m.refused == 1 && m.rx_reorder[0].count == 1);
		m.ready = false;
		sub(107);
		assert(m.refused == 1 && !m.delivered && m.rx_reorder[0].count == 1);
		m.ready = true;
	}

	/* No memory for a held frame: the error, and nothing changed. */
	fail_alloc = 1;
	assert(arrive(110, pn_base + 110, 0) == -ENOMEM);
	fail_alloc = 0;
	assert(m.rx_reorder[0].count == 1 && m.rx_reorder_held == 1);

	/* A lifetime reset counts and frees what is held. */
	sub(111);
	mt6797_rx_reorder_drop(&m);
	assert(m.rx_reorder_dropped == 2 && !live && !m.rx_reorder[0].valid);
	printf("rx reorder: PASS; late holes delivered in order with zero refusals, 200 ms release, behind/duplicate drops, ahead moves, wrap, ADDBA/DELBA flush, bypass, ENOMEM, reset frees\n");
	return 0;
}
