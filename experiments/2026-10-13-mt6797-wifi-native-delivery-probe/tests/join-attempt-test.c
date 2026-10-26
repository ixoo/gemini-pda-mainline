/* SPDX-License-Identifier: GPL-2.0-only */
/* The actual mgd_prepare_tx, the actual management admission of mac_tx and
 * the actual join frame validator: a lost association response, mac80211's
 * retry, and the bound (0304). Built by run-join-attempt-test.py, once on the
 * parent (-DPARENT: boot AA2's stop reproduced) and once on the change. No HIF.
 */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include "join-events.h"
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned long long u64;
#define BIT(n) (1U << (n))
#define NSEC_PER_MSEC 1000000ULL
#define min(a, b) ((a) < (b) ? (a) : (b))
#define IS_ENABLED(x) 1
#define dev_info(d, ...) do { if (0) printf(__VA_ARGS__); } while (0)
#define wiphy_dev(w) ((void *)(w))
#define get_unaligned_le16 mt6797_join_le16
#define WLAN_EID_SSID 0
#define WLAN_EID_HT_CAPABILITY 45
#define WLAN_EID_RSN 48
#define WLAN_EID_MOBILITY_DOMAIN 54
#define WLAN_EID_FAST_BSS_TRANSITION 55
#define WLAN_EID_VHT_CAPABILITY 191
#define WLAN_EID_VENDOR_SPECIFIC 221
#define WLAN_HT_CAP_SM_PS_DISABLED 3
#define IEEE80211_HT_CAP_SM_PS_SHIFT 2
#define IEEE80211_HT_CAP_SM_PS 0x000c
#define IEEE80211_HT_MAX_AMPDU_8K 0
#define IEEE80211_HT_MPDU_DENSITY_8 6
#define IEEE80211_HT_AMPDU_PARM_DENSITY_SHIFT 2
#define IEEE80211_HT_MCS_TX_DEFINED 0x01
#define IEEE80211_STYPE_ASSOC_REQ 0x0000
#define IEEE80211_STYPE_DISASSOC 0x00a0
#define IEEE80211_STYPE_AUTH 0x00b0
#define IEEE80211_STYPE_DEAUTH 0x00c0

static u64 now;
static u64 ktime_get_ns(void) { return now; }
struct mutex { int held; };
static void mutex_lock(struct mutex *m) { assert(!m->held); m->held = 1; }
static void mutex_unlock(struct mutex *m) { assert(m->held); m->held = 0; }
#define spin_lock_irqsave(l, f) do { (void)(l); (f) = 0; } while (0)
#define spin_unlock_irqrestore(l, f) do { (void)(l); (void)(f); } while (0)
struct sk_buff { unsigned int len; u8 *data; };
struct sk_buff_head { struct sk_buff *q[8]; unsigned int len; int lock; };
static int skb_copy_bits(const struct sk_buff *s, int o, void *to, int n)
{
	if ((unsigned int)(o + n) > s->len)
		return -EFAULT;
	memcpy(to, s->data + o, n);
	return 0;
}
static unsigned int skb_queue_len(const struct sk_buff_head *h) { return h->len; }
static void __skb_queue_tail(struct sk_buff_head *h, struct sk_buff *s) { h->q[h->len++] = s; }
static bool ether_addr_equal(const u8 *a, const u8 *b) { return !memcmp(a, b, 6); }
struct delayed_work { int scheduled; };
static void schedule_delayed_work(struct delayed_work *w, int d) { (void)d; w->scheduled++; }
struct wiphy { u8 perm_addr[6]; };
struct ieee80211_hw { void *priv; struct wiphy *wiphy; };
struct ieee80211_vif { unsigned int valid_links; };
struct ieee80211_prep_tx_info { u16 subtype; bool success; int link_id; };

struct mt6797_mac {
	struct mutex mutex;
	struct ieee80211_hw *hw;
	struct ieee80211_vif *vif;
	bool join_cleanup_requested, join_cleanup_done, join_data_phase, join_data_ended;
	bool join_peer_ready, join_running, join_retired, closing;
	bool join_channel_valid, join_bss_valid, join_channel_granted;
	bool join_authenticated, join_auth_received, join_assoc_received;
	bool join_open, join_rsn, join_wmm_requested, join_ht_requested;
	int first_error, ended;
	u64 join_deadline, join_grant_deadline;
	struct sk_buff_head join_queue;
	unsigned int join_queue_bytes, join_seen, join_tx_allowed, join_rx_allowed;
	unsigned int join_auth_attempts, join_assoc_attempts;
	u8 join_ap[6], join_ssid[32];
	unsigned int join_ssid_bytes;
	struct delayed_work join_work;
};
static void mt6797_mac_join_end_data(struct mt6797_mac *mac, const char *why)
{
	(void)why;
	mac->ended++;
}
#include "join-attempt-functions.inc"

static const u8 ap[6] = { 2, 0, 0, 0, 0, 1 }, own[6] = { 2, 0, 0, 0, 0, 2 };
static struct wiphy wiphy;
static struct ieee80211_hw hw;
static struct ieee80211_vif vif;
static struct mt6797_mac m;
static u8 frames[8][128];
static struct sk_buff skbs[8];
static unsigned int built;

static void start(void)
{
	memset(&m, 0, sizeof(m));
	memcpy(wiphy.perm_addr, own, 6);
	hw.priv = &m; hw.wiphy = &wiphy; m.hw = &hw; m.vif = &vif;
	memcpy(m.join_ap, ap, 6);
	now = 10000 * NSEC_PER_MSEC;
	m.join_peer_ready = m.join_running = true;
	m.join_channel_valid = m.join_bss_valid = m.join_channel_granted = true;
	m.join_deadline = now + 10000 * NSEC_PER_MSEC;
	m.join_grant_deadline = now + 60000 * NSEC_PER_MSEC;
	built = 0;
}

static struct sk_buff *frame(unsigned int subtype)
{
	static const u8 rsn[] = { 48, 20, 1, 0, 0, 0x0f, 0xac, 4, 1, 0, 0, 0x0f, 0xac, 4,
				  1, 0, 0, 0x0f, 0xac, 2, 0, 0 };
	static const u8 wmm[] = { 221, 7, 0, 0x50, 0xf2, 2, 0, 1, 0 };
	u8 *f = frames[built];
	size_t n = 24;

	memset(f, 0, 128);
	f[0] = subtype << 4;
	memcpy(f + 4, ap, 6); memcpy(f + 10, own, 6); memcpy(f + 16, ap, 6);
	f[22] = (built << 4) & 0xf0;
	if (subtype == 11) {
		f[26] = 1;
		n = 30;
	} else if (subtype == 12) {
		f[24] = 3;
		n = 26;
	} else {
		f[24] = 0x11; f[26] = 10; n = 28;
		f[n++] = 0; f[n++] = 4; memcpy(f + n, "test", 4); n += 4;
		memcpy(f + n, rsn, sizeof(rsn)); n += sizeof(rsn);
		memcpy(f + n, wmm, sizeof(wmm)); n += sizeof(wmm);
		f[n] = 45; f[n + 1] = 26; f[n + 2] = 0x0c; f[n + 4] = 0x18; f[n + 5] = 0xff;
		f[n + 17] = 0x01; n += 28;
	}
	skbs[built].data = f; skbs[built].len = n;
	return &skbs[built++];
}

/* mac80211's prepare, its frame through mac_tx, and the worker's dequeue and
 * validation; returns whether the frame reached the validated queue head.
 */
static bool attempt(u16 stype)
{
	struct ieee80211_prep_tx_info info = { .subtype = stype };
	struct sk_buff *s = frame(stype >> 4);

	mt6797_mac_mgd_prepare_tx(&hw, &vif, &info);
	if (!queue(&hw, s))
		return false;
	assert(m.join_queue.len == 1 && m.join_queue.q[0] == s);
	m.join_queue.len = 0;
	m.join_queue_bytes = 0;
	return mt6797_mac_join_frame(&m, s);
}

static void refused_closed(void)
{
	assert(!m.join_open && !m.join_tx_allowed);
	assert(m.first_error == -EOPNOTSUPP && m.closing);
}

static void authenticated(void)
{
	assert(attempt(IEEE80211_STYPE_AUTH));
	m.join_authenticated = m.join_auth_received = true;
}

int main(void)
{
	/* The sequence of boot AA2: auth, association request, no response,
	 * mac80211's second try after its timeout.
	 */
	start(); authenticated();
	assert(attempt(IEEE80211_STYPE_ASSOC_REQ));
	assert(m.join_wmm_requested && m.join_ht_requested && !m.closing);
	now += 200 * NSEC_PER_MSEC;
#ifdef PARENT
	assert(!attempt(IEEE80211_STYPE_ASSOC_REQ));
	refused_closed();
	/* and the parent's validator refuses the same request a second time */
	start(); authenticated();
	assert(attempt(IEEE80211_STYPE_ASSOC_REQ));
	{
		struct sk_buff *s = frame(0);

		assert(!mt6797_mac_join_frame(&m, s));
	}
	printf("parent: the association retry fails closed (-EOPNOTSUPP), boot AA2's stop reproduced\n");
#else
	assert(attempt(IEEE80211_STYPE_ASSOC_REQ));
	assert(m.join_assoc_attempts == 2 && m.join_auth_attempts == 1);
	assert(m.join_running && !m.closing && !m.first_error && m.join_open);
	assert(m.join_wmm_requested && m.join_ht_requested);
	assert(m.join_rx_allowed == (BIT(1) | BIT(10) | BIT(12)));
	/* the third try fails closed, and its frame is not queued */
	now += 200 * NSEC_PER_MSEC;
	assert(!attempt(IEEE80211_STYPE_ASSOC_REQ));
	refused_closed();
	assert(m.join_assoc_attempts == 2);

	/* authentication: two attempts, the third fails closed */
	start();
	assert(attempt(IEEE80211_STYPE_AUTH) && attempt(IEEE80211_STYPE_AUTH));
	assert(!m.closing && m.join_auth_attempts == 2);
	assert(!attempt(IEEE80211_STYPE_AUTH));
	refused_closed();

	/* the window still holds a retry: 850 ms before the join deadline */
	start(); authenticated();
	assert(attempt(IEEE80211_STYPE_ASSOC_REQ));
	now = m.join_deadline - 850 * NSEC_PER_MSEC;
	assert(!attempt(IEEE80211_STYPE_ASSOC_REQ));
	refused_closed();
	/* ... and the grant deadline */
	start(); authenticated();
	assert(attempt(IEEE80211_STYPE_ASSOC_REQ));
	m.join_grant_deadline = now + 850 * NSEC_PER_MSEC;
	assert(!attempt(IEEE80211_STYPE_ASSOC_REQ));
	refused_closed();
	/* no retry once a response was received */
	start(); authenticated();
	assert(attempt(IEEE80211_STYPE_ASSOC_REQ));
	m.join_assoc_received = true;
	assert(!attempt(IEEE80211_STYPE_ASSOC_REQ));
	refused_closed();
	/* no authentication retry once authenticated */
	start(); authenticated();
	assert(!attempt(IEEE80211_STYPE_AUTH));
	refused_closed();

	/* every other subtype stays one frame per lifetime */
	start();
	m.join_open = true;
	m.join_tx_allowed = BIT(12);
	assert(queue(&hw, frame(12)));
	m.join_queue.len = 0;
	m.join_queue_bytes = 0;
	assert(!queue(&hw, frame(12)) && m.join_seen == BIT(12));
	assert(!m.join_auth_attempts && !m.join_assoc_attempts);
	printf("join attempts: PASS; a second authentication and association try admitted inside the window, the third and every other refusal fail closed, other subtypes one per lifetime\n");
#endif
	return 0;
}
