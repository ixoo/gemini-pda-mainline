/* SPDX-License-Identifier: GPL-2.0-only */
/* Added cases run after the existing actual-source pthread callback fixture. */
#include <sanitizer/asan_interface.h>

static int mt6797_hif_diag_mask(void *hif, unsigned int seq, bool enable, u64 deadline)
{
	/* Control-call model only. The unchanged actual HIF is source-pinned. */
	return mt6797_hif_native_monitor(hif, seq, enable, 40, deadline);
}

static void gtk_callback_tests(void)
{
	struct mt6797_mac m = {0};
	struct wiphy w = {{2, 0, 0, 0, 0, 1}};
	struct ieee80211_hw hw = {&m, &w};
	struct ieee80211_vif vif = {0};
	struct ieee80211_sta sta = {{2, 0, 0, 0, 0, 2}, false, 0};
	struct ieee80211_key_conf ptk = {IEEE80211_KEY_FLAG_PAIRWISE, WLAN_CIPHER_SUITE_CCMP, 0, 16, {0}, 0};
	struct ieee80211_key_conf gtk = {0, WLAN_CIPHER_SUITE_CCMP, 1, 16, {0}, 0};
	struct sk_buff_head q;
	struct mt6797_ccmp_rx_context old_ptk, old_gtk;
	struct sk_buff *queued;
	u8 packet[512];
	size_t n;
	unsigned int count, seeds, submitted, received_before;

	prepare(&m, &hw, &vif, &sta); wait_mode = OWNED_FIRST;
	assert(!mt6797_mac_set_key(&hw, SET_KEY, &vif, &sta, &ptk));
	assert(!mt6797_mac_set_key(&hw, SET_KEY, &vif, NULL, &gtk));
	assert(m.ccmp_gtk_attempted && m.ccmp_gtk_rx.seeded && m.ccmp_gtk_rx.active);
	assert(!m.ccmp_gtk_rx.authorized && !m.ccmp_gtk_rx.pairwise);
	assert(m.ccmp_rx.pn[5] == 5 && m.ccmp_gtk_rx.pn[5] == 50 && seed_calls == 2);
	assert(!mt6797_mac_sta_state(&hw, &vif, &sta, IEEE80211_STA_ASSOC, IEEE80211_STA_AUTHORIZED));
	mt6797_mac_sta_set_decap_offload(&hw, &vif, &sta, true);
	assert(m.ccmp_gtk_rx.authorized && mt6797_ccmp_rx_ready(&m));
	m.native_diag_engaged = true; m.native_diag_started = now;
	skb_queue_head_init(&q);

	/* One clean initial GTK ARP: exact queue/flags, separate PN commit. */
	n = frame(packet, 9, false, 51);
	packet[4] = 0x48; packet[8] = 2; memset(packet + 48, 255, 6);
	packet[60] = 8; packet[61] = 6;
	memcpy(m.join_packet, packet, n); old_ptk = m.ccmp_rx;
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && q.head && !q.head->next);
	assert(!memcmp(&old_ptk, &m.ccmp_rx, sizeof(old_ptk)));
	assert(m.ccmp_gtk_rx.pn[5] == 51 && m.ccmp_queued == 1 && m.ccmp_gtk_seen);
	assert(q.head->len == n - 48 && !memcmp(q.head->data, packet + 48, n - 48));
	assert(q.head->status.flag == (RX_FLAG_8023 | RX_FLAG_DECRYPTED | RX_FLAG_IV_STRIPPED |
	       RX_FLAG_MIC_STRIPPED | RX_FLAG_PN_VALIDATED | RX_FLAG_NO_SIGNAL_VAL));
	dev_kfree_skb(__skb_dequeue(&q));

	/* Replayed ARP is withheld; the counter itself never reads G1 PN. */
	old_gtk = m.ccmp_gtk_rx;
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && !q.head && m.ccmp_gtk_arp_withheld == 1);
	assert(!memcmp(&old_gtk, &m.ccmp_gtk_rx, sizeof(old_gtk)));
	__asan_poison_memory_region(m.join_packet + 32, 16);
	mt6797_ccmp_withheld_arp(&m, n);
	__asan_unpoison_memory_region(m.join_packet + 32, 16);
	assert(m.ccmp_gtk_arp_withheld == 2);
	n = frame(packet, 8, false, 51); packet[4] = 0x48; packet[8] = 2;
	memset(packet + 32, 255, 6); packet[44] = 8; packet[45] = 6;
	memcpy(m.join_packet, packet, n);
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && !q.head && m.ccmp_gtk_arp_withheld == 3);
	assert(!memcmp(&old_gtk, &m.ccmp_gtk_rx, sizeof(old_gtk)));

	/* PTK PN 6 remains valid after GTK PN 51. */
	n = frame(packet, 9, false, 6); memcpy(m.join_packet, packet, n);
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && q.head && m.ccmp_queued == 2);
	assert(m.ccmp_rx.pn[5] == 6 && m.ccmp_gtk_rx.pn[5] == 51);
	dev_kfree_skb(__skb_dequeue(&q));

	n = frame(packet, 9, false, 52); packet[4] = 0x48; packet[8] = 2;
	memset(packet + 48, 255, 6); packet[60] = 8; packet[61] = 6;
	memcpy(m.join_packet, packet, n);
	old_gtk = m.ccmp_gtk_rx; fail_alloc = true;
	assert(mt6797_ccmp_queue_rx(&m, n, &q) == -ENOMEM && !q.head);
	assert(!memcmp(&old_gtk, &m.ccmp_gtk_rx, sizeof(old_gtk))); fail_alloc = false;
	m.ccmp_queued = 64;
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && !q.head);
	assert(!memcmp(&old_gtk, &m.ccmp_gtk_rx, sizeof(old_gtk))); m.ccmp_queued = 2;

	/* Queue a GTK frame, then revoke the epoch before actual core handoff. */
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && q.head);
	queued = __skb_dequeue(&q); count = m.ccmp_gtk_arp_withheld;
	mutex_lock(&m.mutex); mt6797_ccmp_withdraw(&m); mutex_unlock(&m.mutex);
	assert(!m.ccmp_gtk_rx.active && !m.ccmp_gtk_rx.authorized && !m.ccmp_gtk);
	received_before = received;
	mutex_lock(&m.ccmp_receive_mutex); mt6797_ccmp_receive(&m, queued); mutex_unlock(&m.ccmp_receive_mutex);
	assert(received == received_before);
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && !q.head && m.ccmp_gtk_arp_withheld == count);
	seeds = seed_calls; submitted = key_submits;
	assert(mt6797_mac_set_key(&hw, SET_KEY, &vif, NULL, &gtk) == -EOPNOTSUPP);
	assert(seed_calls == seeds && key_submits == submitted);
	destroy(&m);
	/* Neither rejected command credit nor a withdrawal during seed collection
	 * may publish a GTK context or let that key be retried.
	 */
	for (unsigned int failure = 0; failure < 5; failure++) {
		prepare(&m, &hw, &vif, &sta); wait_mode = OWNED_FIRST;
		assert(!mt6797_mac_set_key(&hw, SET_KEY, &vif, &sta, &ptk));
		gtk.hw_key_idx = 0;
		if (failure == 0) submit_error = -EPROTO;
		if (failure == 1) credit_error = -EPROTO;
		if (failure == 2) withdraw_at_gtk_seed = true;
		if (failure == 3) withdraw_on_credit = true;
		if (failure == 4) {
			m.join_deadline = now + 10000 * NSEC_PER_MSEC;
			expire_on_credit = true;
		}
		assert(mt6797_mac_set_key(&hw, SET_KEY, &vif, NULL, &gtk) < 0);
		assert(m.ccmp_closed && m.ccmp_gtk_attempted && !m.ccmp_gtk);
		assert(!m.ccmp_gtk_rx.active && !m.ccmp_gtk_rx.seeded && !gtk.hw_key_idx);
		assert(seed_calls == 2 && key_submits == (failure == 2 ? 1U : 2U));
		seeds = seed_calls; submitted = key_submits;
		assert(mt6797_mac_set_key(&hw, SET_KEY, &vif, NULL, &gtk) < 0);
		assert(seed_calls == seeds && key_submits == submitted);
		destroy(&m);
	}
	puts("GTK actual callbacks: PASS distinct seed/PN/auth/flags, PN-free ARP counter, allocation/cap, stale queued RX, command/credit/withdrawal/setup-expiry failures and no reinstall");
}

int main(void)
{
	assert(existing_callbacks() == 0);
	gtk_callback_tests();
	return 0;
}
