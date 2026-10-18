/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual grant-event block feeds the actual data-opening function. No HIF. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include "join-events.h"
typedef unsigned long long u64;
typedef unsigned int u32;
#define NSEC_PER_MSEC 1000000ULL
#define min_t(t, a, b) ((t)(a) < (t)(b) ? (t)(a) : (t)(b))
#define min(a, b) ((a) < (b) ? (a) : (b))
#define IS_ENABLED(x) 1
#define dev_info(d, ...) do { if (0) printf(__VA_ARGS__); } while (0)
struct completion { bool done; };
static void complete_all(struct completion *c) { c->done = true; }
static u64 now;
static u64 ktime_get_ns(void) { return now; }
static bool ccmp_stable_epoch = true;
struct mt6797_mac {
 bool join_channel_pending, join_channel_granted, join_channel_released;
 bool join_data_phase, join_data_ended, join_credit_pending;
 unsigned int join_channel_token, join_requested_ms, join_page_debt;
 u64 join_grant_deadline, join_deadline, join_data_started, join_data_deadline, join_hold_until;
 unsigned char join_packet[24];
 struct completion join_channel_done;
 struct { bool active; } ccmp_observation;
};
#include "grant-horizon-functions.inc"

static void prepare(struct mt6797_mac *m, unsigned int interval)
{
 memset(m, 0, sizeof(*m)); now = 1000000000ULL;
 m->join_channel_pending = true; m->join_channel_token = 7; m->join_requested_ms = 65000;
 m->join_deadline = now + 10000 * NSEC_PER_MSEC;
 m->join_packet[0] = 24; m->join_packet[3] = 0xe0; m->join_packet[4] = 0x10;
 m->join_packet[9] = 7; m->join_packet[11] = 40; m->join_packet[13] = 2;
 for (unsigned int i = 0; i < 4; i++) m->join_packet[20 + i] = interval >> (8 * i);
}

static void selected_window(long long setup_delay_ns, int expected)
{
 struct mt6797_mac m, before;
 prepare(&m, 65000);
 assert(!successor_grant_event(&m, 24));
 assert(m.join_channel_granted && !m.join_channel_pending && m.join_channel_done.done);
 assert(m.join_grant_deadline == now + 65000 * NSEC_PER_MSEC);
 assert(m.join_deadline == now + 10000 * NSEC_PER_MSEC);
 now += setup_delay_ns; before = m;
 assert(mt6797_mac_join_release_channel(&m) == expected);
 if (expected) { assert(!memcmp(&m, &before, sizeof(m))); return; }
 assert(m.join_data_phase && m.ccmp_observation.active);
 assert(m.join_data_deadline == now + 60000 * NSEC_PER_MSEC);
 assert(m.join_deadline == m.join_data_deadline + 5000 * NSEC_PER_MSEC);
 assert(m.join_grant_deadline - m.join_data_deadline >= 2500 * NSEC_PER_MSEC);
}

int main(void)
{
 struct mt6797_mac m, before;
 /* The parent reproduces GTK1's exact remaining value without manually
  * inserting a grant deadline. Key/setup time remains independently bounded.
  */
 prepare(&m, 65000); assert(!parent_grant_event(&m, 24));
 now += 534 * NSEC_PER_MSEC;
 assert((m.join_grant_deadline - now) / NSEC_PER_MSEC == 9466);
 before = m; assert(mt6797_mac_join_release_channel(&m) == -ERANGE);
 assert(!memcmp(&m, &before, sizeof(m)));
 selected_window(534 * NSEC_PER_MSEC, 0);
 selected_window(2500 * NSEC_PER_MSEC - 1, 0);
 selected_window(2500 * NSEC_PER_MSEC, 0);
 selected_window(2500 * NSEC_PER_MSEC + 1, -ERANGE);
 selected_window(65000 * NSEC_PER_MSEC, -ERANGE);

 /* The early necessary condition rejects short grants before successful
  * channel completion, retaining ownership. It cannot promise that setup
  * consumes no time: the late test remains authoritative.
  */
 for (unsigned int interval = 1; interval <= 65000; interval++) {
  prepare(&m, interval);
  int rc = successor_grant_event(&m, 24);
  assert(rc == (interval < 62500 ? -ERANGE : 0));
  assert(m.join_channel_granted && !m.join_channel_pending && !m.join_data_phase);
  assert(m.join_grant_deadline == now + interval * NSEC_PER_MSEC);
  assert(m.join_deadline == now + 10000 * NSEC_PER_MSEC);
  assert(m.join_channel_done.done == (interval >= 62500));
 }
 for (unsigned int bad = 0; bad < 13; bad++) {
  prepare(&m, bad == 0 ? 0 : bad == 1 ? 65001 : 65000);
  if (bad >= 2 && bad <= 11) m.join_packet[8 + bad - 2] ^= 1;
  if (bad == 12) m.join_channel_pending = false;
  before = m; assert(successor_grant_event(&m, 24) == -EPROTO);
  assert(!memcmp(&m, &before, sizeof(m)));
 }
 prepare(&m, 65000); before = m;
 for (size_t n = 0; n < 24; n++) {
  assert(successor_grant_event(&m, n) == -EPROTO);
  assert(!memcmp(&m, &before, sizeof(m)));
 }
 /* The event does not extend setup; actual key callbacks separately test
  * expiry during credit acquisition. The late window remains impossible
  * after a genuinely short grant even if its early error were ignored.
  */
 prepare(&m, 62499); assert(successor_grant_event(&m, 24) == -ERANGE);
 before = m; assert(mt6797_mac_join_release_channel(&m) == -ERANGE);
 assert(!memcmp(&m, &before, sizeof(m)));
 puts("grant horizon: PASS actual parent refusal 9466ms, 65000 event-to-window, +/-1ns, 65000 early boundaries, invalid/truncated event no-publication; setup unchanged");
 return 0;
}
