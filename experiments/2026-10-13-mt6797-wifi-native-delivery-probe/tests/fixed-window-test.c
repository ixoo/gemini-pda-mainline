/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual encoder, grant parser, budget and extracted data-opening function. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
typedef unsigned long long u64;
#define NSEC_PER_MSEC 1000000ULL
#define RX_FLAG_DECRYPTED 1U
#define RX_FLAG_IV_STRIPPED 2U
#define RX_FLAG_PN_VALIDATED 4U
#define RX_FLAG_MMIC_STRIPPED 8U
#define RX_FLAG_MIC_STRIPPED 16U
#define RX_FLAG_ALLOW_SAME_PN 32U
#define RX_FLAG_NO_SIGNAL_VAL 64U
#include "join-commands.h"
#include "native-diag.h"
static u64 now = 1000000000ULL;
static u64 ktime_get_ns(void) { return now; }
#define min(a, b) ((a) < (b) ? (a) : (b))
#define wiphy_dev(x) (x)
#define dev_info(d, ...) do { if (0) printf(__VA_ARGS__); } while (0)
static bool ccmp_stable_epoch = true;
struct mt6797_mac {
 bool join_channel_granted, join_channel_released, join_data_phase, join_data_ended;
 bool join_credit_pending;
 unsigned int join_page_debt;
 u64 join_grant_deadline, join_data_started, join_data_deadline, join_deadline, join_hold_until;
 struct { bool active; } ccmp_observation;
};
#include "window-functions.inc"

static void window(long long remaining_ms, long long extra_ns, int expected)
{
 struct mt6797_mac m = {.join_channel_granted = true, .join_data_ended = true,
   .join_grant_deadline = now + remaining_ms * NSEC_PER_MSEC + extra_ns};
 struct mt6797_mac before = m;
 int rc = mt6797_mac_join_release_channel(&m);
 assert(rc == expected);
 if (rc) { assert(!memcmp(&before, &m, sizeof(m))); return; }
 assert(m.join_data_phase && !m.join_data_ended && m.ccmp_observation.active);
 assert(m.join_data_started == now);
 assert(m.join_data_deadline == now + 60000 * NSEC_PER_MSEC);
 assert(m.join_hold_until == m.join_data_deadline);
 assert(m.join_deadline == m.join_data_deadline + 5000 * NSEC_PER_MSEC);
 assert(m.join_grant_deadline - m.join_data_deadline >= 2500 * NSEC_PER_MSEC);
}

int main(void)
{
 unsigned char out[16], saved[16], event[24] = {24, 0, 0, 0xe0, 0x10};
 struct mt6797_join_channel expected = {.token = 1, .channel = 40, .band = 2,
   .max_ms = 65000};
 unsigned int interval;
 /* Narrow exception: all previously accepted intervals, exactly 65000, no
  * intervening or larger values. Refusal must not publish partial bytes. */
 for (unsigned int ms = 0; ms <= 70000; ms++) {
  memset(out, 0xa5, sizeof(out)); memcpy(saved, out, sizeof(out));
  bool ok = mt6797_join_channel_payload(1, 40, ms, false, out);
  assert(ok == ((ms > 0 && ms <= 10000) || ms == 65000));
  if (!ok) assert(!memcmp(out, saved, sizeof(out)));
  else assert(mt6797_join_le32(out + 12) == ms);
 }
 assert(requested_interval() == 65000);
 event[9] = 1; event[11] = 40; event[13] = 2;
 for (unsigned int ms = 0; ms <= 70000; ms++) {
  event[20] = ms; event[21] = ms >> 8; event[22] = ms >> 16;
  interval = 777;
  assert(mt6797_join_channel_grant(event, sizeof(event), &expected, &interval) ==
         (ms > 0 && ms <= 65000));
  assert(interval == (ms > 0 && ms <= 65000 ? ms : 777));
 }
 /* A representable interval never overrides grant identity matching. */
 event[20] = 65000 & 255; event[21] = 65000 >> 8; event[22] = 0;
 for (unsigned int field = 8; field <= 17; field++) {
  event[field] ^= 1; interval = 777;
  assert(!mt6797_join_channel_grant(event, sizeof(event), &expected, &interval));
  assert(interval == 777); event[field] ^= 1;
 }
 window(-1, 0, -ERANGE); window(0, 0, -ERANGE);
 window(2500, 0, -ERANGE); window(9000, 0, -ERANGE);
 window(62500, -1, -ERANGE); window(62500, 0, 0);
 window(62500, 1, 0); window(65000, 0, 0);
 for (unsigned int failure = 0; failure < 5; failure++) {
  struct mt6797_mac m = {.join_channel_granted = true,
    .join_grant_deadline = now + 65000 * NSEC_PER_MSEC};
  if (failure == 0) m.join_channel_granted = false;
  if (failure == 1) m.join_channel_released = true;
  if (failure == 2) m.join_data_phase = true;
  if (failure == 3) m.join_page_debt = 1;
  if (failure == 4) m.join_credit_pending = true;
  struct mt6797_mac before = m;
  assert(mt6797_mac_join_release_channel(&m) == -EBUSY);
  assert(!memcmp(&before, &m, sizeof(m)));
 }
 struct mt6797_native_diag_budget b = {.elapsed_ms = 59999};
 assert(mt6797_native_diag_budget_step(&b) == MT6797_NATIVE_DIAG_CONTINUE);
 b.elapsed_ms = 60000;
 assert(mt6797_native_diag_budget_step(&b) == MT6797_NATIVE_DIAG_STOP);
 b.elapsed_ms = 0; b.total_rx = 512;
 assert(mt6797_native_diag_budget_step(&b) == MT6797_NATIVE_DIAG_STOP);
 b.total_rx = 0; b.native_rx = 64;
 assert(mt6797_native_diag_budget_step(&b) == MT6797_NATIVE_DIAG_STOP);
 b.native_rx = 0; b.bytes = 1024 * 1024;
 assert(mt6797_native_diag_budget_step(&b) == MT6797_NATIVE_DIAG_STOP);
 assert(MT6797_NATIVE_DIAG_RETIRE_MS == 750);
 puts("fixed-window: narrow 65000 request, grant identity/range, 62500ms +/-1ns admission, 60000ms stop, unchanged resource/cleanup caps PASS");
 return 0;
}
