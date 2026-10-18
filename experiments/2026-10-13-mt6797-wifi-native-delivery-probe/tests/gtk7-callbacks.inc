/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual MAC bodies; simulated wire/credits do not establish firmware behavior. */
static void gtk7_start(struct mt6797_mac *m, struct ieee80211_hw *hw,
		struct ieee80211_vif *v, struct ieee80211_sta *sta)
{
	deauth_prepare(m, hw, v, sta);
	m->join_inflight = NULL; m->join_page_debt = 0;
	__skb_queue_tail(&m->join_queue, m->join_internal);
	assert(mt6797_ccmp_pm_holds_deauth(m));
	mutex_lock(&m->mutex);
	assert(!mt6797_mac_join_cleanup_step(m));
	assert(pm_count == 1 && pm_ops[0] == 0x17 && m->join_page_debt == 1);
	assert(m->ccmp_cleanup_credit_floor == 0 && !mt6797_ccmp_cleanup_credit_ready(m));
	assert(m->join_internal == m->join_queue.head && !m->join_inflight);
	m->join_page_debt = 0; assert(mt6797_ccmp_cleanup_credit_ready(m));
	mt6797_ccmp_cleanup_timing(m, true);
	m->join_credit_pending = m->ccmp_cleanup_credit_active = false;
	assert(!mt6797_mac_join_cleanup_step(m) && pm_count == 1);
	assert(m->ccmp_pm_abort_credited && !m->ccmp_pm_connected && !mt6797_ccmp_pm_holds_deauth(m));
	assert(__skb_dequeue(&m->join_queue) == m->join_internal);
	m->join_inflight = m->join_internal; m->join_page_debt = 1;
	m->join_frame_deadline = now + 750 * NSEC_PER_MSEC;
	mutex_unlock(&m->mutex);
}
static void gtk7_finish(struct mt6797_mac *m, unsigned int floor)
{
	mutex_lock(&m->mutex);
	for (unsigned int i = 0; i < 6; i++) {
		assert(!mt6797_mac_join_cleanup_step(m));
		if (m->join_credit_pending) {
			assert(m->ccmp_cleanup_credit_floor == floor && m->join_page_debt == floor + 1);
			assert(m->join_credit_deadline == now + 100 * NSEC_PER_MSEC);
			assert(!mt6797_ccmp_cleanup_credit_ready(m));
			m->join_page_debt = floor;
			assert(mt6797_ccmp_cleanup_credit_ready(m));
			mt6797_ccmp_cleanup_timing(m, true);
			m->join_credit_pending = m->ccmp_cleanup_credit_active = false;
		}
	}
	assert(pm_count == 6 && pm_ops[0] == 0x17 && pm_ops[1] == 0x71 &&
	       pm_ops[2] == 0x72 && pm_ops[3] == 0x14 && pm_ops[4] == 0x1c && pm_ops[5] == 0x0a);
	assert(m->join_cleanup_done && m->join_retired && m->join_page_debt == floor);
	assert(m->ccmp_cleanup_bounded_done == (floor == 1));
	assert(m->join_cleanup_stage == (floor ? 4U : 3U));
	assert(pm_losses == 1);
	mutex_unlock(&m->mutex);
}
static void gtk7_callback_tests(void)
{
	struct mt6797_mac m, before;
	struct wiphy w = {{2, 0, 0, 0, 0, 1}};
	struct ieee80211_hw hw = {NULL, &w};
	struct ieee80211_vif v = {0};
	struct ieee80211_sta sta = {{2, 0, 0, 0, 0, 2}, false, 0};
	struct sk_buff_head discard;
	struct sk_buff *internal;
	unsigned int healthy, bounded;

	/* Whole-ledger path: PM credit before deauth, then the existing removals. */
	gtk7_start(&m, &hw, &v, &sta); healthy = gtk7_healthy_logs; bounded = gtk7_bounded_logs;
	dev_kfree_skb(m.join_internal); m.join_internal = m.join_inflight = NULL;
	m.join_deauth_done = true; m.join_page_debt = 0;
	gtk7_finish(&m, 0);
	assert(gtk7_healthy_logs == healthy + 1 && gtk7_bounded_logs == bounded);
	skb_queue_head_init(&discard); deauth_free(&m, &discard);
	/* A charged retired page survives every cleanup command and terminal. */
	gtk7_start(&m, &hw, &v, &sta); healthy = gtk7_healthy_logs; bounded = gtk7_bounded_logs;
	skb_queue_head_init(&discard); internal = NULL; now = m.join_frame_deadline;
	assert(mt6797_ccmp_deauth_retire(&m, now, &discard, &internal));
	assert(m.ccmp_cleanup_retained_pages == 1 && m.join_page_debt == 1 && !m.join_deauth_done);
	memset(m.join_packet, 0, sizeof(m.join_packet)); m.join_packet[0] = 24;
	m.join_packet[3] = 0xe0; m.join_packet[4] = 0x0f;
	m.join_packet[8] = m.ccmp_deauth_retired_pid; m.join_packet[12] = 1;
	before = m; assert(mt6797_ccmp_deauth_late(&m, 24)); before.ccmp_deauth_late++;
	assert(!memcmp(&m, &before, sizeof(m)) && m.join_page_debt == 1);
	m.join_packet[8]++; before = m; assert(!mt6797_ccmp_deauth_late(&m, 24));
	assert(!memcmp(&m, &before, sizeof(m)));
	pm_idle = false; gtk7_finish(&m, 1);
	assert(m.join_closed && gtk7_healthy_logs == healthy && gtk7_bounded_logs == bounded + 1);
	assert(!mt6797_ccmp_disable_key(&m));
	assert(strstr(last_log, "disable bounded:") && strstr(last_log, "resource_debt=1 no_reuse=1"));
	deauth_free(&m, &discard);
	/* If the old page returns before a later command, its floor is zero.
	 * Merely having a quarantine budget cannot acknowledge a fresh debit.
	 */
	gtk7_start(&m, &hw, &v, &sta); healthy = gtk7_healthy_logs;
	skb_queue_head_init(&discard); internal = NULL; now = m.join_frame_deadline;
	assert(mt6797_ccmp_deauth_retire(&m, now, &discard, &internal));
	m.join_page_debt = 0; pm_idle = true; gtk7_finish(&m, 0);
	assert(gtk7_healthy_logs == healthy + 1 && !m.ccmp_cleanup_bounded_done);
	deauth_free(&m, &discard);
	/* No borrowed queue entry or in-flight frame may be hidden for abort. */
	deauth_prepare(&m, &hw, &v, &sta); pm_count = 0;
	mutex_lock(&m.mutex); assert(!mt6797_mac_join_cleanup_step(&m) && !pm_count); mutex_unlock(&m.mutex);
	skb_queue_head_init(&discard); deauth_free(&m, &discard);
	/* Exact clock diagnostics: no future/absent clock claim or state changes. */
	pm_prepare(&m, &hw, &v, &sta); m.ccmp_pm_credit_ns = now - 1000;
	m.join_beacons_delivered = 8; m.ccmp_beacons_at_pm_credit = 2;
	m.ccmp_last_beacon_rx = now - 100; m.join_beacon_interval = 100;
	before = m; mt6797_ccmp_data_end_beacons(&m);
	assert(strstr(last_log, "count=8 known=1 age_ns=100 since_pm_known=1 since_pm=6 interval_tu=100"));
	assert(!memcmp(&m, &before, sizeof(m)));
	mt6797_ccmp_tx_timing(&m, 34, 0, 1); assert(strstr(last_log, "pid=34 status=0 class=1") && strstr(last_log, "pm_offset_ns=1000"));
	m.ccmp_cleanup_credit_active = true; m.ccmp_cleanup_op = 4; m.ccmp_cleanup_sequence = 31;
	m.ccmp_cleanup_credit_floor = m.ccmp_cleanup_retained_pages = m.join_page_debt = 1;
	mt6797_ccmp_cleanup_timing(&m, true); assert(strstr(last_log, "op=4 sequence=31 credit=1") && strstr(last_log, "floor=1 debt=1"));
	m.ccmp_cleanup_credit_floor = 0; assert(!mt6797_ccmp_cleanup_credit_ready(&m));
	m.join_page_debt = 0; assert(mt6797_ccmp_cleanup_credit_ready(&m));
	m.ccmp_pm_credit_ns = now + 1; strcpy(last_log, "untouched"); mt6797_ccmp_tx_timing(&m, 34, 0, 1); assert(!strcmp(last_log, "untouched"));
	m.ccmp_last_beacon_rx = now + 1; mt6797_ccmp_data_end_beacons(&m); assert(strstr(last_log, "known=0 age_ns=0"));
	destroy(&m);
	puts("GTK7 actual MAC: PASS PM-before-deauth credit fence, bounded/whole terminals, per-command floors and clock/beacon scalars; no firmware claim");
}
