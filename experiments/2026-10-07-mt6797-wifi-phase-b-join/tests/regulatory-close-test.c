/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual current caller bodies; kernel, policy, HIF and idle-retirement shims.
 * No hardware ownership retirement, firmware or kernel concurrency proof.
 */
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t u8;
typedef uint64_t u64;
#define NSEC_PER_SEC 1000000000ULL
#define IS_ENABLED(x) (x)
#define CONFIG_MT6797_STATION_JOIN 1
#define CONFIG_MT6797_PASSIVE_SCAN 1
#define __maybe_unused __attribute__((unused))
#define ASSERT_RTNL() assert(rtnl)
#define dev_info(dev, ...) ((void)(dev))
#define dev_err(dev, ...) ((void)(dev))
#define wiphy_dev(w) ((void *)(w))
struct mutex { bool held; };
struct completion { unsigned int done; };
struct delayed_work { unsigned int unused; };
struct sk_buff { struct sk_buff *next; };
struct sk_buff_head { struct sk_buff *head; bool lock; };
struct ieee80211_hw;
struct wiphy { struct ieee80211_hw *hw; };
struct ieee80211_hw { void *priv; struct wiphy *wiphy; };
struct ieee80211_vif { unsigned int unused; };
struct regulatory_request { char alpha2[2]; };
struct cfg80211_scan_info { bool aborted; };
struct mt6797_hif { unsigned int submitted_debt; };
enum mt6797_normal_config_kind { MT6797_NORMAL_DOMAIN, MT6797_NORMAL_TX_CTRL };
struct mt6797_regulatory_payloads { u8 passive[4], domain[4], power[4]; };
struct mt6797_mac {
	struct mutex mutex;
	struct ieee80211_hw *hw;
	struct mt6797_hif *hif;
	struct sk_buff_head join_queue;
	struct sk_buff *join_inflight, *join_internal;
	struct delayed_work join_work;
	struct completion join_credit_done, join_frame_done, join_channel_done, join_sta_done;
	unsigned int sequence, join_queue_bytes, join_page_debt, join_data_page_debt;
	char alpha2[2];
	int first_error;
	bool closing, configured, started, scan_active;
	bool join_closed, join_scan_ready, join_peer_used, join_cleanup_done;
	bool join_running, join_retired, join_open, join_rearm_pending, join_tx_stopped;
	bool join_credit_pending, join_channel_pending, join_sta_pending;
};
static struct mt6797_mac *current;
static struct regulatory_request request = { .alpha2 = {'U', 'S'} };
static bool rtnl, notify_during_cancel;
static unsigned int sends, policies, cancels, freed, stops, regulatory_stops;
static int send_error;
static void mt6797_mac_regulatory(struct wiphy *wiphy, struct regulatory_request *request);
static void mutex_lock(struct mutex *m) { assert(!m->held); m->held = true; }
static void mutex_unlock(struct mutex *m) { assert(m->held); m->held = false; }
#define spin_lock_irqsave(l, f) do { assert(!*(l)); *(l) = true; (f) = 0; } while (0)
#define spin_unlock_irqrestore(l, f) do { (void)(f); assert(*(l)); *(l) = false; } while (0)
static struct ieee80211_hw *wiphy_to_ieee80211_hw(struct wiphy *w) { return w->hw; }
static u64 ktime_get_ns(void) { return 1000; }
static void skb_queue_head_init(struct sk_buff_head *q) { memset(q, 0, sizeof(*q)); }
static struct sk_buff *__skb_dequeue(struct sk_buff_head *q)
{
	struct sk_buff *skb = q->head;
	if (skb) { q->head = skb->next; skb->next = NULL; }
	return skb;
}
static void __skb_queue_tail(struct sk_buff_head *q, struct sk_buff *skb)
{
	struct sk_buff **p = &q->head;
	while (*p) p = &(*p)->next;
	*p = skb; skb->next = NULL;
}
static void skb_queue_splice_init(struct sk_buff_head *from, struct sk_buff_head *to)
{ assert(from->lock && !to->head); to->head = from->head; from->head = NULL; }
static void dev_kfree_skb(struct sk_buff *skb) { assert(skb); freed++; }
static void ieee80211_free_txskb(struct ieee80211_hw *hw, struct sk_buff *skb)
{ assert(hw && skb); freed++; }
static void complete_all(struct completion *c) { c->done++; }
static void ieee80211_stop_queues(struct ieee80211_hw *hw)
{ assert(hw && current->join_queue.lock); stops++; }
static void cancel_delayed_work_sync(struct delayed_work *work)
{
	assert(work == &current->join_work && !current->mutex.held && !current->join_queue.lock);
	cancels++;
	if (notify_during_cancel) {
		unsigned int before = sends;
		assert(current->join_closed);
		mt6797_mac_regulatory(current->hw->wiphy, &request);
		assert(sends == before); /* Actual close's unlock/cancel gap is fenced. */
	}
}
static int mt6797_mac_join_retire_idle_bss(struct mt6797_mac *mac) { return 0; }
static void mt6797_mac_cancel_scan(struct ieee80211_hw *hw, struct ieee80211_vif *vif)
{ assert(((struct mt6797_mac *)hw->priv)->join_closed); }
static bool mt6797_mac_finish_scan(struct mt6797_mac *mac, int *status, bool cancel)
{ return false; }
static void ieee80211_scan_completed(struct ieee80211_hw *hw, struct cfg80211_scan_info *info) {}
static int mt6797_mac_policy(struct mt6797_mac *mac, struct mt6797_regulatory_payloads *policy)
{ policies++; memset(policy, 0, sizeof(*policy)); return 0; }
static int mt6797_hif_send_config(struct mt6797_hif *hif, enum mt6797_normal_config_kind kind,
				unsigned int sequence, const u8 *payload, size_t bytes, u64 deadline)
{
	assert(current->mutex.held && rtnl);
	sends++;
	if (!send_error) hif->submitted_debt++;
	return send_error;
}
static int mt6797_mac_join_fail_stop(struct mt6797_mac *mac, int ret, unsigned int branch,
				   struct sk_buff_head *discard, struct sk_buff **internal)
{ regulatory_stops++; mac->first_error = ret; mac->closing = true; return ret; }
#include "regulatory-functions.h"

static void base(struct mt6797_mac *mac, struct ieee80211_hw *hw, struct mt6797_hif *hif)
{
	memset(mac, 0, sizeof(*mac)); memset(hif, 0, sizeof(*hif));
	mac->hw = hw; mac->hif = hif; hw->priv = mac; hw->wiphy->hw = hw;
	mac->configured = mac->started = true; mac->sequence = 5;
	mac->alpha2[0] = mac->alpha2[1] = '0';
	current = mac; rtnl = true; notify_during_cancel = false;
	sends = policies = cancels = freed = stops = regulatory_stops = 0; send_error = 0;
}
int main(void)
{
	struct wiphy wiphy;
	struct ieee80211_hw hw = { .wiphy = &wiphy };
	struct mt6797_mac mac;
	struct mt6797_hif hif;
	/* Healthy stage3 retirement without explicit close must remain benign. */
	base(&mac, &hw, &hif); mac.join_cleanup_done = mac.join_peer_used = true;
	mt6797_mac_regulatory(&wiphy, &request);
	assert(sends == 3 && policies == 1 && mac.sequence == 8 && !mac.first_error);
	/* Actual .stop publishes close before cancellation: notifier in the gap and
	 * after .stop must not reach any sender, debit or fresh sequence. */
	base(&mac, &hw, &hif); mac.join_cleanup_done = mac.join_peer_used = true;
	notify_during_cancel = true;
	mt6797_mac_stop(&hw, false);
	mt6797_mac_regulatory(&wiphy, &request);
	assert(mac.join_closed && !mac.started && cancels == 1 && stops == 1);
	assert(!sends && !policies && mac.sequence == 5 && !hif.submitted_debt);
	assert(!mac.first_error && !mac.closing); /* no invented failure on healthy close */
	base(&mac, &hw, &hif); /* no peer/cleanup: the idle explicit stop is fenced too */
	mt6797_mac_stop(&hw, false); mt6797_mac_regulatory(&wiphy, &request);
	assert(mac.join_closed && !sends && !policies && mac.sequence == 5);
	/* Unsent software frees do not refund submitted TC4/TC1 ownership. */
	base(&mac, &hw, &hif);
	struct sk_buff unsent = {0}, inflight = {0};
	mac.join_queue.head = &unsent; mac.join_queue_bytes = 30;
	mac.join_inflight = &inflight; mac.join_page_debt = 2; mac.join_data_page_debt = 3;
	hif.submitted_debt = 5; mac.first_error = -EIO;
	mt6797_mac_stop(&hw, false); mt6797_mac_regulatory(&wiphy, &request);
	assert(freed == 2 && !sends && mac.first_error == -EIO);
	assert(hif.submitted_debt == 5 && mac.join_page_debt == 2 && mac.join_data_page_debt == 3);
	/* Existing active-lifetime and first-error fences are preserved. */
	base(&mac, &hw, &hif); mac.join_scan_ready = mac.join_running = true;
	mt6797_mac_regulatory(&wiphy, &request);
	assert(regulatory_stops == 1 && !sends && mac.first_error == -ECANCELED);
	base(&mac, &hw, &hif); mac.closing = true;
	mt6797_mac_regulatory(&wiphy, &request); assert(!sends && !policies);
	base(&mac, &hw, &hif); send_error = -EIO;
	mt6797_mac_regulatory(&wiphy, &request);
	assert(sends == 1 && mac.first_error == -EIO && mac.sequence == 6);
	mt6797_mac_regulatory(&wiphy, &request); assert(sends == 1 && mac.first_error == -EIO);
	return 0;
}
