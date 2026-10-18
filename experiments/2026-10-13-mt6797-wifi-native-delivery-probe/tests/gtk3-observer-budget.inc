/* SPDX-License-Identifier: GPL-2.0-only */
/* Extend the actual GTK queue/handoff and actual engine fixtures. Host only. */
static int gtk3_pre_read(struct mt6797_mac *m, unsigned int total,
			 unsigned int checked, unsigned int bytes, unsigned int native)
{
	m->native_diag_state = MT6797_ND_ACTIVE;
	m->native_diag_sample_done = false; m->join_data_ended = false;
	m->native_diag_total = total; m->ccmp_queued = checked;
	m->native_diag_bytes = bytes; m->native_diag_native = native;
	m->join_inflight = NULL; m->join_page_debt = 0; m->join_credit_pending = false;
	return mt6797_native_diag_pre_read(m);
}

static void gtk3_observer_budget_tests(void)
{
	struct mt6797_mac m = {0};
	struct wiphy w = {{2, 0, 0, 0, 0, 1}};
	struct ieee80211_hw hw = {&m, &w};
	struct ieee80211_vif vif = {0};
	struct ieee80211_sta sta = {{2, 0, 0, 0, 0, 2}, false, 0};
	struct ieee80211_key_conf ptk = {IEEE80211_KEY_FLAG_PAIRWISE, WLAN_CIPHER_SUITE_CCMP, 0, 16, {0}, 0};
	struct ieee80211_key_conf gtk = {0, WLAN_CIPHER_SUITE_CCMP, 1, 16, {0}, 0};
	struct sk_buff_head q;
	struct mt6797_hif_rx_result rx = {0};
	unsigned char packet[512];
	size_t n;
	unsigned int old_received;

	prepare(&m, &hw, &vif, &sta); wait_mode = OWNED_FIRST;
	assert(!mt6797_mac_set_key(&hw, SET_KEY, &vif, &sta, &ptk));
	assert(!mt6797_mac_set_key(&hw, SET_KEY, &vif, NULL, &gtk));
	assert(!mt6797_mac_sta_state(&hw, &vif, &sta, IEEE80211_STA_ASSOC, IEEE80211_STA_AUTHORIZED));
	mt6797_mac_sta_set_decap_offload(&hw, &vif, &sta, true);
	m.native_diag_engaged = true; m.native_diag_started = now;
	skb_queue_head_init(&q);

	/* Queue admission alone is not counted as an ARP handoff. */
	n = frame(packet, 9, false, 51); packet[4] = 0x48; packet[8] = 2;
	memset(packet + 48, 255, 6); packet[60] = 8; packet[61] = 6;
	memcpy(m.join_packet, packet, n);
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && q.head);
	assert(m.ccmp_queued == 1 && m.ccmp_gtk_queued == 1 && !m.ccmp_gtk_arp_handoff);
	old_received = received;
	mutex_lock(&m.ccmp_receive_mutex); mt6797_ccmp_receive(&m, __skb_dequeue(&q)); mutex_unlock(&m.ccmp_receive_mutex);
	assert(received == old_received + 1 && m.ccmp_gtk_arp_handoff == 1);
	/* Replayed GTK ARP is withheld, with no new queue/handoff evidence. */
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && !q.head && m.ccmp_gtk_arp_withheld == 1);
	assert(m.ccmp_queued == 1 && m.ccmp_gtk_queued == 1 && m.ccmp_gtk_arp_handoff == 1);

	/* An ARP carried by PTK does not count as GTK ARP. */
	n = frame(packet, 9, false, 6); packet[60] = 8; packet[61] = 6;
	memcpy(m.join_packet, packet, n);
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && q.head);
	assert(m.ccmp_queued - m.ccmp_gtk_queued == 1);
	mutex_lock(&m.ccmp_receive_mutex); mt6797_ccmp_receive(&m, __skb_dequeue(&q)); mutex_unlock(&m.ccmp_receive_mutex);
	assert(m.ccmp_gtk_arp_handoff == 1);
	/* GTK non-ARP reaches the same core handoff without inflating ARP. */
	n = frame(packet, 9, false, 52); packet[4] = 0x48; packet[8] = 2;
	memset(packet + 48, 255, 6); memcpy(m.join_packet, packet, n);
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && q.head && m.ccmp_gtk_queued == 2);
	mutex_lock(&m.ccmp_receive_mutex); mt6797_ccmp_receive(&m, __skb_dequeue(&q)); mutex_unlock(&m.ccmp_receive_mutex);
	assert(m.ccmp_gtk_arp_handoff == 1);

	/* All four binding sites must use CCMP capacity, not the native 512/64:
	 * engine transition, pre-read, post-read dispatch and queue admission.
	 */
	m.join_deadline = m.join_data_deadline = now + 120000 * NSEC_PER_MSEC;
	assert(!gtk3_pre_read(&m, 512, 64, 1024 * 1024, 0));
	mt6797_native_diag_step(&m); assert(m.native_diag_state == MT6797_ND_ACTIVE);
	assert(!gtk3_pre_read(&m, 4095, 1023, 0, 0));
	assert(gtk3_pre_read(&m, 4096, 1023, 0, 0) == 1);
	assert(gtk3_pre_read(&m, 4095, 1024, 0, 0) == 1);
	assert(!gtk3_pre_read(&m, 0, 0, 2 * 1024 * 1024 - MT6797_HIF_RX_MAX_PACKET, 0));
	assert(gtk3_pre_read(&m, 0, 0, 2 * 1024 * 1024 - MT6797_HIF_RX_MAX_PACKET + 1, 0) == 1);
	assert(gtk3_pre_read(&m, 0, 0, 0, 64) == 1); /* native ceiling unchanged */
	assert(!gtk3_pre_read(&m, 0, 3, 0, 0));
	rx.logical_bytes = frame(packet, 9, false, 7); rx.packet_type = mt6797_join_le16(packet + 2);
	memcpy(m.join_packet, packet, rx.logical_bytes); m.native_diag_total = 511;
	assert(!dispatch(&m, &rx, &q) && q.head && m.native_diag_total == 512);
	dev_kfree_skb(__skb_dequeue(&q));
	/* Crossing the actual new all-RX threshold still withholds the frame. */
	rx.logical_bytes = frame(packet, 9, false, 8); memcpy(m.join_packet, packet, rx.logical_bytes);
	m.native_diag_total = 4095; old_received = m.ccmp_queued;
	assert(!dispatch(&m, &rx, &q) && !q.head && m.native_diag_total == 4096);
	assert(m.ccmp_queued == old_received && m.ccmp_rx.pn[5] == 7);

	ccmp_stable_epoch = false;
	assert(!gtk3_pre_read(&m, 511, 0, 0, 63));
	assert(gtk3_pre_read(&m, 512, 0, 0, 63) == 1);
	assert(gtk3_pre_read(&m, 0, 0, 0, 64) == 1);
	assert(!gtk3_pre_read(&m, 0, 0, 1024 * 1024 - MT6797_HIF_RX_MAX_PACKET, 0));
	assert(gtk3_pre_read(&m, 0, 0, 1024 * 1024 - MT6797_HIF_RX_MAX_PACKET + 1, 0) == 1);
	ccmp_stable_epoch = true;
	m.ccmp_queued = 4; /* Restore the four actual admissions after quota probes. */
	assert(!gtk3_pre_read(&m, 0, m.ccmp_queued, 0, 0));
	/* A queued GTK ARP revoked before handoff is not delivery evidence. */
	n = frame(packet, 9, false, 53); packet[4] = 0x48; packet[8] = 2;
	memset(packet + 48, 255, 6); packet[60] = 8; packet[61] = 6;
	memcpy(m.join_packet, packet, n);
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && q.head);
	old_received = received;
	mutex_lock(&m.mutex); mt6797_ccmp_withdraw(&m); mutex_unlock(&m.mutex);
	mutex_lock(&m.ccmp_receive_mutex); mt6797_ccmp_receive(&m, __skb_dequeue(&q)); mutex_unlock(&m.ccmp_receive_mutex);
	assert(received == old_received && m.ccmp_gtk_arp_handoff == 1);
	destroy(&m);
	puts("GTK3 actual callbacks: PASS queue split, ARP core handoff/replay/PTK/non-ARP/stale refusal, all four CCMP capacity gates, unchanged native bounds");
}
