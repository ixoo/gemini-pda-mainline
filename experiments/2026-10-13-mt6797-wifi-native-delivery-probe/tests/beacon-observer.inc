/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual successful queue helper; caller ownership/dispatch is source-compared. */
static void beacon_observer_tests(void)
{
	struct mt6797_mac m = {0}, before;
	struct wiphy w = {{2, 0, 0, 0, 0, 1}};
	struct ieee80211_hw hw = {&m, &w};
	struct sk_buff_head q;
	unsigned char *p = m.join_packet;

	m.hw = &hw; skb_queue_head_init(&q); now = 10000ULL * NSEC_PER_MSEC;
	/* Existing caller-qualified clear/keyed queue paths move the beacon clock. */
	assert(!mt6797_mac_join_deliver_beacon(&m, 16, 36, 100, false, &q));
	assert(q.head && m.join_beacons_delivered == 1 && !m.join_keyed_beacons && m.ccmp_last_beacon_rx == now);
	dev_kfree_skb(__skb_dequeue(&q)); now += 100 * NSEC_PER_MSEC;
	assert(!mt6797_mac_join_deliver_beacon(&m, 16, 36, 100, true, &q));
	assert(q.head && m.join_beacons_delivered == 2 && m.join_keyed_beacons == 1 && m.ccmp_last_beacon_rx == now);
	dev_kfree_skb(__skb_dequeue(&q)); before = m;
	fail_alloc = true; now += 100 * NSEC_PER_MSEC;
	assert(mt6797_mac_join_deliver_beacon(&m, 16, 36, 100, false, &q) == -ENOMEM);
	fail_alloc = false; assert(!q.head && m.ccmp_last_beacon_rx == before.ccmp_last_beacon_rx && m.join_beacons_delivered == 2);
	/* Checked-data idle/unknown stays separate from known recent owned beacons. */
	memset(p, 0, 12); p[0] = 12; p[3] = 0xe0; p[4] = 0x13; p[9] = 8;
	before = m; mt6797_ccmp_timeout_observe(&m, 12);
	assert(strstr(last_log, "checked_rx_known=0 checked_rx_age_ms=0 beacon_known=1 beacon_count=2 beacon_age_ms=100"));
	assert(!memcmp(&m, &before, sizeof(m)));
	/* Sub-ms boundary truncation, older gap, unknown and impossible future clock. */
	for (int delta = -1; delta <= 1; delta++) {
		char expected[128];
		m.ccmp_last_beacon_rx = now - (2000ULL * NSEC_PER_MSEC + delta);
		mt6797_ccmp_timeout_observe(&m, 12);
		snprintf(expected, sizeof(expected), "beacon_known=1 beacon_count=2 beacon_age_ms=%u", delta < 0 ? 1999 : 2000);
		assert(strstr(last_log, expected));
	}
	m.ccmp_last_beacon_rx = now - 5000ULL * NSEC_PER_MSEC;
	mt6797_ccmp_timeout_observe(&m, 12); assert(strstr(last_log, "beacon_age_ms=5000"));
	m.ccmp_last_beacon_rx = now + 1; mt6797_ccmp_timeout_observe(&m, 12);
	assert(strstr(last_log, "beacon_known=0 beacon_count=2 beacon_age_ms=0"));
	m.join_beacons_delivered = 0; m.ccmp_last_beacon_rx = 0; mt6797_ccmp_timeout_observe(&m, 12);
	assert(strstr(last_log, "beacon_known=0 beacon_count=0 beacon_age_ms=0"));
	/* The timeout/noise cannot refresh the clock it reports. */
	m.join_beacons_delivered = 2; m.ccmp_last_beacon_rx = now - 5000ULL * NSEC_PER_MSEC;
	p[5] = 1; strcpy(last_log, "untouched"); before = m;
	mt6797_ccmp_timeout_observe(&m, 12);
	assert(!strcmp(last_log, "untouched") && !memcmp(&m, &before, sizeof(m)));
	ccmp_stable_epoch = false;
	assert(!mt6797_mac_join_deliver_beacon(&m, 16, 36, 100, false, &q));
	assert(m.ccmp_last_beacon_rx == before.ccmp_last_beacon_rx);
	dev_kfree_skb(__skb_dequeue(&q)); ccmp_stable_epoch = true;
	puts("owned beacon observer: PASS existing count, successful queue clock, idle-data separation, ages/unknown/future, allocation and disabled mode");
}
