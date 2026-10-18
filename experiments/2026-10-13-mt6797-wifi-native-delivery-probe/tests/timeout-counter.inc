/* SPDX-License-Identifier: GPL-2.0-only */
/* No reason interpretation, tolerance, wire read or resource mutation. */
static void timeout_event(struct mt6797_mac *, unsigned int, unsigned int);
static void timeout_counter_tests(void)
{
	struct mt6797_mac m = {0}, expected;
	struct wiphy w = {{2, 0, 0, 0, 0, 1}};
	struct ieee80211_hw hw = {&m, &w};
	m.hw = &hw; now = 10000ULL * NSEC_PER_MSEC;
	m.join_beacons_delivered = 293; m.ccmp_last_beacon_rx = now - 71 * NSEC_PER_MSEC;
	m.join_beacon_interval = 100;
	for (unsigned int reason = 0; reason <= 255; reason++) {
		timeout_event(&m, 0, reason); expected = m; expected.ccmp_timeout_observed++;
		mt6797_ccmp_timeout_observe(&m, 12);
		assert(!memcmp(&m, &expected, sizeof(m)));
		assert(mt6797_mac_join_control_event(&m, 12) == -EPROTO);
		assert(!memcmp(&m, &expected, sizeof(m)) && !handler_reads);
	}
	timeout_event(&m, 1, 0); expected = m;
	mt6797_ccmp_timeout_observe(&m, 12); assert(!memcmp(&m, &expected, sizeof(m)));
	puts("owned timeout counter: PASS all reasons still fatal, owned counter only, fresh beacons do not tolerate event, no wire/credit/key change");
}
