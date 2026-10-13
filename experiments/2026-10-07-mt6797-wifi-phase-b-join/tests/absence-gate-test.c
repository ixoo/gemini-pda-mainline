// SPDX-License-Identifier: GPL-2.0-only
/* Host fixture for the maintained owned-BSS absence/presence backpressure gate.
 * It compiles the ACTUAL extracted helpers (mt6797_mac_join_tx_pressure /
 * publish_tx_gate / set_absent) and the actual MT6797_JOIN_DATA_TX_QUEUE[_BYTES]
 * limits against a minimal struct holding exactly the fields they touch, with
 * skb_queue_len as a test value and ieee80211 stop/wake as counters. It verifies
 * the DECIDE+PUBLISH state machine, not kernel concurrency. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

struct sk_buff_head { int placeholder; int lock; };
struct ieee80211_hw { int placeholder; };
struct mt6797_mac {
	struct sk_buff_head join_queue;
	unsigned int join_queue_bytes;
	bool join_bss_absent, join_tx_stopped, closing;
	int first_error;
	struct ieee80211_hw *hw;
};
static unsigned int g_qlen, g_stops, g_wakes;
static unsigned int skb_queue_len(const struct sk_buff_head *q) { (void)q; return g_qlen; }
static void ieee80211_stop_queues(struct ieee80211_hw *hw) { (void)hw; g_stops++; }
static void ieee80211_wake_queues(struct ieee80211_hw *hw) { (void)hw; g_wakes++; }
#define spin_lock_irqsave(l, f) do { (void)(l); (f) = 0; } while (0)
#define spin_unlock_irqrestore(l, f) do { (void)(l); (void)(f); } while (0)

#include ABSENCE_GATE_FUNCTIONS

int main(void)
{
	struct mt6797_mac mac;
	memset(&mac, 0, sizeof(mac));

	g_qlen = MT6797_JOIN_DATA_TX_QUEUE - 2; mac.join_queue_bytes = 0;
	assert(!mt6797_mac_join_tx_pressure(&mac));
	g_qlen = MT6797_JOIN_DATA_TX_QUEUE - 1;
	assert(mt6797_mac_join_tx_pressure(&mac));
	g_qlen = 0; mac.join_queue_bytes = MT6797_JOIN_DATA_TX_QUEUE_BYTES - 1549;
	assert(mt6797_mac_join_tx_pressure(&mac));
	mac.join_queue_bytes = 0;

	/* absence stops; presence with an empty, non-closing queue wakes once; idempotent */
	g_stops = g_wakes = 0; g_qlen = 1; mac.join_tx_stopped = false;
	mt6797_mac_join_set_absent(&mac, true);
	assert(mac.join_bss_absent && mac.join_tx_stopped && g_stops == 1 && g_wakes == 0);
	mt6797_mac_join_set_absent(&mac, true);
	assert(g_stops == 1);
	g_qlen = 0;
	mt6797_mac_join_set_absent(&mac, false);
	assert(!mac.join_bss_absent && !mac.join_tx_stopped && g_wakes == 1);

	/* pressure holds the stop through presence until drained below the low mark */
	g_stops = g_wakes = 0; mac.join_tx_stopped = false; mac.join_bss_absent = false;
	g_qlen = MT6797_JOIN_DATA_TX_QUEUE - 1;
	mt6797_mac_join_publish_tx_gate(&mac);
	assert(mac.join_tx_stopped && g_stops == 1);
	g_qlen = MT6797_JOIN_DATA_TX_QUEUE / 2 + 1;
	mt6797_mac_join_publish_tx_gate(&mac);
	assert(mac.join_tx_stopped && g_wakes == 0);
	g_qlen = MT6797_JOIN_DATA_TX_QUEUE / 2;
	mt6797_mac_join_publish_tx_gate(&mac);
	assert(!mac.join_tx_stopped && g_wakes == 1);

	/* closing never wakes */
	g_stops = g_wakes = 0; mac.join_tx_stopped = true; mac.join_bss_absent = false;
	g_qlen = 0; mac.closing = true;
	mt6797_mac_join_publish_tx_gate(&mac);
	assert(mac.join_tx_stopped && g_wakes == 0);

	puts("absence-gate scenarios OK");
	return 0;
}
