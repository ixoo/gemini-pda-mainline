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
#define RX_FLAG_NO_SIGNAL_VAL (1U << 8)
typedef unsigned char u8;
static const u8 own[ETH_ALEN] = { 2, 0, 0, 0, 0, 1 };
static const u8 ap[ETH_ALEN] = { 2, 0, 0, 0, 0, 2 };
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
static unsigned int infos; /* production dev_info records */
/* Counted, format-checked, never printed: the arguments stay evaluated. */
#define dev_info(dev, ...) do { (void)(dev); infos++; if (0) printf(__VA_ARGS__); } while (0)
#define dev_err(...) do { } while (0)
#define __maybe_unused __attribute__((unused))
#define wiphy_dev(w) (w)
#include "fixed-channels.h"
#include "join-events.h"
#include "join-rx.h"
#include "join-tx.h"
#include "eapol-rx.h"
#include "join-refused.h"
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
struct ieee80211_tx_info { unsigned int flags; int band; struct { unsigned int flags; } control; };
#define IEEE80211_TX_CTRL_PORT_CTRL_PROTO (1U << 1)
struct ieee80211_tx_control { int unused; };
struct ieee80211_rx_status { int band, freq, signal; unsigned int flag; };
struct mt6797_hif { int unused; };
struct mt6797_hif_tx_status { int unused; };
struct mt6797_hif_rx_result { size_t logical_bytes; };

/* Every skb carries an owner tag and a single release ledger. */
enum { OWNER_MAC80211 = 1, OWNER_DRIVER };
struct sk_buff {
	struct sk_buff *next;
	u8 data[256];
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
#define skb_queue_walk_safe(q, s, t) for ((s) = (q)->head, (t) = (s) ? (s)->next : NULL; (s); (s) = (t), (t) = (s) ? (s)->next : NULL)
static void __skb_unlink(struct sk_buff *s, struct sk_buff_head *q)
{
	struct sk_buff **link = &q->head;

	while (*link && *link != s)
		link = &(*link)->next;
	assert(*link == s);
	*link = s->next;
	s->next = NULL;
	q->qlen--;
}
static int skb_copy_bits(const struct sk_buff *s, int off, void *to, int n)
{
	if (off < 0 || (unsigned)(off + n) > s->len)
		return -EFAULT;
	memcpy(to, s->data + off, n);
	return 0;
}
static unsigned int skb_queue_len(const struct sk_buff_head *q) { return q->qlen; }
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
static unsigned int security_submissions;
static int mt6797_hif_send_security(struct mt6797_hif *h, const u8 *f, size_t n,
	unsigned int wlan, unsigned int pid, unsigned int life, unsigned int count, u64 d)
{
	(void)h; (void)d;
	/* Ethernet II EAPOL to the target from this station, as the worker builds it. */
	assert(n >= 18 && n <= 1518 && wlan == 1 && pid && life == 500 && count == 3);
	assert(!memcmp(f, ap, ETH_ALEN) && !memcmp(f + 6, own, ETH_ALEN) && f[12] == 0x88 && f[13] == 0x8e);
	security_submissions++;
	submissions++;
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
static int mt6797_hif_join_key(struct mt6797_hif *h, unsigned int s, bool add, bool pairwise,
	const u8 *peer, unsigned int key_id, const u8 *material, u64 d)
{ (void)h; (void)s; (void)add; (void)pairwise; (void)peer; (void)key_id; (void)material; (void)d;
  assert(!"no key command in these scenarios"); return -EIO; }
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
	security_submissions = 0;
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

/* The association request mac80211 builds for the Phase C1 connect against
 * a legacy 5 GHz BSS (ieee80211_send_assoc, legacy connection mode, one
 * hardware queue so no WMM): header, capability with privacy, listen interval
 * 5, SSID, the eight OFDM supported rates, then the connect request's RSN
 * element. `variant` perturbs one thing for the refusal cases.
 */
enum { ASSOC_GOOD, ASSOC_RSN_TKIP, ASSOC_RSN_TWICE, ASSOC_RSN_SHORT, ASSOC_HT, ASSOC_WMM,
       ASSOC_RSN_CAPAB_MFPC, ASSOC_RSN_CAPAB_PREAUTH, ASSOC_RSN_CAPAB_NO_PAIRWISE,
       ASSOC_RSN_CAPAB_EXTRA_BIT, ASSOC_RSN_CAPAB_HIGH_BYTE, ASSOC_RSN_CAPAB_COUNTERS_4,
       ASSOC_NO_RSN, ASSOC_RSN_CAPAB_WMM };
static struct sk_buff *assoc_frame(unsigned int variant)
{
	static const u8 rsn[22] = {
		0x30, 0x14, 0x01, 0x00, 0x00, 0x0f, 0xac, 0x04, 0x01, 0x00, 0x00,
		0x0f, 0xac, 0x04, 0x01, 0x00, 0x00, 0x0f, 0xac, 0x02, 0x00, 0x00
	};
	static const u8 rates[10] = { 1, 8, 0x8c, 0x12, 0x98, 0x24, 0xb0, 0x48, 0x60, 0x6c };
	static const u8 ht[28] = { 45, 26, 0x6f, 0x00, 0x17 };
	static const u8 wmm[9] = { 221, 7, 0x00, 0x50, 0xf2, 2, 0, 1, 0 };
	struct sk_buff *s = new_skb(OWNER_MAC80211);
	u8 *p = s->data;
	size_t n = 24;

	memset(p, 0, sizeof(s->data));
	memcpy(p + 4, ap, ETH_ALEN); memcpy(p + 10, own, ETH_ALEN); memcpy(p + 16, ap, ETH_ALEN);
	put_unaligned_le16(7 << 4, p + 22);
	put_unaligned_le16(0x0011, p + n); n += 2;    /* ESS, privacy */
	put_unaligned_le16(5, p + n); n += 2;         /* listen interval */
	p[n] = 0; p[n + 1] = 7; memcpy(p + n + 2, "gemini7", 7); n += 9;
	memcpy(p + n, rates, sizeof(rates)); n += sizeof(rates);
	if (variant != ASSOC_NO_RSN) {
		memcpy(p + n, rsn, sizeof(rsn));
		if (variant == ASSOC_RSN_TKIP)
			p[n + 13] = 0x02;
		/* Capabilities: the supplicant's 16-replay-counter declaration is
		 * the one admitted variant; every other bit pattern is refused.
		 */
		if (variant == ASSOC_RSN_CAPAB_WMM)
			p[n + 20] = 0x0c;
		if (variant == ASSOC_RSN_CAPAB_MFPC)
			p[n + 20] = 0x80;
		if (variant == ASSOC_RSN_CAPAB_PREAUTH)
			p[n + 20] = 0x01;
		if (variant == ASSOC_RSN_CAPAB_NO_PAIRWISE)
			p[n + 20] = 0x02;
		if (variant == ASSOC_RSN_CAPAB_EXTRA_BIT)
			p[n + 20] = 0x0d;
		if (variant == ASSOC_RSN_CAPAB_HIGH_BYTE)
			p[n + 21] = 0x0c;
		if (variant == ASSOC_RSN_CAPAB_COUNTERS_4)
			p[n + 20] = 0x08;
		if (variant == ASSOC_RSN_SHORT) {
			p[n + 1] = 18; n += 20;
		} else {
			n += sizeof(rsn);
		}
		if (variant == ASSOC_RSN_TWICE) {
			memcpy(p + n, rsn, sizeof(rsn)); n += sizeof(rsn);
		}
	}
	if (variant == ASSOC_HT) {
		memcpy(p + n, ht, sizeof(ht)); n += sizeof(ht);
	}
	if (variant == ASSOC_WMM) {
		memcpy(p + n, wmm, sizeof(wmm)); n += sizeof(wmm);
	}
	s->len = n;
	return s;
}

static struct sk_buff *eapol_tx_frame(unsigned body_bytes)
{
	static const u8 llc[8] = { 0xaa, 0xaa, 3, 0, 0, 0, 0x88, 0x8e };
	struct sk_buff *s = new_skb(OWNER_MAC80211);
	u8 *p = s->data;

	assert(32 + body_bytes <= sizeof(s->data));
	memset(p, 0, sizeof(s->data));
	put_unaligned_le16(0x0108, p);
	memcpy(p + 4, ap, ETH_ALEN); memcpy(p + 10, own, ETH_ALEN); memcpy(p + 16, ap, ETH_ALEN);
	memcpy(p + 24, llc, 8);
	p[32] = 2; p[33] = 3; p[34] = (body_bytes - 4) >> 8; p[35] = (body_bytes - 4) & 255;
	s->len = 32 + body_bytes;
	s->cb.tx.control.flags = IEEE80211_TX_CTRL_PORT_CTRL_PROTO;
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
static void script_eapol_bss(bool translated, bool vector, bool padding, unsigned bss)
{
	static const u8 origin[ETH_ALEN] = { 2, 0, 0, 0, 0, 3 };
	static const u8 native_header[32] = {
		8, 2, 0, 0, 2, 0, 0, 0, 0, 1, 2, 0, 0, 0, 0, 2,
		2, 0, 0, 0, 0, 3, 0x30, 0x12, 0xaa, 0xaa, 3, 0, 0, 0, 0x88, 0x8e
	};
	u8 *p = script[script_count];
	unsigned groups = (translated ? 8 : 0) | (vector ? 4 : 0);
	size_t off = 16, payload, bytes;
	unsigned length = 95;

	assert(script_count < 6);
	memset(p, 0, sizeof(script[0]));
	put_unaligned_le16(0x4000 | groups << 9, p + 2);
	p[4] = 2; p[5] = 40; p[6] = (translated ? 0x8e : 24) | (padding ? 0x40 : 0); p[7] = bss << 2; p[8] = 1;
	put_unaligned_le16(0xc000, p + 10);
	if (groups & 8) {
		p[off] = 8; p[off + 1] = 2;
		memcpy(p + off + 2, ap, ETH_ALEN); put_unaligned_le16(0x1230, p + off + 8); off += 16;
	}
	if (vector) {
		p[off + 9] = 51; off += 24;
	}
	if (padding)
		off += 2;
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

static void script_eapol_layout(bool translated, bool vector, bool padding) { script_eapol_bss(translated, vector, padding, 0); }
static void script_eapol(bool translated) { script_eapol_layout(translated, true, false); }

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
	assert(!mac.first_error && mac.join_eapol_seen == 1 && rx_delivered == 1 && !submissions && mac.join_running);
	mac.join_sta_active = true;
	script_eapol(true);                               /* translated layout, after activation */
	run_worker();
	assert(!mac.first_error && mac.join_eapol_seen == 2 && rx_delivered == 2 && !submissions);
	script_eapol(false);                              /* third: beyond the budget */
	run_worker();
	assert(mac.first_error == -EPROTO && mac.join_retired && !mac.join_running && rx_delivered == 2);
	/* 5b. Before any association response, or after a denied one, the same
	 *     frame is refused as before. */
	setup(); script_eapol(false); run_worker();
	assert(mac.first_error == -EPROTO && !mac.join_eapol_seen);
	setup(); mac.join_assoc_received = true; mac.join_assoc_status = 45; script_eapol(true); run_worker();
	assert(mac.first_error == -EPROTO && !mac.join_eapol_seen);
	/* 5c. A hypothetical source-valid packet with runtime 10's measured
	 *     length and group set (translated, group 4 only, header padding,
	 *     147 bytes), before activation; its fields are the fixture's, not
	 *     the captured packet's. With group 3 optional it is observed.
	 */
	setup(); mac.join_assoc_received = true; mac.join_assoc_status = 0; mac.join_sta_active = false;
	script_eapol_layout(true, false, true);
	assert(script_bytes[script_count - 1] == 147);
	run_worker();
	assert(!mac.first_error && mac.join_eapol_seen == 1 && rx_delivered == 1 && !submissions && mac.join_running);
	mt6797_mac_join_close(&mac);
	/* 5d. The runtime-11 base header: BSSID tag 15. Admitted after the
	 *     accepted association and until the successful BSS command credit
	 *     completion is recorded (join_bss_configured); refused after that
	 *     (and so after activation), before any association, after a denied
	 *     one, and beyond the cap of two; every other tag refused; tag 0
	 *     admitted after activation.
	 */
	setup(); mac.join_assoc_received = true; mac.join_assoc_status = 0; mac.join_bss_configured = false;
	script_eapol_bss(true, false, true, 15);
	run_worker();
	assert(!mac.first_error && mac.join_eapol_seen == 1 && rx_delivered == 1 && !submissions);
	mt6797_mac_join_close(&mac);
	setup(); mac.join_assoc_received = true; mac.join_assoc_status = 0; mac.join_bss_configured = true; mac.join_sta_active = true;
	script_eapol_bss(true, false, true, 15);
	run_worker();
	assert(mac.first_error == -EPROTO && !mac.join_eapol_seen);
	setup(); mac.join_assoc_received = true; mac.join_assoc_status = 0; mac.join_bss_configured = false;
	script_eapol_bss(true, true, false, 1);
	run_worker();
	assert(mac.first_error == -EPROTO && !mac.join_eapol_seen);
	setup(); script_eapol_bss(true, false, true, 15);        /* before any association */
	run_worker();
	assert(mac.first_error == -EPROTO && !mac.join_eapol_seen);
	setup(); mac.join_assoc_received = true; mac.join_assoc_status = 45; script_eapol_bss(true, false, true, 15);
	run_worker();                                             /* after a denied one */
	assert(mac.first_error == -EPROTO && !mac.join_eapol_seen);
	setup(); mac.join_assoc_received = true; mac.join_assoc_status = 0; mac.join_bss_configured = false;
	script_eapol_bss(true, false, true, 15); run_worker();
	script_eapol_bss(true, false, true, 15); run_worker();
	assert(!mac.first_error && mac.join_eapol_seen == 2);
	script_eapol_bss(true, false, true, 15); run_worker();   /* third: beyond the cap */
	assert(mac.first_error == -EPROTO && mac.join_eapol_seen == 2 && !mac.join_running);
	setup(); mac.join_assoc_received = true; mac.join_assoc_status = 0; mac.join_sta_active = true;
	script_eapol_bss(false, true, false, 0);
	run_worker();
	assert(!mac.first_error && mac.join_eapol_seen == 1);
	mt6797_mac_join_close(&mac);
	/* 5e. After the deauthentication completed the window is closed. */
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
	run_worker();                                     /* an observation does not release it */
	assert(!submissions && !mac.join_inflight && mac.join_internal);
	now_ns += 260 * NSEC_PER_MSEC;
	run_worker();
	assert(submissions == 1 && mac.join_inflight == mac.join_internal);
	mt6797_mac_join_close(&mac);
	setup(); mac.join_tx_allowed = BIT(11);
	__skb_queue_tail(&mac.join_queue, frame(OWNER_MAC80211, 11));
	mac.join_hold_until = now_ns + 250 * NSEC_PER_MSEC;
	run_worker();
	assert(submissions == 1 && mac.join_inflight && mac.join_inflight->owner == OWNER_MAC80211);
	mt6797_mac_join_close(&mac);

	/* 7. Admission of the Phase C1 association request (runtime 9 stopped at
	 *    this predicate with -EINVAL): the frame mac80211 builds with the
	 *    helper's RSN element is admitted; every perturbation is refused with
	 *    one element-refusal record; auth and deauth are unchanged.
	 */
	setup(); mac.join_tx_allowed = BIT(0);
	{
		struct sk_buff *good = assoc_frame(ASSOC_GOOD), *bad;
		unsigned int before = infos, v;

		assert(good->len == 24 + 4 + 9 + 10 + 22 && mt6797_mac_join_frame(&mac, good));
		assert(infos == before && mac.join_ssid_bytes == 7 && !memcmp(mac.join_ssid, "gemini7", 7));
		for (v = ASSOC_RSN_TKIP; v <= ASSOC_RSN_CAPAB_COUNTERS_4; v++) {
			bad = assoc_frame(v);
			before = infos;
			assert(!mt6797_mac_join_frame(&mac, bad));
			assert(infos == before + 1);
			ieee80211_free_txskb(mac.hw, bad);
		}
		/* The pinned supplicant's RSN element on a WMM-advertising AP:
		 * capabilities 0x000c, otherwise the same body, admitted silently.
		 */
		bad = assoc_frame(ASSOC_RSN_CAPAB_WMM);
		before = infos;
		assert(bad->len == good->len && mt6797_mac_join_frame(&mac, bad));
		assert(infos == before && mac.join_rsn);
		ieee80211_free_txskb(mac.hw, bad);
		bad = assoc_frame(ASSOC_NO_RSN);           /* still admitted: the runtime-8 shape */
		assert(mt6797_mac_join_frame(&mac, bad));
		ieee80211_free_txskb(mac.hw, bad);
		mac.join_tx_allowed = BIT(11);
		assert(!mt6797_mac_join_frame(&mac, good)); /* subtype not allowed: silent refusal */
		ieee80211_free_txskb(mac.hw, good);
		bad = frame(OWNER_MAC80211, 11); assert(mt6797_mac_join_frame(&mac, bad)); ieee80211_free_txskb(mac.hw, bad);
		mac.join_tx_allowed = BIT(12);
		bad = frame(OWNER_MAC80211, 12); assert(mt6797_mac_join_frame(&mac, bad)); ieee80211_free_txskb(mac.hw, bad);
	}
	mt6797_mac_join_close(&mac);

	/* 8. Phase C2 end to end on the one queue: early message 1 delivered,
	 *    association accepted, the driver's deauthentication queued and held,
	 *    message 2 admitted behind it before activation and held there,
	 *    activation, message 2 submitted as a security frame (the mac80211 skb
	 *    untouched, its status reported), message 3 delivered, message 4
	 *    submitted, a third control-port frame refused at admission, the hold
	 *    ended as the group key credit would end it, the single deauthentication
	 *    submitted and acknowledged, nothing left queued or in flight.
	 */
	setup();
	{
		struct sk_buff *m2, *m4, *extra;

		mac.join_assoc_received = true; mac.join_assoc_status = 0;
		script_eapol_bss(true, false, true, 15);          /* M1: translated, no vector, tag 15 */
		run_worker();
		assert(!mac.first_error && rx_delivered == 1 && mac.join_eapol_seen == 1);
		queue_internal_deauth();                           /* the reserved deauthentication, head of the queue */
		mac.join_hold_until = now_ns + 4000 * NSEC_PER_MSEC;
		mac.join_tx_allowed = BIT(12);
		m2 = eapol_tx_frame(121);
		mt6797_mac_tx(mac.hw, NULL, m2);                   /* admitted behind the held deauthentication */
		assert(mac.join_queue.qlen == 2 && mac.join_eapol_tx == 1 && !mac80211_frees);
		run_worker();                                      /* before activation: nothing leaves the queue */
		assert(!submissions && !mac.join_inflight && mac.join_queue.qlen == 2);
		mac.join_sta_active = true; mac.join_bss_configured = true;
		run_worker();                                      /* M2 passes the held deauthentication */
		assert(security_submissions == 1 && submissions == 1 && mac.join_inflight == m2 && mac.join_queue.qlen == 1);
		assert(mac.join_queue.head == mac.join_internal);
		script_tx_done(0);
		released = mac.join_page_debt;                     /* its pages return on the next poll */
		run_worker();
		assert(statuses == 1 && !mac.join_inflight && mac.join_internal && !mac.join_page_debt);
		script_eapol_bss(true, false, true, 0);            /* M3 after the BSS configuration: tag 0 */
		run_worker();
		assert(rx_delivered == 2 && mac.join_eapol_seen == 2);
		m4 = eapol_tx_frame(121);
		mt6797_mac_tx(mac.hw, NULL, m4);
		assert(mac.join_eapol_tx == 2);
		run_worker();
		assert(security_submissions == 2 && mac.join_inflight == m4);
		script_tx_done(0);
		released = mac.join_page_debt;
		run_worker();
		assert(statuses == 2 && !mac.join_inflight && !mac.join_page_debt);
		extra = eapol_tx_frame(121);                       /* a third: beyond the cap, back to mac80211 */
		mt6797_mac_tx(mac.hw, NULL, extra);
		assert(mac.join_eapol_tx == 2 && mac80211_frees == 1 && mac.join_queue.qlen == 1);
		mac.join_hold_until = now_ns;                      /* the group key credit ends the hold */
		run_worker();
		assert(submissions == 3 && security_submissions == 2 && mac.join_inflight == mac.join_internal);
		script_tx_done(0);
		released = mac.join_page_debt;
		idle = false;                                      /* the teardown itself is the peer fixture's */
		run_worker();
		assert(mac.join_deauth_done && !mac.join_inflight && !mac.join_internal && skb_queue_empty(&mac.join_queue));
		assert(statuses == 2 && dev_frees == 1 && rx_delivered == 2);
	}
	mt6797_mac_join_close(&mac);

	puts("join_ownership=pass; production close/worker paths; exact-once release; EAPOL delivery window and hold; C1 association request admitted; C2 one-queue handshake sequence; no device");
	return 0;
}

static void close_now(void)
{
	mt6797_mac_join_close(&mac);
}
