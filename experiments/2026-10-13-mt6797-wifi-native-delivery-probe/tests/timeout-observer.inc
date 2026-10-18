/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual acquisition observer: no radio, event admission or firmware model. */
static void timeout_event(struct mt6797_mac *m, unsigned int bss, unsigned int reason)
{
	memset(m->join_packet, 0, sizeof(m->join_packet));
	m->join_packet[0] = 12; m->join_packet[3] = 0xe0;
	m->join_packet[4] = 0x13;
	m->join_packet[8] = bss; m->join_packet[9] = reason;
}

static void timeout_observer_tests(void)
{
	struct mt6797_mac m = {0}, before;
	struct wiphy w = {{2, 0, 0, 0, 0, 1}};
	struct ieee80211_hw hw = {&m, &w};
	struct ieee80211_vif vif = {0};
	struct ieee80211_sta sta = {{2, 0, 0, 0, 0, 2}, false, 0};
	struct ieee80211_key_conf ptk = {IEEE80211_KEY_FLAG_PAIRWISE, WLAN_CIPHER_SUITE_CCMP, 0, 16, {0}, 0};
	struct ieee80211_key_conf gtk = {0, WLAN_CIPHER_SUITE_CCMP, 1, 16, {0}, 0};
	struct sk_buff_head q;
	unsigned char packet[512];
	size_t n;
	char expected[256];

	m.hw = &hw; now = 10000ULL * NSEC_PER_MSEC;
	/* Every BSS/reason byte is observed as metadata, never accepted/normalized. */
	for (unsigned int bss = 0; bss < 256; bss++) {
		for (unsigned int reason = 0; reason < 256; reason++) {
			timeout_event(&m, bss, reason); before = m;
			mt6797_ccmp_timeout_observe(&m, 12);
			snprintf(expected, sizeof(expected), "bss=%u reason=%u checked_rx_known=0 checked_rx_age_ms=0", bss, reason);
			assert(strstr(last_log, expected) && !memcmp(&m, &before, sizeof(m)));
		}
	}
	/* Length/type/id/sequence gates read no body for an inexact acquisition. */
	for (unsigned int nbytes = 0; nbytes <= 64; nbytes++) {
		if (nbytes == 12) continue;
		timeout_event(&m, 0, 8); m.join_packet[0] = nbytes;
		strcpy(last_log, "untouched"); mt6797_ccmp_timeout_observe(&m, nbytes);
		assert(!strcmp(last_log, "untouched"));
	}
	for (unsigned int offset = 0; offset <= 5; offset++) {
		timeout_event(&m, 0, 8); m.join_packet[offset] ^= 1;
		strcpy(last_log, "untouched"); mt6797_ccmp_timeout_observe(&m, 12);
		assert(!strcmp(last_log, "untouched"));
	}
	timeout_event(&m, 0, 8); m.join_packet[10] = 255; m.join_packet[11] = 255;
	m.ccmp_queued = 1;
	for (int delta = -1; delta <= 1; delta++) {
		m.ccmp_last_checked_rx = now - (2000ULL * NSEC_PER_MSEC + delta);
		mt6797_ccmp_timeout_observe(&m, 12);
		snprintf(expected, sizeof(expected), "checked_rx_known=1 checked_rx_age_ms=%u", delta < 0 ? 1999 : 2000);
		assert(strstr(last_log, expected));
	}
	m.ccmp_last_checked_rx = now + 1;
	mt6797_ccmp_timeout_observe(&m, 12);
	assert(strstr(last_log, "checked_rx_known=0 checked_rx_age_ms=0"));
	ccmp_stable_epoch = false; strcpy(last_log, "untouched");
	mt6797_ccmp_timeout_observe(&m, 12); assert(!strcmp(last_log, "untouched"));
	ccmp_stable_epoch = true;

	/* Only successful strict PTK/GTK checks move the queue-admission clock. */
	prepare(&m, &hw, &vif, &sta); wait_mode = OWNED_FIRST;
	assert(!mt6797_mac_set_key(&hw, SET_KEY, &vif, &sta, &ptk));
	assert(!mt6797_mac_set_key(&hw, SET_KEY, &vif, NULL, &gtk));
	assert(!mt6797_mac_sta_state(&hw, &vif, &sta, IEEE80211_STA_ASSOC, IEEE80211_STA_AUTHORIZED));
	mt6797_mac_sta_set_decap_offload(&hw, &vif, &sta, true);
	m.native_diag_engaged = true; m.native_diag_started = now;
	skb_queue_head_init(&q); n = frame(packet, 9, false, 6);
	memcpy(m.join_packet, packet, n); now += 100;
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && q.head && m.ccmp_last_checked_rx == now);
	dev_kfree_skb(__skb_dequeue(&q)); before = m; now += 100;
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && !q.head && m.ccmp_last_checked_rx == before.ccmp_last_checked_rx);
	n = frame(packet, 9, false, 51); packet[4] = 0x48; packet[8] = 2;
	memset(packet + 48, 255, 6); memcpy(m.join_packet, packet, n);
	fail_alloc = true; assert(mt6797_ccmp_queue_rx(&m, n, &q) == -ENOMEM);
	fail_alloc = false; assert(m.ccmp_last_checked_rx == before.ccmp_last_checked_rx);
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && q.head && m.ccmp_last_checked_rx == now);
	dev_kfree_skb(__skb_dequeue(&q)); before = m; m.ccmp_closed = true; now++;
	assert(!mt6797_ccmp_queue_rx(&m, n, &q) && !q.head && m.ccmp_last_checked_rx == before.ccmp_last_checked_rx);
	puts("timeout observer: PASS exact body scalars, no state changes, malformed/disabled silence, age bounds and strict queue clock");
}
