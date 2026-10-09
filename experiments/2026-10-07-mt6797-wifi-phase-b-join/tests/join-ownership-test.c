/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * Frame ownership through the production join worker and close paths.
 * run-ownership-test.py extracts struct mt6797_mac and the join functions from
 * the selected mac.c; this file supplies only kernel/HIF shims and scenarios.
 * Deterministic host interleavings, not a kernel concurrency or firmware model.
 */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
#define IS_ENABLED(x) (x)
#define CONFIG_MT6797_PASSIVE_SCAN 1
#define CONFIG_MT6797_STATION_JOIN 1
#define CONFIG_MT6797_SCAN_TUNING_SAMPLE 0
#define BIT(n) (1U << (n))
#define ETH_ALEN 6
#define __aligned(x) __attribute__((aligned(x)))
#define NSEC_PER_SEC 1000000000ULL
#define NSEC_PER_MSEC 1000000ULL
#define NL80211_BAND_5GHZ 1
#define MT6797_HIF_RX_MAX_PACKET 2352U /* hif.h, not included here */
#define IEEE80211_TX_STAT_ACK BIT(0)
#define IEEE80211_STYPE_DEAUTH 0xc0
#define WLAN_EID_SSID 0
#define WLAN_EID_RSN 48
#define WLAN_EID_HT_CAPABILITY 45
#define WLAN_EID_VHT_CAPABILITY 191
#define WLAN_EID_MOBILITY_DOMAIN 54
#define WLAN_EID_FAST_BSS_TRANSITION 55
#define WLAN_EID_VENDOR_SPECIFIC 221
#define min(a, b) ((a) < (b) ? (a) : (b))
#define min_t(t, a, b) min((t)(a), (t)(b))
#define container_of(p, t, m) ((t *)((char *)(p) - offsetof(t, m)))
#define dev_info(...) do { } while (0)
#define dev_err(...) do { } while (0)
#define __maybe_unused __attribute__((unused))
#define wiphy_dev(w) (w)
#include "fixed-channels.h"
#include "join-events.h"
#include "join-rx.h"
#include "join-tx.h"
#include "eapol-rx.h"
#include "scan-wire.h"

struct mutex { int held; };
struct work_struct { int unused; };
struct delayed_work { struct work_struct work; };
struct completion { unsigned int done; };
struct ieee80211_supported_band { int unused; };
struct ieee80211_channel { int unused; };
struct ieee80211_rate { int unused; };
struct wiphy { u8 perm_addr[ETH_ALEN]; };
struct ieee80211_hw { void *priv; struct wiphy *wiphy; };
struct ieee80211_vif { int unused; };
struct ieee80211_tx_info { unsigned int flags; int band; };
struct ieee80211_rx_status { int band, freq, signal; };
struct mt6797_hif { int unused; };
struct mt6797_hif_tx_status { int unused; };
struct mt6797_hif_rx_result { size_t logical_bytes; };

/* Every skb carries an owner tag and a single release ledger. */
enum { OWNER_MAC80211 = 1, OWNER_DRIVER };
struct sk_buff {
	struct sk_buff *next;
	u8 data[64];
	unsigned int len, owner, released;
	union { struct ieee80211_tx_info tx; struct ieee80211_rx_status rx; } cb;
};
struct sk_buff_head { struct sk_buff *head; unsigned int qlen; int lock; };
#define IEEE80211_SKB_CB(s) (&(s)->cb.tx)
#define IEEE80211_SKB_RXCB(s) (&(s)->cb.rx)

static unsigned int dev_frees, mac80211_frees, statuses, rx_delivered, live;
static void release(struct sk_buff *s, unsigned int how)
{
	assert(s && !s->released);
	s->released = how;
	live--;
	free(s);
}
static void dev_kfree_skb(struct sk_buff *s)
{
	if (!s)
		return;
	/* Driver-owned frames and dropped RX copies only. */
	assert(s->owner == OWNER_DRIVER);
	dev_frees++;
	release(s, 1);
}
static struct sk_buff *new_skb(unsigned int owner)
{
	struct sk_buff *s = calloc(1, sizeof(*s));

	assert(s);
	s->owner = owner;
	live++;
	return s;
}
static struct sk_buff *dev_alloc_skb(unsigned int n)
{
	assert(n <= sizeof(((struct sk_buff *)0)->data));
	return new_skb(OWNER_DRIVER);
}
static void *skb_put_data(struct sk_buff *s, const void *d, unsigned int n)
{
	memcpy(s->data + s->len, d, n);
	s->len += n;
	return s->data;
}
static int skb_linearize(struct sk_buff *s) { (void)s; return 0; }
static void skb_queue_head_init(struct sk_buff_head *q) { q->head = NULL; q->qlen = 0; }
static struct sk_buff *skb_peek(struct sk_buff_head *q) { return q->head; }
static bool skb_queue_empty(const struct sk_buff_head *q) { return !q->head; }
static void __skb_queue_tail(struct sk_buff_head *q, struct sk_buff *s)
{
	struct sk_buff **p = &q->head;

	while (*p)
		p = &(*p)->next;
	s->next = NULL;
	*p = s;
	q->qlen++;
}
static struct sk_buff *__skb_dequeue(struct sk_buff_head *q)
{
	struct sk_buff *s = q->head;

	if (s) {
		q->head = s->next;
		s->next = NULL;
		q->qlen--;
	}
	return s;
}
static void skb_queue_splice_init(struct sk_buff_head *from, struct sk_buff_head *to)
{
	struct sk_buff *s;

	while ((s = __skb_dequeue(from)))
		__skb_queue_tail(to, s);
}
struct ieee80211_hw;
static void ieee80211_free_txskb(struct ieee80211_hw *hw, struct sk_buff *s)
{
	(void)hw;
	/* mac80211 may only be handed back frames it gave the driver. */
	assert(s->owner == OWNER_MAC80211);
	mac80211_frees++;
	release(s, 2);
}
static void ieee80211_tx_status_ni(struct ieee80211_hw *hw, struct sk_buff *s)
{
	(void)hw;
	assert(s->owner == OWNER_MAC80211);
	statuses++;
	release(s, 3);
}
static void ieee80211_rx_ni(struct ieee80211_hw *hw, struct sk_buff *s)
{
	(void)hw;
	rx_delivered++;
	release(s, 4);
}
static void ieee80211_tx_info_clear_status(struct ieee80211_tx_info *i) { i->flags = 0; }
static void ieee80211_connection_loss(struct ieee80211_vif *v) { (void)v; }

static unsigned int get_unaligned_le16(const void *p)
{ const u8 *b = p; return b[0] | b[1] << 8; }
static void put_unaligned_le16(unsigned int v, void *p)
{ u8 *b = p; b[0] = v; b[1] = v >> 8; }
static bool ether_addr_equal(const u8 *a, const u8 *b) { return !memcmp(a, b, ETH_ALEN); }
static void ether_addr_copy(u8 *a, const u8 *b) { memcpy(a, b, ETH_ALEN); }

static u64 now_ns = 1000 * NSEC_PER_MSEC;
static u64 ktime_get_ns(void) { return now_ns; }
static unsigned long nsecs_to_jiffies(u64 ns) { return ns / NSEC_PER_MSEC; }
static unsigned long msecs_to_jiffies(unsigned int ms) { return ms; }
static unsigned int locked;
static void mutex_lock(struct mutex *m) { assert(!m->held); m->held = 1; locked++; }
static void mutex_unlock(struct mutex *m) { assert(m->held); m->held = 0; locked--; }
#define spin_lock_irqsave(l, f) do { (void)(l); (f) = 0; } while (0)
#define spin_unlock_irqrestore(l, f) do { (void)(l); (void)(f); } while (0)
static void complete_all(struct completion *c) { c->done++; }
static void reinit_completion(struct completion *c) { c->done = 0; }
static unsigned int scheduled, cancelled;
static void schedule_delayed_work(struct delayed_work *w, unsigned long d)
{ (void)w; (void)d; scheduled++; }
static void cancel_delayed_work_sync(struct delayed_work *w)
{ (void)w; assert(!locked); cancelled++; }
#define to_delayed_work(w) container_of(w, struct delayed_work, work)

/* HIF transport: scripted RX packets, page releases and submissions. */
static u8 script[6][512];
static size_t script_bytes[6];
static unsigned int script_count, script_next, released, submissions;
static bool idle = true;
static int mt6797_hif_read32(struct mt6797_hif *h, unsigned int reg, u64 d, u32 *v)
{ (void)h; (void)d; *v = reg ? BIT(8) : 0x0279 | BIT(21); return 0; }
static int mt6797_hif_reconcile_runtime(struct mt6797_hif *h, u64 d,
	struct mt6797_hif_tx_status *s, struct mt6797_normal_release *a)
{ (void)h; (void)d; (void)s; a->released_pages = released; released = 0; return 0; }
static bool mt6797_hif_normal_idle(struct mt6797_hif *h) { (void)h; return idle; }
struct mt6797_hif_ledger { unsigned phase, tc4_free, tc4_limit, pending_cpu, pending_ffa; bool sequences, locked; };
static void mt6797_hif_normal_ledger(struct mt6797_hif *h, struct mt6797_hif_ledger *o) { (void)h; *o = (struct mt6797_hif_ledger){0}; }
static int mt6797_hif_receive_packet(struct mt6797_hif *h, unsigned int port, u64 d,
	u8 *buf, size_t cap, struct mt6797_hif_rx_result *rx)
{
	(void)h; (void)d;
	if (port || script_next == script_count)
		return -EAGAIN;
	assert(script_bytes[script_next] <= cap);
	memcpy(buf, script[script_next], script_bytes[script_next]);
	rx->logical_bytes = script_bytes[script_next++];
	return 0;
}
static int mt6797_hif_send_management(struct mt6797_hif *h, const u8 *f, size_t n,
	unsigned int wlan, unsigned int pid, unsigned int life, unsigned int count, u64 d)
{
	(void)h; (void)f; (void)d;
	assert(n >= 24 && wlan == 1 && pid && life == 500 && count == 3);
	submissions++;
	return 0;
}
static int mt6797_hif_join_remove_station(struct mt6797_hif *h, unsigned int s, u64 d)
{ (void)h; (void)s; (void)d; assert(!"no cleanup command in these scenarios"); return -EIO; }
static int mt6797_hif_join_channel(struct mt6797_hif *h, unsigned int s, u8 t, u8 c,
	unsigned int ms, bool abort, u64 d)
{ (void)h; (void)s; (void)t; (void)c; (void)ms; (void)abort; (void)d; assert(0); return -EIO; }
static int mt6797_hif_send_config(struct mt6797_hif *h, unsigned int k, unsigned int s,
	const u8 *p, size_t n, u64 d)
{ (void)h; (void)k; (void)s; (void)p; (void)n; (void)d; assert(0); return -EIO; }
struct mt6797_mac;
static int mt6797_mac_send(struct mt6797_mac *m, unsigned int k, const u8 *p, size_t n)
{ (void)m; (void)k; (void)p; (void)n; assert(!"no BSS command in these scenarios"); return -EIO; }

#include "ownership-functions.h"

static const u8 own[ETH_ALEN] = { 2, 0, 0, 0, 0, 1 };
static const u8 ap[ETH_ALEN] = { 2, 0, 0, 0, 0, 2 };
static struct wiphy wiphy;
static struct ieee80211_hw hw;
static struct ieee80211_vif vif;
static struct mt6797_mac mac;
/* Driver-paced wait stub: an optional callback runs while the mutex is dropped. */
static void (*during_wait)(void);
static unsigned long wait_for_completion_timeout(struct completion *c, unsigned long t)
{
	(void)c; (void)t;
	assert(!locked);
	if (during_wait)
		during_wait();
	return 0;
}

static void setup(void)
{
	memset(&mac, 0, sizeof(mac));
	memcpy(wiphy.perm_addr, own, ETH_ALEN);
	hw.wiphy = &wiphy;
	hw.priv = &mac;
	mac.hw = &hw;
	mac.vif = &vif;
	mac.hif = (struct mt6797_hif *)&mac;
	skb_queue_head_init(&mac.join_queue);
	memcpy(mac.join_ap, ap, ETH_ALEN);
	memcpy(mac.join_bssid, ap, ETH_ALEN);
	mac.join_running = mac.join_open = true;
	mac.join_peer_used = mac.join_peer_ready = true;
	mac.join_channel_granted = true;
	mac.started = mac.configured = true;
	mac.join_next_pid = 1;
	mac.sequence = 10;
	mac.join_deadline = mac.join_grant_deadline = now_ns + 5 * NSEC_PER_SEC;
	script_count = script_next = released = submissions = 0;
	dev_frees = mac80211_frees = statuses = rx_delivered = 0;
	during_wait = NULL;
	idle = true;
}

/* A 26-byte deauthentication or 30-byte authentication from us to the AP. */
static struct sk_buff *frame(unsigned int owner, unsigned int subtype)
{
	struct sk_buff *s = new_skb(owner);

	s->len = subtype == 12 ? 26 : 30;
	put_unaligned_le16(subtype << 4, s->data);
	memcpy(s->data + 4, ap, ETH_ALEN);
	memcpy(s->data + 10, own, ETH_ALEN);
	memcpy(s->data + 16, ap, ETH_ALEN);
	put_unaligned_le16(5 << 4, s->data + 22);
	if (subtype == 11)
		put_unaligned_le16(1, s->data + 26); /* Open System, sequence 1. */
	return s;
}

static void queue_internal_deauth(void)
{
	struct sk_buff *s = frame(OWNER_DRIVER, 12);

	mac.join_cleanup_requested = true;
	mac.join_tx_allowed = BIT(12);
	mac.join_seen |= BIT(12);
	mac.join_rx_allowed = BIT(10) | BIT(12);
	mac.join_internal = s;
	mac.join_queue_bytes = s->len;
	__skb_queue_tail(&mac.join_queue, s);
}

static void script_event(u8 eid, const u8 *body, size_t n)
{
	u8 *p = script[script_count];

	assert(script_count < 6 && 8 + n <= sizeof(script[0]));
	memset(p, 0, 8);
	put_unaligned_le16(8 + n, p);
	put_unaligned_le16(0xe000, p + 2);
	p[4] = eid;
	memcpy(p + 8, body, n);
	script_bytes[script_count++] = 8 + n;
}

static void script_tx_done(u8 status)
{
	u8 b[16] = { 0 };

	b[0] = mac.join_pid;
	b[1] = status;
	b[4] = 1;
	script_event(0x0f, b, sizeof(b));
}

static void run_worker(void)
{
	mt6797_mac_join_work(&mac.join_work.work);
	assert(!locked);
}

/* A clear WPA2 EAPOL-Key frame from the target to this station on channel 40
 * in the public gen3 RXD layout, native (groups 4) or translated Ethernet
 * (groups 4 and 8), as the 0140 decoder fixture builds it; no key material.
 */
static void script_eapol(bool translated)
{
	static const u8 origin[ETH_ALEN] = { 2, 0, 0, 0, 0, 3 };
	static const u8 native_header[32] = {
		8, 2, 0, 0, 2, 0, 0, 0, 0, 1, 2, 0, 0, 0, 0, 2,
		2, 0, 0, 0, 0, 3, 0x30, 0x12, 0xaa, 0xaa, 3, 0, 0, 0, 0x88, 0x8e
	};
	u8 *p = script[script_count];
	unsigned groups = translated ? 12 : 4;
	size_t off = 16, payload, bytes;
	unsigned length = 95;

	assert(script_count < 6);
	memset(p, 0, sizeof(script[0]));
	put_unaligned_le16(0x4000 | groups << 9, p + 2);
	p[4] = 2; p[5] = 40; p[6] = translated ? 0x8e : 24; p[8] = 1;
	put_unaligned_le16(0xc000, p + 10);
	if (groups & 8) {
		p[off] = 8; p[off + 1] = 2;
		memcpy(p + off + 2, ap, ETH_ALEN); put_unaligned_le16(0x1230, p + off + 8); off += 16;
	}
	p[off + 9] = 51; off += 24;
	if (translated) {
		memcpy(p + off, own, ETH_ALEN); memcpy(p + off + 6, origin, ETH_ALEN);
		p[off + 12] = 0x88; p[off + 13] = 0x8e; payload = off + 14;
	} else {
		memcpy(p + off, native_header, 32); payload = off + 32;
	}
	p[payload] = 2; p[payload + 1] = 3;
	p[payload + 2] = length >> 8; p[payload + 3] = length;
	p[payload + 4] = 2; p[payload + 6] = 0x8a; p[payload + 8] = 16;
	bytes = payload + length + 4;
	put_unaligned_le16(bytes, p);
	script_bytes[script_count++] = bytes;
}

static void submit_inflight(void)
{
	run_worker(); /* Dequeue and submit; nothing received yet. */
	assert(mac.join_inflight && submissions == 1 && mac.join_page_debt);
	released = mac.join_page_debt; /* Credit returns on the next poll. */
}

static void close_now(void);

int main(void)
{
	/* 1. Internal deauth TX done with NACK: the existing completion path
	 *    owns it, frees it once with dev_kfree_skb, and clears the pointer.
	 */
	setup();
	queue_internal_deauth();
	submit_inflight();
	assert(mac.join_internal == mac.join_inflight);
	script_tx_done(1);
	run_worker();
	assert(mac.first_error == -ENOLINK && mac.join_retired);
	assert(!mac.join_inflight && !mac.join_internal && !mac.join_deauth_done);
	assert(dev_frees == 1 && !mac80211_frees && !statuses && !live);

	/* 2. Unknown event while the internal deauth is in flight: the failure
	 *    path discards it as a driver frame and clears join_internal.
	 */
	setup();
	queue_internal_deauth();
	submit_inflight();
	script_event(0x7e, (const u8[8]){ 0 }, 8);
	run_worker();
	assert(mac.first_error && mac.join_retired && !mac.join_running);
	assert(!mac.join_inflight && !mac.join_internal);
	assert(dev_frees == 1 && !mac80211_frees && !statuses && !live);

	/* 2b. Same failure with the internal deauth still queued behind an
	 *     in-flight mac80211 frame: each goes back to its own owner.
	 */
	setup();
	mac.join_tx_allowed = BIT(11);
	__skb_queue_tail(&mac.join_queue, frame(OWNER_MAC80211, 11));
	submit_inflight();
	queue_internal_deauth();
	script_event(0x7e, (const u8[8]){ 0 }, 8);
	run_worker();
	assert(!mac.join_inflight && !mac.join_internal && skb_queue_empty(&mac.join_queue));
	assert(dev_frees == 1 && mac80211_frees == 1 && !statuses && !live);

	/* 3. Close while a callback waits for its management frame: the waiter
	 *    returns cancelled, the in-flight mac80211 frame goes back to
	 *    mac80211 and the queued internal deauth is freed by the driver.
	 */
	setup();
	mac.join_tx_allowed = BIT(11);
	__skb_queue_tail(&mac.join_queue, frame(OWNER_MAC80211, 11));
	submit_inflight();
	queue_internal_deauth();
	mac.join_frame_deadline = now_ns + 750 * NSEC_PER_MSEC;
	during_wait = close_now;
	mutex_lock(&mac.mutex);
	assert(mt6797_mac_join_wait_management(&mac) == -ECANCELED);
	mutex_unlock(&mac.mutex);
	assert(cancelled && mac.join_retired && !mac.join_running);
	assert(!mac.join_inflight && !mac.join_internal && skb_queue_empty(&mac.join_queue));
	assert(dev_frees == 1 && mac80211_frees == 1 && !statuses && !live);

	/* 4. Close with nothing driver-owned: external frames only, unchanged path. */
	setup();
	mac.join_tx_allowed = BIT(11);
	__skb_queue_tail(&mac.join_queue, frame(OWNER_MAC80211, 11));
	mt6797_mac_join_close(&mac);
	assert(!dev_frees && mac80211_frees == 1 && !live && !mac.join_internal);

	/* 5. Phase C1: clear EAPOL frames from the target are observed and dropped
	 *    after a status-0 association response, before or after the local
	 *    activation, at most twice; a third falls through to the refusal.
	 *    Nothing is delivered to mac80211 and nothing is transmitted.
	 */
	setup();
	mac.join_assoc_received = true; mac.join_assoc_status = 0; mac.join_sta_active = false;
	script_eapol(false);                              /* early: before activation */
	run_worker();
	assert(!mac.first_error && mac.join_eapol_seen == 1 && !rx_delivered && !submissions && mac.join_running);
	mac.join_sta_active = true;
	script_eapol(true);                               /* translated layout, after activation */
	run_worker();
	assert(!mac.first_error && mac.join_eapol_seen == 2 && !rx_delivered && !submissions);
	script_eapol(false);                              /* third: beyond the budget */
	run_worker();
	assert(mac.first_error == -EPROTO && mac.join_retired && !mac.join_running && !rx_delivered);
	/* 5b. Before any association response, or after a denied one, the same
	 *     frame is refused as before. */
	setup(); script_eapol(false); run_worker();
	assert(mac.first_error == -EPROTO && !mac.join_eapol_seen);
	setup(); mac.join_assoc_received = true; mac.join_assoc_status = 45; script_eapol(true); run_worker();
	assert(mac.first_error == -EPROTO && !mac.join_eapol_seen);
	/* 5c. After the deauthentication completed the window is closed. */
	setup(); mac.join_assoc_received = true; mac.join_deauth_done = true; script_eapol(false); run_worker();
	assert(mac.first_error == -EPROTO && !mac.join_eapol_seen);

	/* 6. The finite hold: the queued driver deauthentication is not submitted
	 *    while the hold runs and nothing was observed; time or an observation
	 *    releases it; other frames are never held.
	 */
	setup(); queue_internal_deauth();
	mac.join_hold_until = now_ns + 250 * NSEC_PER_MSEC;
	run_worker();
	assert(!submissions && !mac.join_inflight && !mac.first_error && mac.join_internal);
	now_ns += 260 * NSEC_PER_MSEC;
	run_worker();
	assert(submissions == 1 && mac.join_inflight == mac.join_internal);
	mt6797_mac_join_close(&mac);
	setup(); queue_internal_deauth();
	mac.join_hold_until = now_ns + 250 * NSEC_PER_MSEC; mac.join_eapol_seen = 1;
	run_worker();
	assert(submissions == 1 && mac.join_inflight == mac.join_internal);
	mt6797_mac_join_close(&mac);
	setup(); mac.join_tx_allowed = BIT(11);
	__skb_queue_tail(&mac.join_queue, frame(OWNER_MAC80211, 11));
	mac.join_hold_until = now_ns + 250 * NSEC_PER_MSEC;
	run_worker();
	assert(submissions == 1 && mac.join_inflight && mac.join_inflight->owner == OWNER_MAC80211);
	mt6797_mac_join_close(&mac);

	puts("join_ownership=pass; production close/worker paths; exact-once release; EAPOL observation window and hold; no device");
	return 0;
}

static void close_now(void)
{
	mt6797_mac_join_close(&mac);
}
