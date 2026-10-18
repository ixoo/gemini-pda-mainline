/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual full dispatcher and handler; all command reads are counted stubs. */
static void handler_ready(struct mt6797_mac *m, struct ieee80211_hw *hw,
			  struct ieee80211_sta *sta,
			  struct ieee80211_key_conf *ptk, struct ieee80211_key_conf *gtk)
{
	memset(m, 0, sizeof(*m)); m->hw = hw;
	m->ccmp_rx.active = m->ccmp_rx.authorized = m->ccmp_decap = true;
	m->ccmp_gtk_rx.active = m->ccmp_gtk_rx.authorized = true;
	m->ccmp_sta = sta; m->ccmp_ptk = ptk; m->ccmp_gtk = gtk;
	m->join_bss_valid = m->join_bss_configured = m->join_sta_active = true;
	m->join_beacon_interval = 100; m->join_key_pairwise = m->join_key_group = 1;
	m->join_data_phase = true; m->native_diag_state = MT6797_ND_ACTIVE;
	m->join_data_deadline = now + 50000ULL * NSEC_PER_MSEC;
	m->join_grant_deadline = m->join_data_deadline + 3000ULL * NSEC_PER_MSEC;
	m->ccmp_queued = 149; m->join_beacons_delivered = 293;
	m->ccmp_last_checked_rx = now - 287ULL * NSEC_PER_MSEC;
	m->ccmp_last_beacon_rx = now - 71ULL * NSEC_PER_MSEC;
	m->join_packet[0] = 12; m->join_packet[3] = 0xe0; m->join_packet[4] = 0x13;
	m->join_packet[9] = 6;
}

static void handler_assert(struct mt6797_mac *m, bool accepted)
{
	struct mt6797_mac expected = *m;
	unsigned int reads = handler_reads;

	if (accepted) expected.ccmp_timeout_continued++;
	assert(mt6797_mac_join_control_event(m, 12) == (accepted ? 0 : -EPROTO));
	assert(!memcmp(m, &expected, sizeof(*m)) && handler_reads == reads);
}

static void timeout_handler_tests(void)
{
	struct mt6797_mac m;
	struct wiphy w = {{2, 0, 0, 0, 0, 1}};
	struct ieee80211_hw hw = {&m, &w};
	struct ieee80211_sta sta = {{2, 0, 0, 0, 0, 2}, false, 0};
	struct ieee80211_key_conf ptk = {0}, gtk = {0};

	now = 10000ULL * NSEC_PER_MSEC;
#define READY() handler_ready(&m, &hw, &sta, &ptk, &gtk)
	/* Numeric reasons do not define policy; only exact current-state freshness. */
	for (unsigned int reason = 0; reason < 256; reason++) {
		READY(); m.join_packet[9] = reason; handler_assert(&m, true);
	}
	for (int delta = -1; delta <= 1; delta++) {
		READY(); m.ccmp_last_beacon_rx = now - (2ULL * 100 * 1024 * NSEC_PER_USEC + delta);
		handler_assert(&m, delta < 0);
		READY(); m.ccmp_last_checked_rx = now - (2000ULL * NSEC_PER_MSEC + delta);
		handler_assert(&m, true);
	}
	/* The interval is TU and is current committed metadata, not a guessed 200 ms. */
	READY(); m.ccmp_last_beacon_rx = now - 202ULL * NSEC_PER_MSEC; handler_assert(&m, true);
	READY(); m.ccmp_last_checked_rx = now - 9000ULL * NSEC_PER_MSEC; handler_assert(&m, true);
	READY(); m.join_beacon_interval = 0; handler_assert(&m, false);
	READY(); m.join_beacon_interval = 1; m.ccmp_last_beacon_rx = now - 3ULL * NSEC_PER_MSEC; handler_assert(&m, false);
	READY(); m.ccmp_last_checked_rx = now + 1; handler_assert(&m, true);
	READY(); m.ccmp_last_beacon_rx = now + 1; handler_assert(&m, false);
	READY(); m.ccmp_queued = 0; handler_assert(&m, true);
	READY(); m.join_beacons_delivered = 0; handler_assert(&m, false);
	READY(); m.join_packet[8] = 1; handler_assert(&m, false);
	READY(); m.join_packet[5] = 1; handler_assert(&m, false);
	READY(); m.join_packet[4] = 0x18; handler_assert(&m, false);
#define REJECT(field, value) do { READY(); m.field = (value); handler_assert(&m, false); } while (0)
	REJECT(ccmp_closed, true); REJECT(ccmp_rx.active, false); REJECT(ccmp_rx.authorized, false);
	REJECT(ccmp_decap, false); REJECT(ccmp_sta, NULL); REJECT(ccmp_ptk, NULL); REJECT(ccmp_gtk, NULL);
	REJECT(ccmp_gtk_rx.active, false); REJECT(ccmp_gtk_rx.authorized, false);
	REJECT(closing, true); REJECT(first_error, -EIO); REJECT(join_retired, true);
	REJECT(join_data_phase, false); REJECT(join_data_ended, true); REJECT(native_diag_state, MT6797_ND_CLOSED);
	REJECT(join_bss_valid, false); REJECT(join_bss_configured, false); REJECT(join_sta_active, false);
	REJECT(join_key_pairwise, 2); REJECT(join_key_group, 2); REJECT(join_cleanup_stage, 1);
	REJECT(native_diag_sample_done, true); REJECT(join_data_deadline, now); REJECT(join_grant_deadline, now);
#undef REJECT
	for (unsigned int n = 0; n <= 32; n++) {
		if (n == 12) continue;
		READY(); m.join_packet[0] = n;
		assert(mt6797_mac_join_control_event(&m, n) == -EPROTO && !m.ccmp_timeout_continued);
	}
	READY(); ccmp_stable_epoch = false; handler_assert(&m, false); ccmp_stable_epoch = true;
#undef READY
	puts("conditional BSS timeout: PASS exact dispatcher, all reason bytes, ns boundaries/TU, owned/current keys/state/clocks, no wire or ledger transitions");
}
