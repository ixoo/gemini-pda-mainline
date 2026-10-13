/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
typedef uint64_t u64;
struct sk_buff {
	struct sk_buff *next;
	unsigned char data[2];
	unsigned int len;
	struct { struct { unsigned int flags; } control; } cb;
};
struct sk_buff_head { struct sk_buff *head; unsigned int qlen; bool lock; };
struct mt6797_mac {
	struct sk_buff_head join_queue;
	struct sk_buff *join_inflight, *join_internal;
	unsigned int join_queue_bytes, join_page_debt, join_data_page_debt, join_next_pid;
	u64 join_hold_until;
	bool join_open, join_running, join_bss_absent, join_tx_stopped, join_closed;
	bool closing, join_sta_active, join_data_phase, join_data_ended;
	int first_error;
	void *hw;
};
static struct mt6797_mac *current;
static unsigned int stops, wakes, data_ends;
#define IEEE80211_TX_CTRL_PORT_CTRL_PROTO 1U
#define IEEE80211_SKB_CB(skb) (&(skb)->cb)
#define spin_lock_irqsave(l, f) do { assert(!*(l)); *(l) = true; (f) = 0; } while (0)
#define spin_unlock_irqrestore(l, f) do { (void)(f); assert(*(l)); *(l) = false; } while (0)
static unsigned int skb_queue_len(const struct sk_buff_head *q) { return q->qlen; }
static void ieee80211_stop_queues(void *hw)
{ (void)hw; assert(current->join_queue.lock); stops++; }
static void ieee80211_wake_queues(void *hw)
{ (void)hw; assert(current->join_queue.lock); wakes++; }
static unsigned int get_unaligned_le16(const unsigned char *p) { return p[0] | p[1] << 8; }
static u64 ktime_get_ns(void) { return 1000; }
#define skb_queue_walk_safe(q, walk, tmp) \
	for ((walk) = (q)->head; (walk) && ((tmp) = (walk)->next, true); (walk) = (tmp))
static void __skb_unlink(struct sk_buff *skb, struct sk_buff_head *q)
{
	assert(q->lock);
	struct sk_buff **p = &q->head;
	while (*p != skb) { assert(*p); p = &(*p)->next; }
	*p = skb->next; skb->next = NULL; q->qlen--;
}
static void __skb_queue_tail(struct sk_buff_head *q, struct sk_buff *skb)
{
	struct sk_buff **p = &q->head;
	while (*p) p = &(*p)->next;
	*p = skb; skb->next = NULL; q->qlen++;
}
static void mt6797_mac_join_end_data(struct mt6797_mac *mac, const char *reason)
{ (void)reason; mac->join_data_ended = true; data_ends++; }
#include "queue-functions.h"

int main(void)
{
	struct mt6797_mac mac = { .join_open = true, .join_running = true, .join_sta_active = true };
	struct sk_buff deauth = { .len = 26 }, auth = { .len = 30 };
	struct sk_buff_head discard = {0};
	current = &mac;
	mac.join_internal = &deauth;
	__skb_queue_tail(&mac.join_queue, &deauth);
	__skb_queue_tail(&mac.join_queue, &auth);
	mac.join_queue_bytes = 56;
	mt6797_mac_join_set_absent(&mac, true);
	for (unsigned int i = 0; i < 5; i++) {
		assert(!select_owned(&mac, discard));
		assert(mac.join_queue.qlen == 2 && mac.join_queue_bytes == 56);
		assert(mac.join_queue.head == &deauth && deauth.next == &auth);
		assert(!mac.join_page_debt && !mac.join_inflight && !data_ends);
	}
	mt6797_mac_join_set_absent(&mac, false);
	assert(mac.join_tx_stopped && !wakes); /* shared pressure still holds */
	assert(select_owned(&mac, discard) == &deauth);
	assert(mac.join_queue_bytes == 30 && mac.join_queue.qlen == 1);
	assert(!mac.join_tx_stopped && wakes == 1 && !mac.join_page_debt);
	assert(select_owned(&mac, discard) == &auth);
	assert(!mac.join_queue_bytes && !mac.join_queue.qlen);
	/* Real credit/inflight prerequisites forbid dequeue even while present. */
	__skb_queue_tail(&mac.join_queue, &auth); mac.join_queue_bytes = 30;
	mac.join_page_debt = 1; assert(!select_owned(&mac, discard));
	mac.join_page_debt = 0; mac.join_inflight = &deauth;
	assert(!select_owned(&mac, discard)); mac.join_inflight = NULL;
	assert(select_owned(&mac, discard) == &auth);
	/* Actual close gate starts woken; a later worker/presence cannot undo it. */
	mac.join_closed = true;
	close_gate(&mac);
	assert(!mac.join_open && !mac.join_running && mac.join_tx_stopped);
	unsigned int before = wakes;
	mt6797_mac_join_set_absent(&mac, false);
	assert(mac.join_tx_stopped && wakes == before);
	/* Only the healthy rearm route, with quiescent reset gates, releases. */
	mac.join_closed = false;
	mac.join_bss_absent = true;
	rearm_gate(&mac);
	assert(!mac.join_bss_absent && !mac.join_tx_stopped && wakes == before + 1);
	assert(!mac.join_open && !mac.join_running && !mac.join_queue_bytes);
	return 0;
}
