/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual reserved-frame retirement, cleanup and late-status helpers. */
static bool deauth_hif_ready;
#ifdef FIXTURE_GTK7
static int mt6797_hif_retain_cleanup_page(void *h)
{
	(void)h; assert(current->join_page_debt == 1); return 0;
}
static bool mt6797_hif_cleanup_ready(void *h)
#else
static bool mt6797_hif_cleanup_abort_ready(void *h)
#endif
{
	(void)h; return deauth_hif_ready;
}
static int mt6797_hif_join_pm_abort_debt(void *h, unsigned int seq,
		unsigned int pages, u64 deadline)
{
	assert(pages == 1 && current->join_page_debt == 2);
	return mt6797_hif_join_pm_abort(h, seq, deadline);
}
static void deauth_prepare(struct mt6797_mac *m, struct ieee80211_hw *hw,
		struct ieee80211_vif *v, struct ieee80211_sta *s)
{
	pm_prepare(m, hw, v, s); assert(!pm_associate(m)); pm_count = 0;
	m->join_cleanup_requested = m->join_data_phase = m->join_data_ended = true;
	m->native_diag_state = MT6797_ND_CLOSED;
	m->join_key_pairwise = m->join_key_group = 1; m->join_group_key_id = 1;
	m->join_internal = calloc(1, sizeof(struct sk_buff)); assert(m->join_internal);
	m->join_internal->len = 26; m->join_internal->data[0] = 0xc0;
	m->join_inflight = m->join_internal; m->join_pid = 33; m->join_next_pid = 34;
	m->join_frame_deadline = now + 750 * NSEC_PER_MSEC; m->join_page_debt = 1;
	deauth_hif_ready = true;
}
static void deauth_free(struct mt6797_mac *m, struct sk_buff_head *q)
{
	struct sk_buff *skb;
	while ((skb = __skb_dequeue(q))) dev_kfree_skb(skb);
	if (m->join_internal) dev_kfree_skb(m->join_internal);
	m->join_internal = m->join_inflight = NULL; destroy(m);
}

#ifndef FIXTURE_GTK7
static void deauth_retire_tests(void)
{
	struct mt6797_mac m, before;
	struct wiphy w = {{2, 0, 0, 0, 0, 1}};
	struct ieee80211_hw hw = {NULL, &w};
	struct ieee80211_vif v = {0};
	struct ieee80211_sta s = {{2, 0, 0, 0, 0, 2}, false, 0};
	struct sk_buff_head q;
	struct sk_buff *internal;

	for (int delta = -1; delta <= 1; delta++) {
		deauth_prepare(&m, &hw, &v, &s); skb_queue_head_init(&q); internal = NULL;
		before = m;
		bool retired = mt6797_ccmp_deauth_retire(&m, m.join_frame_deadline + delta, &q, &internal);
		assert(retired == (delta >= 0));
		if (retired) {
			assert(m.ccmp_deauth_timeouts == 1 && m.ccmp_deauth_retired_pid == 33);
			assert(m.join_page_debt == 1 && !m.join_inflight && !m.join_internal);
			assert(q.head == internal && !m.join_deauth_done && !m.join_last_acked && m.join_frame_done.done);
			assert(!mt6797_ccmp_deauth_retire(&m, m.join_frame_deadline + 1, &q, &internal));
		} else assert(!memcmp(&m, &before, sizeof(m)) && !q.head && !internal);
		deauth_free(&m, &q);
	}
	/* Each refusal leaves all owner/debt/completion state unchanged. */
	for (unsigned int mode = 0; mode < 13; mode++) {
		deauth_prepare(&m, &hw, &v, &s); skb_queue_head_init(&q); internal = NULL;
		if (mode == 0) m.first_error = -EIO;
		if (mode == 1) m.closing = true;
		if (mode == 2) m.join_inflight_data = true;
		if (mode == 3) m.join_page_debt = 2;
		if (mode == 4) m.join_credit_pending = true;
		if (mode == 5) m.join_data_page_debt = 1;
		if (mode == 6) m.join_data_ended = false;
		if (mode == 7) m.ccmp_pm_connected = false;
		if (mode == 8) m.join_internal->data[0] = 0x80;
		if (mode == 9) m.native_diag_state = MT6797_ND_DISABLE_PENDING;
		if (mode == 10) m.join_deadline = m.join_frame_deadline;
		if (mode == 11) m.join_cleanup_stage = 1;
		if (mode == 12) ccmp_stable_epoch = false;
		before = m;
		assert(!mt6797_ccmp_deauth_retire(&m, m.join_frame_deadline, &q, &internal));
		assert(!memcmp(&m, &before, sizeof(m)) && !q.head && !internal);
		ccmp_stable_epoch = true; deauth_free(&m, &q);
	}
	/* Only PM abort may start with the charged page. Partial return cannot
	 * acknowledge it or advance to key removal, even if one credit arrived.
	 */
	deauth_prepare(&m, &hw, &v, &s); skb_queue_head_init(&q); internal = NULL;
	now = m.join_frame_deadline;
	assert(mt6797_ccmp_deauth_retire(&m, now, &q, &internal)); pm_idle = false;
	mutex_lock(&m.mutex);
	assert(!mt6797_mac_join_cleanup_step(&m) && pm_count == 1 && pm_ops[0] == 0x17);
	assert(m.join_page_debt == 2 && m.join_credit_pending && m.ccmp_pm_abort_pending);
	assert(m.join_credit_deadline == now + 100 * NSEC_PER_MSEC);
	m.join_page_debt = 1;
	assert(!mt6797_mac_join_cleanup_step(&m) && pm_count == 1 && !m.ccmp_pm_abort_credited);
	m.join_page_debt = 0; m.join_credit_pending = false; pm_idle = true;
	for (unsigned int i = 0; i < 6; i++) {
		m.join_page_debt = 0; m.join_credit_pending = false;
		assert(!mt6797_mac_join_cleanup_step(&m));
	}
	assert(pm_count == 6 && pm_ops[1] == 0x71 && pm_ops[2] == 0x72 && pm_ops[3] == 0x14 && pm_ops[4] == 0x1c && pm_ops[5] == 0x0a);
	assert(m.join_cleanup_done && m.join_retired && m.ccmp_pm_abort_credited && !m.join_deauth_done);
	assert(m.ccmp_deauth_timeouts == 1 && pm_losses == 1);
	mutex_unlock(&m.mutex); deauth_free(&m, &q);
	/* The late exact owned PID is counted without a second free or credit. */
	deauth_prepare(&m, &hw, &v, &s); skb_queue_head_init(&q); internal = NULL;
	assert(mt6797_ccmp_deauth_retire(&m, m.join_frame_deadline, &q, &internal));
	memset(m.join_packet, 0, sizeof(m.join_packet)); m.join_packet[0] = 24;
	m.join_packet[3] = 0xe0; m.join_packet[4] = 0x0f; m.join_packet[8] = 33; m.join_packet[12] = 1;
	for (unsigned int bad = 0; bad < 4; bad++) {
		m.join_packet[8] = bad == 0 ? 34 : 33; m.join_packet[12] = bad == 1 ? 2 : 1;
		m.join_packet[9] = bad == 2 ? 8 : 0; before = m;
		if (bad < 3) assert(!mt6797_ccmp_deauth_late(&m, 24) && !memcmp(&m, &before, sizeof(m)));
		else {
			assert(mt6797_ccmp_deauth_late(&m, 24)); before.ccmp_deauth_late++;
			assert(!memcmp(&m, &before, sizeof(m)) && m.join_page_debt == 1 && q.head == internal);
		}
	}
	deauth_free(&m, &q);
	/* A later fatal guard in the same tick must retain the internal free
	 * classification; the generic terminal must not overwrite it with NULL.
	 */
	deauth_prepare(&m, &hw, &v, &s); skb_queue_head_init(&q); internal = NULL;
	assert(mt6797_ccmp_deauth_retire(&m, m.join_frame_deadline, &q, &internal));
	struct sk_buff *retired = internal;
	mutex_lock(&m.mutex);
	assert(mt6797_mac_join_fail_stop(&m, -EIO, 2, &q, &internal) == -EIO);
	assert(internal == retired && q.head == retired && !q.head->next && m.join_page_debt == 1);
	mutex_unlock(&m.mutex); deauth_free(&m, &q);
	puts("reserved deauth: PASS actual +/-1ns retirement, strict owner/poison gates, no ACK/refund, partial-credit block, original cleanup order and late owned PID only");
}

#endif
