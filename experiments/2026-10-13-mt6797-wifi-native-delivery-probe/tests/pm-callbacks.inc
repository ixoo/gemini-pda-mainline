/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual association/PM/cleanup bodies; only poller credit and wire are mocked. */
static bool pm_mode, pm_idle;
static int pm_metadata, pm_wire_error, pm_credit_error, pm_credit_edge, pm_guard_error;
static unsigned int pm_ops[16], pm_count, pm_pending, pm_losses;
static void pm_reset_world(void)
{
	pm_mode = false; pm_idle = true;
	pm_metadata = pm_wire_error = pm_credit_error = pm_credit_edge = pm_guard_error = 0;
	pm_count = pm_pending = pm_losses = 0;
	memset(pm_ops, 0, sizeof(pm_ops));
}
static int pm_record(unsigned int cid, u64 deadline)
{
	assert(deadline > now && deadline <= now + 100 * NSEC_PER_MSEC);
	assert(pm_count < 16); pm_ops[pm_count++] = cid; pm_pending = cid;
	return pm_wire_error;
}
static bool mt6797_hif_normal_idle(void *h) { (void)h; return pm_idle; }
static void mt6797_hif_normal_ledger(void *h, struct mt6797_hif_ledger *l)
{
	(void)h; memset(l, 0, sizeof(*l));
}
static int mt6797_mac_join_guard(struct mt6797_mac *m, u64 deadline)
{
	(void)m; return pm_guard_error ? pm_guard_error : deadline <= now ? -ETIMEDOUT : 0;
}
static int mt6797_hif_join_bss(void *h, unsigned int seq, const u8 *ap, const u8 *ssid,
		unsigned int bytes, unsigned int rates, unsigned int basic, bool short_pre, bool rsn, u64 d)
{
	(void)h; (void)seq; (void)ap; (void)rates; (void)basic; (void)short_pre;
	assert(bytes == 3 && !memcmp(ssid, "lab", 3) && rsn); return pm_record(0x12, d);
}
static int mt6797_hif_join_station(void *h, unsigned int seq, const u8 *ap, unsigned int state,
		unsigned int aid, unsigned int rates, unsigned int basic, u64 d)
{
	(void)h; (void)seq; (void)ap; (void)rates; (void)basic;
	assert(state == 3 && aid == 6);
	current->join_sta_pending = false; current->join_sta_active = true;
	complete_all(&current->join_sta_done); return pm_record(0x13, d);
}
static int mt6797_hif_join_pm_connected(void *h, unsigned int seq, unsigned int dtim,
		unsigned int aid, unsigned int interval, u64 d)
{
	(void)h; (void)seq; assert(dtim == 3 && aid == 6 && interval == 100);
	assert(!key_submits && !current->join_key_pairwise_submitted && !current->join_key_group_submitted);
	return pm_record(0x16, d);
}
static int mt6797_hif_join_pm_abort(void *h, unsigned int seq, u64 d)
{
	(void)h; (void)seq; assert(!current->ccmp_pm_abort_credited); return pm_record(0x17, d);
}
static int pm_remove_key(bool pairwise) { return pm_record(pairwise ? 0x71 : 0x72, current->join_credit_deadline); }
static int mt6797_hif_join_remove_station(void *h, unsigned int seq, u64 d)
{
	(void)h; (void)seq; return pm_record(0x14, d);
}
static int mt6797_hif_join_channel(void *h, unsigned int seq, u8 token, u8 ch,
		unsigned int ms, bool abort, u64 d)
{
	(void)h; (void)seq; (void)token; assert(ch == 40 && !ms && abort); return pm_record(0x1c, d);
}
static int mt6797_hif_send_config(void *h, enum mt6797_normal_config_kind kind,
		unsigned int seq, const u8 *payload, size_t bytes, u64 d)
{
	(void)h; (void)seq; (void)payload; assert(kind == MT6797_NORMAL_BSS_ACTIVE && bytes == 12);
	return pm_record(0x0a, d);
}
static void ieee80211_connection_loss(struct ieee80211_vif *v)
{
	assert(v == current->vif); pm_losses++;
}
static bool pm_credit_hook(struct mt6797_mac *m, int *rc)
{
	if (!pm_mode) return false;
	*rc = 0;
	if (pm_pending == 0x16) {
		if (pm_credit_edge) now = m->join_credit_deadline + pm_credit_edge - 2;
		if (pm_credit_error) { *rc = pm_credit_error; return true; }
	}
	m->join_page_debt = 0; m->join_credit_pending = false;
	return true;
}
static bool pm_wait_hook(struct mt6797_mac *m, struct completion *c, unsigned long ticks)
{
	struct sk_buff_head q;
	u8 *f = m->join_packet + 16;
	(void)ticks;
	if (!pm_mode || c != &m->ccmp_dtim_done) return false;
	if (pm_metadata == 1) { now += 750 * NSEC_PER_MSEC; return true; }
	if (pm_metadata == 2) { mt6797_ccmp_withdraw(m); return true; }
	memset(m->join_packet, 0, sizeof(m->join_packet));
	f[0] = 0x80; f[32] = 100; f[36] = 0; f[37] = 3; memcpy(f + 38, "lab", 3);
	f[41] = 5; f[42] = 4; f[44] = pm_metadata == 3 ? 0 : 3;
	skb_queue_head_init(&q);
	assert(!mt6797_mac_join_deliver_beacon(m, 16, 47, 100, false, &q));
	dev_kfree_skb(__skb_dequeue(&q));
	return true;
}
static void pm_prepare(struct mt6797_mac *m, struct ieee80211_hw *hw,
		struct ieee80211_vif *v, struct ieee80211_sta *s)
{
	prepare(m, hw, v, s); pm_mode = true; m->ccmp_pm_connected = false;
	m->join_bss_configured = m->join_sta_active = false;
	m->join_bss_valid = m->join_assoc_received = true;
	m->join_aid = 6; m->join_beacon_interval = 100; m->join_ssid_bytes = 3;
	memcpy(m->join_ssid, "lab", 3); m->sequence = 23;
	m->started = true; m->native_diag_state = MT6797_ND_IDLE;
}
static int pm_associate(struct mt6797_mac *m)
{
	int ret; mutex_lock(&m->mutex); ret = mt6797_mac_join_associate(m, 6);
	mutex_unlock(&m->mutex); return ret;
}
static void pm_callback_tests(void)
{
	struct mt6797_mac m;
	struct wiphy w = {{2, 0, 0, 0, 0, 1}};
	struct ieee80211_hw hw = {NULL, &w};
	struct ieee80211_vif v = {0};
	struct ieee80211_sta s = {{2, 0, 0, 0, 0, 2}, false, 0};
	/* No seed or key command may precede credited PM setup. */
	struct ieee80211_key_conf key = {IEEE80211_KEY_FLAG_PAIRWISE, WLAN_CIPHER_SUITE_CCMP, 0, 16, {0}, 0};
	pm_prepare(&m, &hw, &v, &s); wait_mode = OWNED_FIRST;
	assert(mt6797_mac_set_key(&hw, SET_KEY, &v, &s, &key) < 0);
	assert(!seed_calls && !key_submits && !m.join_key_pairwise_submitted); destroy(&m);
	/* Real association blocks for metadata, then credits 0x16 before any key. */
	pm_prepare(&m, &hw, &v, &s); assert(!pm_associate(&m));
	assert(pm_count == 3 && pm_ops[0] == 0x12 && pm_ops[1] == 0x13 && pm_ops[2] == 0x16);
	assert(m.ccmp_pm_connected && m.ccmp_dtim_valid && m.ccmp_dtim_period == 3 && !key_submits);
	destroy(&m);
	for (int mode = 1; mode <= 3; mode++) {
		pm_prepare(&m, &hw, &v, &s); pm_metadata = mode;
		assert(pm_associate(&m) < 0); assert(pm_count == 2 && !key_submits && !m.ccmp_pm_connected);
		destroy(&m);
	}
	/* Credit must arrive strictly before its unchanged command deadline. */
	for (int edge = 1; edge <= 3; edge++) {
		pm_prepare(&m, &hw, &v, &s); pm_credit_edge = edge;
		assert(pm_associate(&m) == (edge == 1 ? 0 : -ETIMEDOUT));
		assert(m.ccmp_pm_connected == (edge == 1) && !key_submits); destroy(&m);
	}
	pm_prepare(&m, &hw, &v, &s); pm_credit_error = -ETIMEDOUT;
	assert(pm_associate(&m) == -ETIMEDOUT && !m.ccmp_pm_connected && !key_submits); destroy(&m);
	/* Isolated admission failures submit no PM command and no key. */
	for (int mode = 0; mode < 4; mode++) {
		pm_prepare(&m, &hw, &v, &s); m.ccmp_dtim_valid = true; m.ccmp_dtim_period = 3;
		m.join_bss_configured = m.join_sta_active = true;
		if (mode == 0) pm_idle = false;
		if (mode == 1) m.sequence = 254;
		if (mode == 2) m.join_credit_pending = true;
		if (mode == 3) pm_wire_error = -EIO;
		mutex_lock(&m.mutex); assert(mt6797_ccmp_pm_indicate(&m, now + 750 * NSEC_PER_MSEC) < 0); mutex_unlock(&m.mutex);
		assert(pm_count == (mode == 3 ? 1U : 0U) && !m.ccmp_pm_connected && !key_submits); destroy(&m);
	}
	/* Actual cleanup cannot remove anything before PM abort credit. */
	pm_prepare(&m, &hw, &v, &s); assert(!pm_associate(&m)); pm_count = 0;
	m.join_cleanup_requested = m.join_deauth_done = true; m.native_diag_state = MT6797_ND_CLOSED;
	m.join_key_pairwise = m.join_key_group = 1; m.join_group_key_id = 1;
	mutex_lock(&m.mutex);
	assert(!mt6797_mac_join_cleanup_step(&m) && pm_count == 1 && pm_ops[0] == 0x17);
	assert(!mt6797_mac_join_cleanup_step(&m) && pm_count == 1 && !m.ccmp_pm_abort_credited);
	for (unsigned int i = 0; i < 6; i++) {
		m.join_page_debt = 0; m.join_credit_pending = false;
		assert(!mt6797_mac_join_cleanup_step(&m));
	}
	assert(pm_count == 6 && pm_ops[1] == 0x71 && pm_ops[2] == 0x72 && pm_ops[3] == 0x14 && pm_ops[4] == 0x1c && pm_ops[5] == 0x0a);
	assert(m.ccmp_pm_abort_credited && !m.ccmp_pm_connected && m.join_cleanup_done && m.join_retired);
	assert(pm_losses == 1); mutex_unlock(&m.mutex); destroy(&m);

#ifdef FIXTURE_CONNECTION_MONITOR
	/* Fatal live data reports loss once; pre-key stops do not report a link. */
	pm_prepare(&m, &hw, &v, &s); m.join_data_phase = true;
	struct sk_buff_head discard; struct sk_buff *internal = NULL; skb_queue_head_init(&discard);
	mutex_lock(&m.mutex); assert(mt6797_mac_join_fail_stop(&m, -EPROTO, 6, &discard, &internal) == -EPROTO);
	assert(pm_losses == 1); mt6797_ccmp_connection_lost(&m, "fixture"); assert(pm_losses == 1);
	mutex_unlock(&m.mutex); destroy(&m);
	pm_prepare(&m, &hw, &v, &s); mutex_lock(&m.mutex);
	assert(mt6797_mac_join_fail_stop(&m, -EPROTO, 6, &discard, &internal) == -EPROTO && !pm_losses);
	mutex_unlock(&m.mutex); destroy(&m);
#endif
	pm_mode = false;
	puts("PM actual MAC: PASS pre-key association/metadata/credit, +/-1ns boundary, abort-before-removal, single standard loss report");
}
