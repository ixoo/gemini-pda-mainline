/* SPDX-License-Identifier: GPL-2.0-only */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <time.h>
#define CONFIG_MT6797_NATIVE_DELIVERY_DIAG 1
#define CONFIG_MT6797_CCMP_STABLE_EPOCH 1
#define IS_ENABLED(x) 1
#define BIT(n) (1U << (n))
enum {
	RX_FLAG_DECRYPTED = BIT(1), RX_FLAG_MMIC_STRIPPED = BIT(3),
	RX_FLAG_IV_STRIPPED = BIT(4), RX_FLAG_NO_SIGNAL_VAL = BIT(8),
	RX_FLAG_PN_VALIDATED = BIT(10), RX_FLAG_MIC_STRIPPED = BIT(21),
	RX_FLAG_ALLOW_SAME_PN = BIT(22), RX_FLAG_8023 = BIT(30),
};
#include "ccmp-rx.h"
#include "data-rx.h"
#include "native-diag.h"
#include "join-rx.h"
#include "action-frame.h"
#include "native-beacon.h"
#include "scan-wire.h"
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long long u64;
#define NSEC_PER_MSEC 1000000ULL
#define ETH_ALEN 6
#define MT6797_JOIN_ETH_MAX_BYTES 1518
#define MT6797_HIF_RX_MAX_PACKET 2352
#define MT6797_JOIN_BMC_WLAN_INDEX 2
#define MT6797_JOIN_DATA_TX_QUEUE 8
#define MT6797_JOIN_DATA_TX_QUEUE_BYTES (8 * 1550)
#define MT6797_JOIN_DATA_LAST_PID 126
#define IEEE80211_TX_CTRL_PORT_CTRL_PROTO 1U
#define WLAN_CIPHER_SUITE_CCMP 0x000fac04U
#define IEEE80211_KEY_FLAG_PAIRWISE BIT(3)
#define NL80211_BAND_5GHZ 1U
#define __aligned(n)
#define __rcu
#define min_t(t, a, b) ((t)(a) < (t)(b) ? (t)(a) : (t)(b))
static _Thread_local unsigned int bh, rcu;
struct mutex { pthread_mutex_t lock; };
static void mutex_init(struct mutex *m) { assert(!pthread_mutex_init(&m->lock, NULL)); }
static void mutex_lock(struct mutex *m)
{
	assert(!bh && !rcu); assert(!pthread_mutex_lock(&m->lock));
}
static void mutex_unlock(struct mutex *m) { assert(!pthread_mutex_unlock(&m->lock)); }
struct completion { bool done; };
static void reinit_completion(struct completion *c) { c->done = false; }
static void complete_all(struct completion *c);
static unsigned long wait_for_completion_timeout(struct completion *, unsigned long);
struct delayed_work { unsigned int scheduled, cancelled; };
static void schedule_delayed_work(struct delayed_work *w, unsigned int delay)
{
	(void)delay; w->scheduled++;
}
#define msecs_to_jiffies(ms) (ms)
static void cancel_delayed_work_sync(struct delayed_work *w) { assert(!bh && !rcu); w->cancelled++; }
static unsigned long nsecs_to_jiffies(u64 ns) { return ns / NSEC_PER_MSEC; }
static u64 now = 1000000000ULL;
static u64 ktime_get_ns(void) { return now; }
static void local_bh_disable(void) { assert(!bh); bh++; }
static void local_bh_enable(void) { assert(bh == 1); bh--; }
#define rcu_read_lock() do { assert(bh == 1); rcu++; } while (0)
#define rcu_read_unlock() do { assert(rcu == 1); rcu--; } while (0)
#define rcu_assign_pointer(p, v) ((p) = (v))
#define RCU_INIT_POINTER(p, v) ((p) = (v))
#define rcu_access_pointer(p) (p)
#define rcu_dereference_protected(p, held) ((void)(held), (p))
#define lockdep_is_held(m) ((void)(m), true)
#define spin_lock_irqsave(lock, flags) do { (void)(lock); (flags) = 0; } while (0)
#define spin_unlock_irqrestore(lock, flags) do { (void)(lock); (void)(flags); } while (0)
struct ieee80211_supported_band { int unused; };
struct ieee80211_channel { int unused; };
struct ieee80211_rate { int unused; };
struct ieee80211_vif { struct { unsigned int aid; } cfg; };
struct ieee80211_sta { u8 addr[6]; bool mlo; unsigned int valid_links; };
struct ieee80211_key_conf { unsigned int flags, cipher; int keyidx, keylen; u8 key[16], hw_key_idx; };
struct ieee80211_key_seq { struct { u8 pn[6]; } ccmp; };
enum set_key_cmd { SET_KEY, DISABLE_KEY };
enum ieee80211_sta_state { IEEE80211_STA_NOTEXIST, IEEE80211_STA_NONE,
	IEEE80211_STA_AUTH, IEEE80211_STA_ASSOC, IEEE80211_STA_AUTHORIZED };
struct wiphy { u8 perm_addr[6]; };
struct ieee80211_hw { void *priv; struct wiphy *wiphy; };
struct ieee80211_rx_status { unsigned int flag, band, freq; int signal; };
struct sk_buff {
	struct sk_buff *next; size_t len; struct ieee80211_rx_status status; u8 data[4096];
	struct { struct { struct ieee80211_key_conf *hw_key; unsigned int flags; } control; } tx;
};
struct ieee80211_tx_control { int unused; };
struct sk_buff_head { struct sk_buff *head, *tail; int lock; };
#define IEEE80211_SKB_RXCB(s) (&(s)->status)
#define IEEE80211_SKB_CB(s) (&(s)->tx)
static int skb_copy_bits(struct sk_buff *s, size_t off, void *out, size_t n)
{
	if (off > s->len || n > s->len - off) return -EINVAL;
	memcpy(out, s->data + off, n); return 0;
}
static void skb_queue_head_init(struct sk_buff_head *q) { memset(q, 0, sizeof(*q)); }
static void __skb_queue_tail(struct sk_buff_head *q, struct sk_buff *s)
{
	s->next = NULL; if (q->tail) q->tail->next = s; else q->head = s; q->tail = s;
}
static struct sk_buff *__skb_dequeue(struct sk_buff_head *q)
{
	struct sk_buff *s = q->head;
	if (s) { q->head = s->next; if (!q->head) q->tail = NULL; s->next = NULL; }
	return s;
}
static unsigned int skb_queue_len(struct sk_buff_head *q)
{
	unsigned int n = 0; for (struct sk_buff *s = q->head; s; s = s->next) n++; return n;
}
static void __skb_unlink(struct sk_buff *s, struct sk_buff_head *q)
{
	struct sk_buff *prev = NULL;
	for (struct sk_buff *i = q->head; i != s; i = i->next) { assert(i); prev = i; }
	if (prev) prev->next = s->next; else q->head = s->next;
	if (q->tail == s) q->tail = prev;
	s->next = NULL;
}
static void skb_queue_splice_init(struct sk_buff_head *from, struct sk_buff_head *to)
{
	struct sk_buff *s; while ((s = __skb_dequeue(from))) __skb_queue_tail(to, s);
}
#define skb_queue_walk_safe(q, s, tmp) \
	for ((s) = (q)->head; (s) && (((tmp) = (s)->next), true); (s) = (tmp))
static unsigned int freed, received, seed_calls, key_submits;
static bool fail_alloc;
static struct sk_buff *dev_alloc_skb(size_t n)
{
	assert(n <= 4096); return fail_alloc ? NULL : calloc(1, sizeof(struct sk_buff));
}
static void skb_put_data(struct sk_buff *s, const void *p, size_t n)
{
	assert(n <= 4096); memcpy(s->data, p, n); s->len = n;
}
static void dev_kfree_skb(struct sk_buff *s) { freed++; free(s); }
static void ieee80211_free_txskb(struct ieee80211_hw *hw, struct sk_buff *s)
{
	(void)hw; dev_kfree_skb(s);
}
#define wiphy_dev(w) (w)
static char last_log[1024];
static void dev_info(void *dev, const char *format, ...) __attribute__((format(printf, 2, 3)));
static void dev_info(void *dev, const char *format, ...)
{
	va_list args; (void)dev; va_start(args, format);
	assert(vsnprintf(last_log, sizeof(last_log), format, args) > 0); va_end(args);
}
#define dev_err dev_info
static bool ether_addr_equal(const u8 *a, const u8 *b) { return !memcmp(a, b, 6); }
static bool is_broadcast_ether_addr(const u8 *a)
{
	for (unsigned int i = 0; i < 6; i++) if (a[i] != 255) return false;
	return true;
}
struct mt6797_mac;
static int mt6797_mac_join_wait_management(struct mt6797_mac *);
static int mt6797_mac_join_wait_credit(struct mt6797_mac *);
static int mt6797_mac_join_release_channel(struct mt6797_mac *);
static void mt6797_mac_join_end_data(struct mt6797_mac *, const char *);
static int mt6797_mac_join_request_cleanup(struct mt6797_mac *);
static void mt6797_mac_join_close(struct mt6797_mac *);
static int mt6797_mac_join_add_peer(struct mt6797_mac *, struct ieee80211_vif *, struct ieee80211_sta *);
static int mt6797_mac_join_associate(struct mt6797_mac *, unsigned int);
static int mt6797_hif_join_key(void *, unsigned int, bool, bool, const u8 *, int, const u8 *, u64);
static int mt6797_hif_native_monitor(void *, unsigned int, bool, unsigned char, u64);
static void ieee80211_rx_napi(struct ieee80211_hw *, struct ieee80211_sta *, struct sk_buff *, void *);
static void ieee80211_get_key_rx_seq(struct ieee80211_key_conf *k, int tid, struct ieee80211_key_seq *s)
{
	assert(k->cipher == WLAN_CIPHER_SUITE_CCMP && tid == 0); seed_calls++;
	memset(s, 0, sizeof(*s)); s->ccmp.pn[5] = 5;
}
static bool ccmp_stable_epoch = true;
static bool native_delivery_diag;
#include "actual-ccmp-monitor.inc"
#include "parent-monitor-step.inc"
#include "actual-key-event.inc"
struct mt6797_hif_rx_result { size_t logical_bytes; unsigned int packet_type; };
#include "actual-dispatch.inc"
#include "helper-fixture.inc"
#include "native-fixture.inc"
static struct mt6797_mac *current;
static pthread_mutex_t observe_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t observe_cond = PTHREAD_COND_INITIALIZER;
static bool watching, withdrawn, disable_done;
static void complete_all(struct completion *c)
{
	c->done = true;
	if (current && c == &current->ccmp_key_done && watching) {
		assert(!pthread_mutex_lock(&observe_lock));
		withdrawn = true; pthread_cond_broadcast(&observe_cond);
		assert(!pthread_mutex_unlock(&observe_lock));
	}
}
static int submit_error, wait_mode;
struct monitor_call { unsigned int seq, enable, channel; u64 deadline; };
static struct monitor_call monitor_calls[4];
static unsigned int monitor_count;
static int monitor_error;
static int mt6797_hif_native_monitor(void *h, unsigned int seq, bool enable,
				     unsigned char channel, u64 deadline)
{
	(void)h; assert(monitor_count < 4 && channel == 40 && deadline > now);
	monitor_calls[monitor_count++] = (struct monitor_call){seq, enable, channel, deadline};
	return monitor_error;
}
enum { OWNED_FIRST, NO_EVENT, WRONG_PEER, WITHDRAW, CLEANUP, POISON };
static int mt6797_hif_join_key(void *h, unsigned int seq, bool add, bool pairwise,
			      const u8 *peer, int id, const u8 *key, u64 deadline)
{
	(void)h; (void)seq; (void)peer; (void)key; assert(add && deadline > now);
	assert((pairwise && id == 0) || (!pairwise && id == 1)); key_submits++;
	return submit_error;
}
static int mt6797_mac_join_wait_credit(struct mt6797_mac *m)
{
	m->join_credit_pending = false; m->join_page_debt = 0; return 0;
}
static int mt6797_mac_join_wait_management(struct mt6797_mac *m)
{
	m->join_inflight = NULL; return 0;
}
static int mt6797_mac_join_release_channel(struct mt6797_mac *m)
{
	m->join_data_phase = true; return 0;
}
static void mt6797_mac_join_end_data(struct mt6797_mac *m, const char *reason)
{
	m->join_data_ended = true; m->join_data_end_reason = reason;
}
static int mt6797_mac_join_request_cleanup(struct mt6797_mac *m)
{
	m->join_cleanup_requested = true; return 0;
}
static void mt6797_mac_join_close(struct mt6797_mac *m) { m->join_retired = true; }
static int mt6797_mac_join_add_peer(struct mt6797_mac *m, struct ieee80211_vif *v, struct ieee80211_sta *s)
{
	(void)m; (void)v; (void)s; return 0;
}
static int mt6797_mac_join_associate(struct mt6797_mac *m, unsigned int aid)
{
	(void)m; (void)aid; return 0;
}
static unsigned long wait_for_completion_timeout(struct completion *c, unsigned long ticks)
{
	struct mt6797_mac *m = current;
	assert(!bh && !rcu && ticks);
	assert(!pthread_mutex_trylock(&m->mutex.lock));
	if (c == &m->ccmp_key_done && !c->done) {
		if (wait_mode == OWNED_FIRST || wait_mode == WRONG_PEER) {
			memset(m->join_packet, 0, 16); m->join_packet[0] = 16;
			m->join_packet[3] = 0xe0; m->join_packet[4] = 0x24;
			memcpy(m->join_packet + 10, m->join_ap, 6);
			if (wait_mode == WRONG_PEER) m->join_packet[15] ^= 1;
			assert(owned_key_event(m, 16) == (wait_mode == OWNED_FIRST ? 0 : -EPROTO));
		} else if (wait_mode == WITHDRAW) {
			mt6797_ccmp_withdraw(m);
		}
	} else if (c == &m->ccmp_cleanup_done) {
		if (wait_mode == CLEANUP) {
			m->join_cleanup_done = true; m->join_running = false;
			m->join_key_pairwise = m->join_key_group = 2; c->done = true;
		} else if (wait_mode == POISON) {
			m->first_error = -EPROTO;
		}
	}
	assert(!pthread_mutex_unlock(&m->mutex.lock));
	return c->done;
}
static pthread_mutex_t core_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t core_cond = PTHREAD_COND_INITIALIZER;
static bool block_core, core_entered, release_core;
static void ieee80211_rx_napi(struct ieee80211_hw *hw, struct ieee80211_sta *sta,
			      struct sk_buff *skb, void *napi)
{
	assert(bh == 1 && rcu == 1 && !napi);
	assert(!pthread_mutex_trylock(&((struct mt6797_mac *)hw->priv)->mutex.lock));
	assert(!pthread_mutex_unlock(&((struct mt6797_mac *)hw->priv)->mutex.lock));
	assert(!(skb->status.flag & RX_FLAG_8023) || sta);
	assert(!pthread_mutex_lock(&core_lock));
	core_entered = true; pthread_cond_broadcast(&core_cond);
	while (block_core && !release_core) pthread_cond_wait(&core_cond, &core_lock);
	assert(!pthread_mutex_unlock(&core_lock));
	received++; dev_kfree_skb(skb);
}

static void await(pthread_cond_t *cond, pthread_mutex_t *lock, bool *condition)
{
	struct timespec until;
	assert(!clock_gettime(CLOCK_REALTIME, &until)); until.tv_sec += 3;
	while (!*condition) assert(!pthread_cond_timedwait(cond, lock, &until));
}
static void *receive_thread(void *arg)
{
	struct sk_buff *s = calloc(1, sizeof(*s)); assert(s); s->status.flag = RX_FLAG_8023;
	mutex_lock(&current->ccmp_receive_mutex);
	mt6797_ccmp_receive(current, s);
	mutex_unlock(&current->ccmp_receive_mutex);
	(void)arg; return NULL;
}
static void *disable_thread(void *arg)
{
	assert(!mt6797_ccmp_disable_key(current));
	assert(!pthread_mutex_lock(&observe_lock)); disable_done = true;
	pthread_cond_broadcast(&observe_cond); assert(!pthread_mutex_unlock(&observe_lock));
	(void)arg; return NULL;
}
static void prepare(struct mt6797_mac *m, struct ieee80211_hw *hw,
		    struct ieee80211_vif *vif, struct ieee80211_sta *sta)
{
	memset(m, 0, sizeof(*m)); current = m; hw->priv = m; m->hw = hw; m->vif = vif;
	mutex_init(&m->mutex); mutex_init(&m->ccmp_receive_mutex); skb_queue_head_init(&m->join_queue);
	memcpy(m->join_ap, sta->addr, 6);
	m->join_running = m->join_open = m->join_rsn = m->join_sta_active = m->join_bss_configured = true;
	m->join_deadline = now + 1000 * NSEC_PER_MSEC; m->native_diag_state = MT6797_ND_ACTIVE;
	seed_calls = key_submits = 0; submit_error = 0;
}
static void destroy(struct mt6797_mac *m)
{
	assert(!m->join_queue.head && !m->join_inflight);
	assert(!pthread_mutex_destroy(&m->mutex.lock));
	assert(!pthread_mutex_destroy(&m->ccmp_receive_mutex.lock));
}
static struct sk_buff *data_skb(struct ieee80211_key_conf *cookie, bool group)
{
	static const u8 llc[8] = {0xaa, 0xaa, 3, 0, 0, 0, 8, 0};
	struct sk_buff *s = calloc(1, sizeof(*s)); assert(s); s->len = 52;
	s->data[0] = 8; s->data[1] = 0x41;
	memcpy(s->data + 4, current->join_ap, 6);
	memcpy(s->data + 10, current->hw->wiphy->perm_addr, 6);
	if (group) memset(s->data + 16, 255, 6);
	else memcpy(s->data + 16, current->join_ap, 6);
	memcpy(s->data + 24, llc, 8); s->tx.control.hw_key = cookie;
	return s;
}

struct engine_point {
	unsigned int state, seq, pending, debt, engaged, total, native, bytes, queued, ended, closing;
	int error;
	u64 started, data_deadline, credit_deadline;
};
static struct engine_point point(struct mt6797_mac *m)
{
	struct engine_point p = {0};
	p.state = m->native_diag_state; p.seq = m->sequence;
	p.pending = m->join_credit_pending; p.debt = m->join_page_debt;
	p.engaged = m->native_diag_engaged; p.total = m->native_diag_total;
	p.native = m->native_diag_native; p.bytes = m->native_diag_bytes; p.queued = m->ccmp_queued;
	p.ended = m->join_data_ended; p.closing = m->closing; p.error = m->first_error;
	p.started = m->native_diag_started; p.data_deadline = m->join_data_deadline;
	p.credit_deadline = m->join_credit_deadline; return p;
}
static void engine_init(struct mt6797_mac *m, struct ieee80211_hw *hw)
{
	memset(m, 0, sizeof(*m)); m->hw = hw; m->sequence = 10;
	m->join_data_phase = true; m->join_key_pairwise = m->join_key_group = 1;
	now = 30000000000ULL; m->join_deadline = now + 20000 * NSEC_PER_MSEC;
	m->join_data_deadline = now + 15000 * NSEC_PER_MSEC;
	monitor_count = 0; monitor_error = 0; memset(monitor_calls, 0, sizeof(monitor_calls));
}
static void credit_retired(struct mt6797_mac *m)
{
	m->join_credit_pending = false; m->join_page_debt = 0;
}
static void engine_tests(struct ieee80211_hw *hw)
{
	struct mt6797_mac m;
	struct engine_point parent_trace[8], child_trace[8];
	struct monitor_call parent_calls[4];
	void (*step)(struct mt6797_mac *);

	/* Both actual functions see the same shared-ledger and command mocks. */
	ccmp_stable_epoch = false; native_delivery_diag = true;
	for (unsigned int version = 0; version < 2; version++) {
		struct engine_point *trace = version ? child_trace : parent_trace;
		step = version ? mt6797_native_diag_step : parent_monitor_step;
		engine_init(&m, hw);
		step(&m); trace[0] = point(&m);
		assert(m.native_diag_state == MT6797_ND_ENABLE_PENDING && monitor_count == 1);
		assert(m.join_page_debt == 1 && m.join_credit_pending && m.native_diag_engaged);
		step(&m); trace[1] = point(&m); /* no early ACTIVE while credit pending */
		m.join_page_debt = 0; step(&m); trace[2] = point(&m);
		assert(m.native_diag_state == MT6797_ND_ENABLE_PENDING && monitor_count == 1);
		credit_retired(&m); step(&m); trace[3] = point(&m);
		assert(m.native_diag_state == MT6797_ND_ACTIVE && m.join_data_deadline == now + 10000 * NSEC_PER_MSEC);
		m.native_diag_total = 100; m.native_diag_bytes = 10000; m.native_diag_native = 63;
		step(&m); trace[4] = point(&m); assert(m.native_diag_state == MT6797_ND_ACTIVE);
		m.native_diag_native = 64; step(&m); trace[5] = point(&m);
		assert(m.native_diag_state == MT6797_ND_DISABLE_PENDING && monitor_count == 2);
		credit_retired(&m); step(&m); trace[6] = point(&m);
		step(&m); trace[7] = point(&m);
		assert(m.native_diag_state == MT6797_ND_CLOSED && m.join_data_ended && monitor_count == 2);
		if (!version) memcpy(parent_calls, monitor_calls, sizeof(parent_calls));
		else assert(!memcmp(parent_calls, monitor_calls, sizeof(parent_calls)));
	}
	assert(!memcmp(parent_trace, child_trace, sizeof(parent_trace)));
	assert(parent_calls[0].seq == 10 && parent_calls[0].enable == 1 &&
	       parent_calls[1].seq == 11 && parent_calls[1].enable == 0);
	/* CCMP arm alone selects SAME admitted commands/ledger, separate64 count. */
	ccmp_stable_epoch = true; native_delivery_diag = false; engine_init(&m, hw);
	mt6797_native_diag_step(&m); credit_retired(&m); mt6797_native_diag_step(&m);
	m.ccmp_queued = 63; m.native_diag_total = 100; m.native_diag_bytes = 10000;
	mt6797_native_diag_step(&m); assert(m.native_diag_state == MT6797_ND_ACTIVE && monitor_count == 1);
	m.ccmp_queued = 64; mt6797_native_diag_step(&m);
	assert(m.native_diag_state == MT6797_ND_DISABLE_PENDING && !m.native_diag_native &&
	       m.join_page_debt == 1 && m.join_credit_pending && monitor_count == 2);
	credit_retired(&m); mt6797_native_diag_step(&m);
	assert(m.native_diag_state == MT6797_ND_CLOSED && !m.native_diag_native);
	assert(!memcmp(parent_calls, monitor_calls, sizeof(parent_calls)));
	/* Owed TX/credit must retire before disable; sampled stop fences ALL TX. */
	engine_init(&m, hw); mt6797_native_diag_step(&m);
	credit_retired(&m); mt6797_native_diag_step(&m); m.ccmp_queued = 64;
	{
		struct sk_buff owed = {0};
		m.join_inflight = &owed;
		mt6797_native_diag_step(&m);
		assert(m.native_diag_state == MT6797_ND_ACTIVE && monitor_count == 1);
		assert(mt6797_native_diag_pre_read(&m) == 0 && m.native_diag_sample_done);
		assert(mt6797_native_diag_tx_fenced(&m));
		m.native_diag_retire_reads = MT6797_NATIVE_DIAG_RETIRE_READS;
		assert(mt6797_native_diag_pre_read(&m) == -ETIMEDOUT);
		m.join_inflight = NULL; m.native_diag_retire_reads = 0;
		mt6797_native_diag_step(&m);
		assert(m.native_diag_state == MT6797_ND_DISABLE_PENDING && monitor_count == 2);
		assert(mt6797_native_diag_pre_read(&m) == 1 && mt6797_native_diag_tx_fenced(&m));
		credit_retired(&m); mt6797_native_diag_step(&m);
		assert(m.native_diag_state == MT6797_ND_CLOSED && !mt6797_native_diag_tx_fenced(&m));
	}
	/* All-RX, prospective bytes, wall and lower DATA deadline still end the window. */
	for (unsigned int boundary = 0; boundary < 4; boundary++) {
		engine_init(&m, hw); if (boundary == 3) m.join_data_deadline = now + 500 * NSEC_PER_MSEC;
		mt6797_native_diag_step(&m); credit_retired(&m); mt6797_native_diag_step(&m);
		m.ccmp_queued = 63;
		if (boundary == 0) m.native_diag_total = 512;
		if (boundary == 1) m.native_diag_bytes = MT6797_NATIVE_DIAG_BYTES_MAX - MT6797_HIF_RX_MAX_PACKET + 1;
		if (boundary == 2) now += 10000 * NSEC_PER_MSEC;
		if (boundary == 3) now += 500 * NSEC_PER_MSEC;
		if (boundary < 3) assert(mt6797_native_diag_pre_read(&m) == 1);
		mt6797_native_diag_step(&m);
		assert(m.native_diag_state == MT6797_ND_DISABLE_PENDING && monitor_count == 2 && !m.native_diag_native);
	}
	/* Ambiguous enable/disable and pending-credit timeout never cause retry. */
	for (unsigned int failure = 0; failure < 4; failure++) {
		engine_init(&m, hw);
		if (failure == 0) monitor_error = -EIO;
		mt6797_native_diag_step(&m);
		if (failure == 1) now = m.join_credit_deadline;
		if (failure >= 2) {
			credit_retired(&m); mt6797_native_diag_step(&m); m.ccmp_queued = 64;
			if (failure == 2) monitor_error = -EPROTO;
			mt6797_native_diag_step(&m);
			if (failure == 3) now = m.join_credit_deadline;
		}
		mt6797_native_diag_step(&m);
		assert(m.closing && m.first_error && m.native_diag_state == MT6797_ND_CLOSED);
		unsigned int calls = monitor_count, seq = m.sequence;
		mt6797_native_diag_step(&m); assert(monitor_count == calls && m.sequence == seq);
	}
	ccmp_stable_epoch = false; native_delivery_diag = false; engine_init(&m, hw);
	mt6797_native_diag_step(&m); assert(!monitor_count && m.native_diag_state == MT6797_ND_IDLE);
	ccmp_stable_epoch = true; native_delivery_diag = false;
	puts("actual monitor engine: PASS native parent/child trace, CCMP-only arm/63->64, ledger/boundaries/no-radio");
}

int main(void)
{
	struct mt6797_mac m = {0};
	struct wiphy w = {{2, 0, 0, 0, 0, 1}};
	struct ieee80211_hw hw = {&m, &w};
	struct ieee80211_vif vif = {0};
	struct ieee80211_sta sta = {{2, 0, 0, 0, 0, 2}, false, 0};
	struct ieee80211_key_conf ptk = {IEEE80211_KEY_FLAG_PAIRWISE, WLAN_CIPHER_SUITE_CCMP, 0, 16, {0}, 0};
	struct ieee80211_key_conf gtk = {0, WLAN_CIPHER_SUITE_CCMP, 1, 16, {0}, 0};
	struct sk_buff *skb;
	u8 packet[512];
	struct mt6797_hif_rx_result rx;
	struct sk_buff_head q;
	struct mt6797_ccmp_rx_context before;

	engine_tests(&hw);
	prepare(&m, &hw, &vif, &sta);
	assert(!mt6797_mac_set_key(&hw, SET_KEY, &vif, &sta, &ptk));
	assert(seed_calls == 1 && key_submits == 1 && ptk.hw_key_idx == 1);
	assert(m.ccmp_rx.active && m.ccmp_rx.seeded && !m.ccmp_rx.authorized && m.ccmp_rx.pn[5] == 5);
	assert(!mt6797_mac_set_key(&hw, SET_KEY, &vif, NULL, &gtk));
	assert(gtk.hw_key_idx == 2 && m.ccmp_ptk == &ptk && m.ccmp_gtk == &gtk);
	{
		struct ieee80211_sta other = sta;
		assert(mt6797_mac_sta_state(&hw, &vif, &other, IEEE80211_STA_ASSOC,
					   IEEE80211_STA_AUTHORIZED) == -EOPNOTSUPP);
		assert(!m.ccmp_rx.authorized && m.ccmp_sta == &sta);
	}
	assert(!mt6797_mac_sta_state(&hw, &vif, &sta, IEEE80211_STA_ASSOC, IEEE80211_STA_AUTHORIZED));
	assert(m.ccmp_rx.authorized && m.ccmp_sta == &sta && m.ccmp_tx_ready);
	mt6797_mac_sta_set_decap_offload(&hw, &vif, &sta, true);
	assert(mt6797_ccmp_rx_ready(&m));
	offline_helper_tests();
	m.native_diag_started = now;
	m.native_diag_engaged = true;
	rx.logical_bytes = frame(packet, 9, false, 6);
	rx.packet_type = mt6797_join_le16(packet + 2);
	memcpy(m.join_packet, packet, rx.logical_bytes); skb_queue_head_init(&q);
	assert(!dispatch(&m, &rx, &q) && q.head && !q.head->next);
	assert(m.ccmp_queued == 1 && !m.native_diag_native && m.ccmp_rx.pn[5] == 6);
	assert(q.head->status.flag == (RX_FLAG_8023 | RX_FLAG_DECRYPTED | RX_FLAG_IV_STRIPPED |
	       RX_FLAG_MIC_STRIPPED | RX_FLAG_PN_VALIDATED | RX_FLAG_NO_SIGNAL_VAL));
	assert(q.head->len == rx.logical_bytes - 48 && !memcmp(q.head->data, packet + 48, q.head->len));
	dev_kfree_skb(__skb_dequeue(&q));
	before = m.ccmp_rx;
	assert(!dispatch(&m, &rx, &q) && !q.head && m.ccmp_queued == 1);
	assert(!memcmp(&before, &m.ccmp_rx, sizeof(before))); /* replay */
	rx.logical_bytes = frame(packet, 8, false, 7); /* G1 absent, no legacy fallback */
	rx.packet_type = mt6797_join_le16(packet + 2); memcpy(m.join_packet, packet, rx.logical_bytes);
	assert(!dispatch(&m, &rx, &q) && !q.head && m.ccmp_queued == 1);
	assert(!memcmp(&before, &m.ccmp_rx, sizeof(before)));
	rx.logical_bytes = frame(packet, 9, false, 7); rx.packet_type = mt6797_join_le16(packet + 2);
	memcpy(m.join_packet, packet, rx.logical_bytes); fail_alloc = true;
	assert(dispatch(&m, &rx, &q) == -ENOMEM && !q.head && m.ccmp_queued == 1);
	assert(!memcmp(&before, &m.ccmp_rx, sizeof(before))); fail_alloc = false;
	m.ccmp_queued = 64;
	assert(mt6797_native_diag_pre_read(&m) == 1 && m.native_diag_sample_done);
	m.ccmp_queued = 1; m.native_diag_sample_done = false;
	m.native_diag_total = 511; before = m.ccmp_rx;
	assert(!dispatch(&m, &rx, &q) && !q.head && m.native_diag_total == 512);
	assert(m.ccmp_queued == 1 && !memcmp(&before, &m.ccmp_rx, sizeof(before)));
	m.native_diag_total = 0;
	/* Actual .tx uses current PTK even for Ethernet broadcast carried ToDS. */
	skb = data_skb(&ptk, true); mt6797_mac_tx(&hw, NULL, skb);
	assert(m.join_queue.head == skb && m.join_data_tx_queued == 1);
	assert(skb->data[1] == 0x41 && ether_addr_equal(skb->data + 4, sta.addr));
	mt6797_mac_tx(&hw, NULL, data_skb(&gtk, false));
	assert(skb_queue_len(&m.join_queue) == 1);
	{
		struct ieee80211_key_conf *dead = malloc(sizeof(*dead)); assert(dead);
		struct sk_buff *wrong = data_skb(dead, false); free(dead);
		mt6797_mac_tx(&hw, NULL, wrong); /* cookie comparison, no dereference */
		assert(skb_queue_len(&m.join_queue) == 1);
	}
	skb = data_skb(&ptk, false); memset(skb->data + 24, 0, 8); /* software IV, not LLC */
	mt6797_mac_tx(&hw, NULL, skb); assert(skb_queue_len(&m.join_queue) == 1);
	skb = calloc(1, sizeof(*skb)); assert(skb); skb->status.flag = RX_FLAG_8023;
	mutex_lock(&m.ccmp_receive_mutex); mt6797_ccmp_receive(&m, skb); mutex_unlock(&m.ccmp_receive_mutex);
	assert(received == 1 && !bh && !rcu);
	mt6797_mac_sta_set_decap_offload(&hw, &vif, &sta, false);
	skb = calloc(1, sizeof(*skb)); assert(skb); skb->status.flag = RX_FLAG_8023;
	mutex_lock(&m.ccmp_receive_mutex); mt6797_ccmp_receive(&m, skb); mutex_unlock(&m.ccmp_receive_mutex);
	assert(received == 1);
	wait_mode = CLEANUP;
	assert(!mt6797_mac_set_key(&hw, DISABLE_KEY, &vif, &sta, &ptk));
	assert(m.ccmp_closed && !m.ccmp_rx.active && !m.ccmp_sta && !m.ccmp_ptk && !m.ccmp_gtk);
	assert(!m.ccmp_tx_ready && m.join_key_pairwise == 2 && m.join_work.cancelled == 1);
	assert(mt6797_mac_set_key(&hw, SET_KEY, &vif, &sta, &ptk) == -EOPNOTSUPP);
	assert(m.ccmp_rx.pn[5] == 6 && seed_calls == 1);
	destroy(&m);
	/* CONFIG present but new arm false: the original native MPDU/counters/
	 * flags still behave exactly, rather than entering the Ethernet path. */
	prepare(&m, &hw, &vif, &sta); ccmp_stable_epoch = false;
	m.native_diag_engaged = true; m.native_diag_started = now; m.join_data_phase = true;
	{
		size_t offset;
		native_layout_tests();
		rx.logical_bytes = build_g(packet, 7, false, false, &offset);
		rx.packet_type = mt6797_join_le16(packet + 2); memcpy(m.join_packet, packet, rx.logical_bytes);
		skb_queue_head_init(&q); assert(!dispatch(&m, &rx, &q) && q.head);
		assert(m.native_diag_native == 1 && !m.ccmp_queued &&
		       q.head->status.flag == mt6797_native_diag_ordinary_flags(0));
		assert(!(q.head->status.flag & mt6797_native_diag_crypto_bypass_mask()));
		dev_kfree_skb(__skb_dequeue(&q));
	}
	ccmp_stable_epoch = true; destroy(&m);
	/* Missing/wrong/withdrawn activation event cannot publish key/context. */
	for (int mode = NO_EVENT; mode <= WITHDRAW; mode++) {
		prepare(&m, &hw, &vif, &sta); wait_mode = mode; ptk.hw_key_idx = 0;
		assert(mt6797_mac_set_key(&hw, SET_KEY, &vif, &sta, &ptk) < 0);
		assert(!m.ccmp_rx.active && !m.ccmp_ptk && !ptk.hw_key_idx && m.ccmp_closed);
		destroy(&m);
	}
	prepare(&m, &hw, &vif, &sta); submit_error = -EPROTO; wait_mode = OWNED_FIRST;
	ptk.hw_key_idx = 0;
	assert(mt6797_mac_set_key(&hw, SET_KEY, &vif, &sta, &ptk) == -EPROTO);
	assert(!m.ccmp_ptk && !m.ccmp_rx.active && !ptk.hw_key_idx); destroy(&m);
	/* HIF poison: LOCAL disable completes, but no command/credit retirement. */
	prepare(&m, &hw, &vif, &sta); wait_mode = POISON;
	m.ccmp_ptk = &ptk; m.ccmp_rx.active = true;
	assert(!mt6797_ccmp_disable_key(&m));
	assert(m.first_error == -EPROTO && m.ccmp_closed && !m.ccmp_rx.active);
	assert(strstr(last_log, "removal_command_credit=0 status=-71")); destroy(&m);
	/* Actual receive pauses inside the core mock; withdrawal must wait for the
	 * batch before callback completion. The pause is a host-test barrier, not
	 * a permitted sleeping kernel RX operation. */
	prepare(&m, &hw, &vif, &sta); wait_mode = OWNED_FIRST;
	assert(!mt6797_mac_set_key(&hw, SET_KEY, &vif, &sta, &ptk));
	assert(!mt6797_mac_set_key(&hw, SET_KEY, &vif, NULL, &gtk));
	assert(!mt6797_mac_sta_state(&hw, &vif, &sta, IEEE80211_STA_ASSOC, IEEE80211_STA_AUTHORIZED));
	mt6797_mac_sta_set_decap_offload(&hw, &vif, &sta, true);
	{
		pthread_t rx_thread, key_thread;
		block_core = watching = true; core_entered = release_core = withdrawn = disable_done = false;
		assert(!pthread_create(&rx_thread, NULL, receive_thread, NULL));
		assert(!pthread_mutex_lock(&core_lock)); await(&core_cond, &core_lock, &core_entered);
		assert(!pthread_mutex_unlock(&core_lock)); wait_mode = CLEANUP;
		assert(!pthread_create(&key_thread, NULL, disable_thread, NULL));
		assert(!pthread_mutex_lock(&observe_lock)); await(&observe_cond, &observe_lock, &withdrawn);
		assert(!disable_done); assert(!pthread_mutex_unlock(&observe_lock));
		mutex_lock(&m.mutex); assert(!m.ccmp_sta && !m.ccmp_ptk && !m.ccmp_tx_ready); mutex_unlock(&m.mutex);
		assert(!pthread_mutex_lock(&core_lock)); release_core = true; pthread_cond_broadcast(&core_cond);
		assert(!pthread_mutex_unlock(&core_lock));
		assert(!pthread_join(rx_thread, NULL) && !pthread_join(key_thread, NULL));
		assert(disable_done && m.ccmp_closed && m.join_work.cancelled == 1);
		block_core = watching = false;
	}
	destroy(&m);
	puts("CCMP actual callbacks: PASS first-event activation/seed/GTK-withhold/pubsta/BH-RCU/withdrawal/no-reuse");
	return 0;
}
