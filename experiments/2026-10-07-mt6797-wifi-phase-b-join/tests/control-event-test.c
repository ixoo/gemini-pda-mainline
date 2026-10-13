// SPDX-License-Identifier: GPL-2.0-only
/* Host fixture for the ACTUAL join 0x11 (owned-BSS absence/presence) admission in
 * mt6797_mac_join_control_event. It includes the real join-events.h (mt6797_join_event
 * and the shape parsers) and supplies a minimal struct plus kernel shims for the
 * unrelated event paths (which a 0x11 event never enters). It proves the R34 fix:
 * valid owned-slot notifications admit in pre-data/data/teardown with no lifetime cap,
 * malformed/foreign/sequence events are honest refusals, and quota/reserved never
 * touch any credit term. Not a kernel concurrency model. */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef uint8_t u8; typedef uint16_t u16; typedef uint32_t u32; typedef uint64_t u64;
#define IS_ENABLED(x) (x)
#define CONFIG_MT6797_STATION_JOIN 1
#define CONFIG_MT6797_PASSIVE_SCAN 1
#define BIT(n) (1U << (n))
#define ETH_ALEN 6
#define NSEC_PER_MSEC 1000000ULL
#define min(a, b) ((a) < (b) ? (a) : (b))
#define min_t(t, a, b) min((t)(a), (t)(b))
struct mt6797_hif; struct wiphy { u8 perm_addr[ETH_ALEN]; };
struct ieee80211_hw { struct wiphy *wiphy; };
struct completion { unsigned int done; };
struct sk_buff { int len; };
struct sk_buff_head { int qlen; int lock; };
#define wiphy_dev(w) ((void *)(w))
static unsigned int infos;
#define dev_info(dev, ...) do { (void)(dev); infos++; } while (0)
#define dev_err(dev, ...) do { (void)(dev); } while (0)
static u64 g_now;
static u64 ktime_get_ns(void) { return g_now; }
static void complete_all(struct completion *c) { if (c) c->done++; }
static bool ether_addr_equal(const u8 *a, const u8 *b) { return !memcmp(a, b, ETH_ALEN); }
static bool is_broadcast_ether_addr(const u8 *a)
{ return (a[0]&a[1]&a[2]&a[3]&a[4]&a[5]) == 0xff; }
static unsigned int g_qlen, g_stops, g_wakes;
static unsigned int skb_queue_len(const struct sk_buff_head *q) { (void)q; return g_qlen; }
static bool skb_queue_empty(const struct sk_buff_head *q) { (void)q; return g_qlen == 0; }
static void ieee80211_stop_queues(struct ieee80211_hw *hw) { (void)hw; g_stops++; }
static void ieee80211_wake_queues(struct ieee80211_hw *hw) { (void)hw; g_wakes++; }
#define spin_lock_irqsave(l, f) do { (void)(l); (f) = 0; } while (0)
#define spin_unlock_irqrestore(l, f) do { (void)(l); (void)(f); } while (0)
static int mt6797_hif_read32(struct mt6797_hif *h, unsigned int r, u64 d, u32 *v)
{ (void)h; (void)r; (void)d; *v = 0; return 0; }

#include "join-events.h"  /* real mt6797_join_event / le16 / channel_grant / sta_active */

struct mt6797_mac {
	struct mt6797_hif *hif;
	struct ieee80211_hw *hw;
	u8 join_packet[64];
	u8 join_ap[ETH_ALEN];
	unsigned int join_absence_seen, join_absence_refused;
	unsigned int join_channel_token, join_requested_ms, join_cleanup_stage;
	unsigned int join_key_pairwise, join_lifetimes, join_sta_sequence;
	u64 join_deadline, join_grant_deadline, join_hold_until;
	struct completion join_channel_done, join_sta_done;
	struct sk_buff *join_inflight, *join_internal;
	struct sk_buff_head join_queue;
	unsigned int join_queue_bytes;
	unsigned int join_page_debt, join_data_page_debt;
	bool join_credit_pending;
	int first_error;
	bool join_running, join_retired, join_open, join_closed, closing;
	bool join_channel_pending, join_channel_granted;
	bool join_sta_pending, join_sta_active, join_bss_configured;
	bool join_cleanup_done, join_cleanup_requested, join_deauth_done;
	bool join_key_pairwise_submitted, join_key_group_submitted;
	bool join_key_done, join_key_done_second;
	bool join_bss_absent, join_tx_stopped, join_data_phase, join_data_ended;
};

#include CONTROL_FUNCTIONS

/* Build a 12-byte 0x11 event: le16 len=12, le16 0xe000, id 0x11, seq, then the
 * 4-byte body ucBssIndex/ucIsAbsent/ucBssFreeQuota/reserved. */
static void ev(struct mt6797_mac *m, u8 seq, u8 bss, u8 absent, u8 quota, u8 reserved)
{
	u8 *p = m->join_packet;
	memset(p, 0, sizeof(m->join_packet));
	p[0] = 12; p[1] = 0; p[2] = 0x00; p[3] = 0xe0; p[4] = 0x11; p[5] = seq;
	p[8] = bss; p[9] = absent; p[10] = quota; p[11] = reserved;
}

static void base(struct mt6797_mac *m)
{
	static struct wiphy wiphy;
	static struct ieee80211_hw hw = { .wiphy = &wiphy };

	memset(m, 0, sizeof(*m));
	m->hw = &hw;
	m->join_running = true;
}

int main(void)
{
	struct mt6797_mac m;

	/* pre-data valid absent -> admitted, recorded absent, counted, uncapped */
	base(&m); ev(&m, 0, 0, 1, 7, 0);
	assert(mt6797_mac_join_control_event(&m, 12) == 0);
	assert(m.join_bss_absent && m.join_absence_seen == 1 && m.join_absence_refused == 0);
	/* present -> admitted, cleared; data phase too; teardown too; all uncapped */
	ev(&m, 0, 0, 0, 0, 0);
	assert(mt6797_mac_join_control_event(&m, 12) == 0 && !m.join_bss_absent && m.join_absence_seen == 2);
	m.join_data_phase = true;
	ev(&m, 0, 0, 1, 0, 0); assert(mt6797_mac_join_control_event(&m, 12) == 0 && m.join_absence_seen == 3);
	m.join_data_phase = false; m.join_cleanup_requested = true; m.join_cleanup_stage = 3;
	ev(&m, 0, 0, 0, 0, 0); assert(mt6797_mac_join_control_event(&m, 12) == 0 && m.join_absence_seen == 4);
	/* > 2 repeats keep admitting (no lifetime cap) */
	ev(&m, 0, 0, 1, 0, 0); assert(mt6797_mac_join_control_event(&m, 12) == 0 && m.join_absence_seen == 5);
	ev(&m, 0, 0, 0, 0, 0); assert(mt6797_mac_join_control_event(&m, 12) == 0 && m.join_absence_seen == 6);
	assert(m.join_absence_refused == 0);

	/* refusals: foreign slot, non-boolean absent, nonzero sequence, not running */
	base(&m); ev(&m, 0, 1, 1, 0, 0);  /* slot 1 */
	unsigned int before = infos;
	assert(mt6797_mac_join_control_event(&m, 12) == -EPROTO && m.join_absence_refused == 1);
	assert(infos == before + 1); /* body logged before refusal */
	base(&m); ev(&m, 0, 0, 2, 0, 0);  /* absent 2 */
	assert(mt6797_mac_join_control_event(&m, 12) == -EPROTO && m.join_absence_refused == 1);
	base(&m); ev(&m, 1, 0, 1, 0, 0);  /* seq 1 */
	assert(mt6797_mac_join_control_event(&m, 12) == -EPROTO);
	base(&m); m.join_retired = true; ev(&m, 0, 0, 1, 0, 0);
	assert(mt6797_mac_join_control_event(&m, 12) == -EPROTO);
	/* Exact shape only: neither truncated nor extended bodies are admitted. */
	for (unsigned int bytes = 8; bytes <= 16; bytes++) {
		if (bytes == 12)
			continue;
		base(&m); ev(&m, 0, 0, 1, 0, 0); m.join_packet[0] = bytes;
		assert(mt6797_mac_join_control_event(&m, bytes) == -EPROTO);
		assert(!m.join_absence_seen && !m.join_bss_absent);
	}
	base(&m); m.join_running = false; ev(&m, 0, 0, 1, 0, 0);
	assert(mt6797_mac_join_control_event(&m, 12) == -EPROTO);

	/* quota/reserved are metadata: a nonzero quota/reserved is still admitted and
	 * changes nothing about the ledger (there is no credit field here to touch). */
	base(&m); ev(&m, 0, 0, 1, 255, 255);
	m.join_page_debt = 1; m.join_data_page_debt = 2; m.join_credit_pending = true;
	assert(mt6797_mac_join_control_event(&m, 12) == 0 && m.join_bss_absent);
	assert(m.join_page_debt == 1 && m.join_data_page_debt == 2 && m.join_credit_pending);

	puts("control-event-admission scenarios OK");
	return 0;
}
