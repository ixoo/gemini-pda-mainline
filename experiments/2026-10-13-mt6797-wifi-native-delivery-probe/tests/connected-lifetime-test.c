/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
#include <limits.h>
typedef uint64_t u64;
#define U64_MAX UINT64_MAX
#define NSEC_PER_MSEC 1000000ULL
#define MT6797_JOIN_GRANT_TAIL_MS 2500U
#define MT6797_JOIN_TEARDOWN_MARGIN_MS 5000U
#define MT6797_JOIN_MAX_POLLS 4096U
#define MT6797_HIF_RX_MAX_PACKET 2352U
#define RX_FLAG_DECRYPTED 1U
#define RX_FLAG_IV_STRIPPED 2U
#define RX_FLAG_PN_VALIDATED 4U
#define RX_FLAG_MMIC_STRIPPED 8U
#define RX_FLAG_MIC_STRIPPED 16U
#define RX_FLAG_ALLOW_SAME_PN 32U
#define RX_FLAG_NO_SIGNAL_VAL 64U
#define min(a, b) ((a) < (b) ? (a) : (b))
#define min_t(t, a, b) min((t)(a), (t)(b))
#define dev_info(...) ((void)0)
#include "native-diag.h"
struct mt6797_mac {
 bool join_channel_granted, join_channel_released, join_data_phase, join_data_ended;
 bool ccmp_pm_connected, join_credit_pending, scan_active, closing;
 int first_error;
 unsigned int join_page_debt, join_polls, native_diag_state;
 unsigned int native_diag_total, native_diag_native, native_diag_bytes;
 unsigned int native_diag_retire_reads, native_diag_retire_bytes;
 bool native_diag_sample_done;
 void *join_inflight;
 u64 join_data_deadline, join_deadline, join_frame_deadline, join_grant_deadline;
 u64 join_data_started, join_hold_until, ccmp_pm_credit_ns;
 u64 native_diag_started, native_diag_retire_started, ccmp_channel_release_at;
 const char *join_data_end_reason;
};
static bool ccmp_stable_epoch = true;
static u64 test_now;
static u64 ktime_get_ns(void) { return test_now; }
#include "actual-open.inc"
#include "actual-end.inc"
#include "actual-pre-read.inc"
#include "actual-poll.inc"
#include "actual-entry.inc"
static struct mt6797_mac ready(void)
{
 return (struct mt6797_mac){ .join_channel_granted = true, .ccmp_pm_connected = true,
  .ccmp_pm_credit_ns = 1000000000ULL, .join_deadline = 10000000000ULL,
  .join_grant_deadline = 9000000000ULL, .join_polls = 80 };
}
int main(void)
{
 struct mt6797_mac m = ready();
 struct mt6797_native_diag_budget b = { .elapsed_ms = UINT_MAX };
 unsigned int i;
 test_now = 2000000000ULL;
 assert(!mt6797_mac_join_release_channel(&m));
 assert(m.join_deadline == U64_MAX && m.join_data_deadline == U64_MAX);
 assert(m.join_hold_until == U64_MAX && m.ccmp_channel_release_at == 6500000000ULL);
 /* No overflow into the past; 60 s, 2 min and 10 min are not join deadlines. */
 for (i = 0; i < 10000; i++) assert(!actual_poll_guard(&m, 600000000000ULL));
 assert(m.join_polls == 80);
 m.native_diag_state = MT6797_ND_ACTIVE;
 actual_mode_entry(&m, test_now, MT6797_ND_IDLE);
 assert(m.join_data_deadline == U64_MAX);
 test_now = 600000000000ULL;
 assert(!mt6797_native_diag_pre_read(&m) && !m.native_diag_sample_done);
 assert(mt6797_ccmp_diag_budget_step(&b) == MT6797_NATIVE_DIAG_CONTINUE);
 b.total_rx = MT6797_CCMP_DIAG_RX_MAX - 1;
 b.native_rx = MT6797_CCMP_DIAG_CHECKED_MAX - 1;
 b.bytes = MT6797_CCMP_DIAG_BYTES_MAX - 1;
 assert(mt6797_ccmp_diag_budget_step(&b) == MT6797_NATIVE_DIAG_CONTINUE);
 b.total_rx++; assert(mt6797_ccmp_diag_budget_step(&b) == MT6797_NATIVE_DIAG_STOP); b.total_rx--;
 b.native_rx++; assert(mt6797_ccmp_diag_budget_step(&b) == MT6797_NATIVE_DIAG_STOP); b.native_rx--;
 b.bytes++; assert(mt6797_ccmp_diag_budget_step(&b) == MT6797_NATIVE_DIAG_STOP);
 assert(mt6797_ccmp_diag_budget_step(NULL) == MT6797_NATIVE_DIAG_STOP);
 /* Every end gets one five-second fence; repeated callbacks never renew it. */
 mt6797_mac_join_end_data(&m, "disconnect");
 assert(m.join_deadline == test_now + 5000000000ULL && m.join_hold_until == test_now);
 assert(!actual_poll_guard(&m, m.join_deadline - 1));
 assert(actual_poll_guard(&m, m.join_deadline));
 assert(actual_poll_guard(&m, m.join_deadline + 1));
 test_now++;
 mt6797_mac_join_end_data(&m, "key-disable");
 assert(m.join_deadline == test_now - 1 + 5000000000ULL);
 assert(m.join_data_end_reason[0] == 'd');
 m = ready(); mt6797_mac_join_end_data(&m, "not-started");
 assert(m.join_deadline == 10000000000ULL && !m.join_data_ended);
 for (i = 0; i < 3; i++) {
  m = ready(); m.join_data_phase = true;
  m.join_deadline = test_now + 5000000000ULL - 1 + i;
  mt6797_mac_join_end_data(&m, "disconnect");
  assert(m.join_deadline == test_now + 5000000000ULL - (i == 0));
 }
 m = ready(); m.join_polls = 4095;
 assert(!actual_poll_guard(&m, 0) && m.join_polls == 4096);
 assert(actual_poll_guard(&m, 0) && m.join_polls == 4097);
 m = ready(); m.join_data_phase = m.join_data_ended = true; m.join_polls = 4096;
 assert(actual_poll_guard(&m, 0));
 for (i = 0; i < 4; i++) {
  m = ready(); m.join_data_phase = true;
  if (i == 0) m.first_error = -EIO;
  if (i == 1) m.closing = true;
  if (i == 2) m.scan_active = true;
  if (i == 3) { m.join_inflight = &m; m.join_frame_deadline = 1; }
  assert(actual_poll_guard(&m, 1));
 }
 /* Capacity reserve and post-end drain retain the exact existing boundaries. */
 m = ready(); m.join_data_phase = true; m.native_diag_state = MT6797_ND_ACTIVE;
 m.native_diag_bytes = MT6797_CCMP_DIAG_BYTES_MAX - MT6797_HIF_RX_MAX_PACKET;
 assert(!mt6797_native_diag_pre_read(&m));
 m.native_diag_bytes++; assert(mt6797_native_diag_pre_read(&m) == 1);
 m = ready(); m.native_diag_state = MT6797_ND_ACTIVE; m.join_data_ended = true;
 m.join_inflight = &m; m.native_diag_retire_started = test_now - 750000000ULL;
 assert(mt6797_native_diag_pre_read(&m) == -ETIMEDOUT);
 /* Native ciphertext retains its own 60 s wall even in this config. */
 ccmp_stable_epoch = false; m = ready(); m.native_diag_state = MT6797_ND_ACTIVE;
 m.native_diag_started = test_now - 60000000000ULL;
 assert(mt6797_native_diag_pre_read(&m) == 1 && m.native_diag_sample_done);
 m = ready(); m.native_diag_state = MT6797_ND_ACTIVE; m.join_data_deadline = U64_MAX;
 actual_mode_entry(&m, test_now, MT6797_ND_IDLE);
 assert(m.join_data_deadline == test_now + 60000000000ULL);
 puts("connected lifetime actual-source opening, +/-1 ns teardown, caps, poison and native parity PASS");
 return 0;
}
