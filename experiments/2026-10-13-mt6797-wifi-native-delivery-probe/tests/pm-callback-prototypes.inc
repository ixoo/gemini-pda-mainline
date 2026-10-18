/* SPDX-License-Identifier: GPL-2.0-only */
/* Host ledger/command shims; actual MAC functions are extracted separately. */
struct mt6797_hif_ledger {
	unsigned int phase, tc4_free, tc4_limit, pending_cpu, pending_ffa;
	bool sequences, locked;
};
static void pm_reset_world(void);
static bool pm_credit_hook(struct mt6797_mac *, int *);
static bool pm_wait_hook(struct mt6797_mac *, struct completion *, unsigned long);
static int pm_remove_key(bool);
static int mt6797_mac_join_guard(struct mt6797_mac *, u64);
static bool mt6797_hif_normal_idle(void *);
static void mt6797_hif_normal_ledger(void *, struct mt6797_hif_ledger *);
static int mt6797_hif_join_bss(void *, unsigned int, const u8 *, const u8 *, unsigned int,
			      unsigned int, unsigned int, bool, bool, u64);
static int mt6797_hif_join_station(void *, unsigned int, const u8 *, unsigned int,
				  unsigned int, unsigned int, unsigned int, u64);
static int mt6797_hif_join_pm_connected(void *, unsigned int, unsigned int, unsigned int,
				       unsigned int, u64);
static int mt6797_hif_join_pm_abort(void *, unsigned int, u64);
static int mt6797_hif_join_remove_station(void *, unsigned int, u64);
static int mt6797_hif_join_channel(void *, unsigned int, u8, u8, unsigned int, bool, u64);
static int mt6797_hif_send_config(void *, enum mt6797_normal_config_kind, unsigned int,
				const u8 *, size_t, u64);
static void ieee80211_connection_loss(struct ieee80211_vif *);

#ifdef FIXTURE_DEAUTH_RETIRE
#ifndef FIXTURE_GTK7
static bool mt6797_ccmp_deauth_abort_owed(const struct mt6797_mac *);
static bool mt6797_hif_cleanup_abort_ready(void *);
#else
static bool mt6797_ccmp_cleanup_debt_ready(const struct mt6797_mac *);
static bool mt6797_ccmp_cleanup_credit_ready(const struct mt6797_mac *);
static bool mt6797_ccmp_pm_holds_deauth(const struct mt6797_mac *);
static bool mt6797_hif_cleanup_ready(void *);
static int mt6797_hif_retain_cleanup_page(void *);
static void mt6797_ccmp_tx_timing(struct mt6797_mac *, unsigned int, unsigned int, unsigned int);
static void mt6797_ccmp_cleanup_timing(struct mt6797_mac *, bool);
static void mt6797_ccmp_data_end_beacons(struct mt6797_mac *);
static struct sk_buff *skb_peek(const struct sk_buff_head *q) { return q->head; }
#endif
static int mt6797_hif_join_pm_abort_debt(void *, unsigned int, unsigned int, u64);
#endif
