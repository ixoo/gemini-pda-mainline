/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <errno.h>
typedef uint64_t u64;
#define IS_ENABLED(x) 0
#define NSEC_PER_MSEC 1000000ULL
#define MT6797_JOIN_DATA_BUDGET_MS 60000U
#define MT6797_JOIN_GRANT_TAIL_MS 2500U
#define MT6797_JOIN_TEARDOWN_MARGIN_MS 5000U
#define min(a, b) ((a) < (b) ? (a) : (b))
#define min_t(t, a, b) min((t)(a), (t)(b))
#define wiphy_dev(x) (x)
#define dev_info(...) ((void)0)
struct hw { void *wiphy; };
struct mt6797_mac {
 bool join_channel_released, ccmp_channel_release_pending;
 bool join_data_phase, join_data_ended, first_error, closing, join_retired;
 bool join_running, join_channel_granted, ccmp_pm_connected, join_sta_active;
 bool join_credit_pending, join_channel_pending;
 unsigned int join_key_pairwise, join_key_group, join_page_debt;
 unsigned int join_data_page_debt, sequence, join_channel_token;
 unsigned int ccmp_channel_release_sequence;
 u64 ccmp_channel_release_at, join_grant_deadline, join_deadline;
 u64 ccmp_pm_credit_ns, join_credit_deadline;
 u64 join_data_started, join_data_deadline, join_hold_until;
 void *join_inflight, *hif;
 struct hw *hw;
 int join_credit_done, join_channel_done;
 unsigned char join_packet[24];
};
static bool ccmp_stable_epoch = true;
static unsigned int submissions;
static int transport_error;
static u64 submitted_deadline;
static void reinit_completion(int *done) { *done = 0; }
static int mt6797_hif_join_channel(void *hif, unsigned int seq, unsigned int token,
 unsigned int channel, unsigned int ms, bool abort, u64 deadline)
{
 (void)hif;
 assert(seq == 30 && token == 1 && channel == 40 && !ms && abort);
 submissions++; submitted_deadline = deadline;
 return transport_error;
}
static u64 test_now;
static u64 ktime_get_ns(void) { return test_now; }
#include "actual-channel-release.inc"
#include "actual-open-data.inc"
static unsigned int grant_interval;
static bool grant_valid = true;
static bool mt6797_join_event(const void *p, size_t n, int id, int size)
{
 (void)p; (void)n; (void)id; (void)size; return true;
}
static bool mt6797_join_channel_grant(const void *p, size_t n, const int *expected,
 unsigned int *interval)
{
 (void)p; (void)n; (void)expected;
 *interval = grant_interval; return grant_valid;
}
static void complete_all(int *done) { *done = 1; }
#include "actual-grant.inc"
static struct mt6797_mac ready(void)
{
 return (struct mt6797_mac){ .join_data_phase = true, .join_running = true,
  .join_channel_granted = true, .ccmp_pm_connected = true, .join_sta_active = true,
  .join_key_pairwise = 1, .join_key_group = 1, .sequence = 30,
  .join_channel_token = 1, .ccmp_channel_release_at = 6500000000ULL,
  .join_grant_deadline = 9000000000ULL, .join_deadline = 65000000000ULL,
  .ccmp_pm_credit_ns = 1000000000ULL };
}
int main(void)
{
 struct mt6797_mac m;
 unsigned int i;
 const u64 at = 6500000000ULL;
 m = ready(); m.join_channel_pending = true; test_now = 1000000000ULL;
 grant_interval = 8999;
 assert(actual_grant(&m) == -ERANGE);
 assert(m.join_channel_granted && !m.join_channel_pending && !m.join_channel_done);
 assert(m.join_grant_deadline == test_now + 8999000000ULL);
 m = ready(); m.join_channel_pending = true; grant_interval = 9000;
 assert(!actual_grant(&m) && m.join_channel_done);
 assert(m.join_grant_deadline == test_now + 9000000000ULL);
 m = ready(); m.join_channel_pending = true; grant_valid = false;
 assert(actual_grant(&m) == -EPROTO && m.join_channel_pending);
 grant_valid = true;
 m = ready(); m.join_data_phase = false; test_now = at - 1;
 ccmp_stable_epoch = false;
 assert(mt6797_mac_join_release_channel(&m) == -EOPNOTSUPP);
 ccmp_stable_epoch = true;
 assert(!mt6797_mac_join_release_channel(&m));
 assert(m.join_data_deadline == test_now + 60000000000ULL);
 assert(m.join_deadline == m.join_data_deadline + 5000000000ULL);
 assert(m.ccmp_channel_release_at == at);
 m = ready(); m.join_data_phase = false; test_now = at;
 assert(mt6797_mac_join_release_channel(&m) == -ETIMEDOUT);
 m = ready(); m.join_data_phase = false; test_now = at + 1;
 assert(mt6797_mac_join_release_channel(&m) == -ETIMEDOUT);
 m = ready(); assert(!mt6797_ccmp_channel_release_step(&m, at - 1));
 assert(!submissions && !m.join_credit_pending);
 m = ready(); assert(mt6797_ccmp_channel_release_step(&m, at) == 1);
 assert(submissions == 1 && m.sequence == 31 && m.join_page_debt == 1);
 assert(m.ccmp_channel_release_pending && !m.join_channel_released);
 assert(submitted_deadline == at + 100 * NSEC_PER_MSEC);
 assert(mt6797_ccmp_channel_release_step(&m, at + 1) == 1 && submissions == 1);
 m.join_credit_pending = false; /* A flag alone must not manufacture credit. */
 assert(mt6797_ccmp_channel_release_step(&m, at + 2) == 1);
 m.join_page_debt = 0;
 assert(!mt6797_ccmp_channel_release_step(&m, at + 3));
 assert(m.join_channel_released && !m.join_channel_granted);
 assert(!mt6797_ccmp_channel_release_step(&m, m.join_grant_deadline + 1));
 assert(submissions == 1); /* Release is once, never re-acquired. */
 for (i = 0; i < 4; i++) {
  m = ready(); submissions = 0;
  if (i == 0) m.join_inflight = &m;
  if (i == 1) m.join_credit_pending = true;
  if (i == 2) m.join_page_debt = 1;
  if (i == 3) m.join_data_page_debt = 1;
  assert(mt6797_ccmp_channel_release_step(&m, at) == 1 && !submissions);
 }
 for (i = 0; i < 9; i++) {
  m = ready(); submissions = 0;
  if (i == 0) m.first_error = true;
  if (i == 1) m.closing = true;
  if (i == 2) m.join_retired = true;
  if (i == 3) m.join_running = false;
  if (i == 4) m.join_channel_granted = false;
  if (i == 5) m.ccmp_pm_connected = false;
  if (i == 6) m.ccmp_pm_credit_ns = 0;
  if (i == 7) m.join_key_pairwise = 2;
  if (i == 8) m.join_key_group = 2;
  assert(mt6797_ccmp_channel_release_step(&m, at) == -EPROTO && !submissions);
 }
 for (i = 0; i < 2; i++) {
  m = ready(); submissions = 0;
  if (i == 0) m.join_grant_deadline = at;
  else m.join_deadline = at;
  assert(mt6797_ccmp_channel_release_step(&m, at) == -ETIMEDOUT && !submissions);
 }
 m = ready(); submissions = 0; m.sequence = 254;
 assert(mt6797_ccmp_channel_release_step(&m, at) == -ENOSPC && !submissions);
 m = ready(); m.join_data_ended = true;
 assert(!mt6797_ccmp_channel_release_step(&m, at) && !submissions);
 m = ready(); m.join_grant_deadline = at + 1;
 assert(mt6797_ccmp_channel_release_step(&m, at) == 1);
 assert(submitted_deadline == at + 1); /* Never extend the resource horizon. */
 m = ready(); transport_error = -EIO;
 assert(mt6797_ccmp_channel_release_step(&m, at) == -EIO);
 assert(m.join_page_debt == 1 && m.ccmp_channel_release_pending);
 assert(!m.join_channel_released); /* Uncertain PIO must retain the debit. */
 puts("channel-release actual-source ownership/drain/failure cases PASS");
 return 0;
}
