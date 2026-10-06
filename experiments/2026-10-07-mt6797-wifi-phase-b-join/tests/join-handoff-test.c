/* SPDX-License-Identifier: GPL-2.0-only */
/* Host lifetime fixtures only; bus/firmware and workqueue races are not modeled. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
#include <fixed-channels.h>
typedef uint8_t u8;
typedef uint64_t u64;
#define IS_ENABLED(option) (option)
#define BIT(n) (1U << (n))
#define NSEC_PER_SEC 1000000000ULL
#define NSEC_PER_MSEC 1000000ULL
#define NSEC_PER_USEC 1000ULL
#define MT6797_PASSIVE_SCAN_DWELL_MS 500
#define MT6797_NORMAL_NVRAM_SUBMITTED 1
#define MT6797_NORMAL_SCAN_CANCEL 2
#define MT6797_NORMAL_BSS_ACTIVE 3
#define dev_info(...) ((void)0)
#define memzero_explicit(p, n) memset((p), 0, (n))
#define spin_lock_irqsave(lock, flags) do { (void)(lock); (flags) = 0; } while (0)
#define spin_unlock_irqrestore(lock, flags) do { (void)(lock); (void)(flags); } while (0)
struct sk_buff { int unused; };
struct sk_buff_head { int lock; struct sk_buff *first; };
struct normal { unsigned phase, tc4_limit, tc4_free, tc4_pending_cpu, tc4_pending_ffa; void *used_sequences; };
struct hif { struct normal normal; };
struct wiphy { u8 perm_addr[6]; };
struct hw { struct wiphy *wiphy; void *priv; };
#define ieee80211_hw hw
struct ieee80211_vif { int unused; };
struct cfg80211_scan_info { bool aborted; };
struct mt6797_mac {
 struct hif *hif; struct hw *hw;
 bool scan_active, bss_active, join_retired, join_scan_ready, join_peer_used;
 bool join_running, join_open, join_sta_pending, join_sta_active;
 bool join_channel_pending, join_channel_granted;
 bool scan_frame_seen, scan_beacon, scan_credit, tuning_pending;
 unsigned scan_count, scan_channels, tuning_received, tuning_submitted;
 unsigned join_page_debt;
 int first_error;
 void *join_inflight;
 u64 scan_started_ns, join_deadline;
 struct sk_buff_head join_queue;
 int mutex, join_channel_done, join_sta_done; unsigned join_queue_bytes;
 int join_work, scan_work; u8 scan_packet[16];
};
static unsigned submissions, schedules, guards, kinds[4];
static int guard_error, send_error;
static inline u64 ktime_get_ns(void) { return 1000000000ULL; }
static inline unsigned msecs_to_jiffies(unsigned ms) { return ms; }
static inline void schedule_delayed_work(int *work, unsigned delay)
{ (void)work; assert(delay == 20); schedules++; }
static void mt6797_scan_bss(const u8 *address, bool active, u8 payload[12])
{ assert(address); assert(!active); memset(payload, 0, 12); }
static int mt6797_mac_send(struct mt6797_mac *mac, unsigned kind,
                           const u8 *payload, size_t bytes)
{
 assert(!mac->first_error && payload);
 assert((kind == MT6797_NORMAL_SCAN_CANCEL && bytes == 4) ||
        (kind == MT6797_NORMAL_BSS_ACTIVE && bytes == 12));
 assert(submissions < 4); kinds[submissions++] = kind;
 if (send_error) mac->first_error = send_error;
 return send_error;
}
#if CONFIG_MT6797_STATION_JOIN
static int mt6797_mac_join_guard(struct mt6797_mac *mac, u64 deadline)
{ (void)mac; assert(deadline == ktime_get_ns()+100*NSEC_PER_MSEC); guards++; return guard_error; }
#endif
static struct mt6797_mac *close_mac;
static bool finish_during_cancel;
static unsigned mutex_depth, cancels, completions, scan_notifications;
static int cancel_finish_status;
static void mutex_lock(int *mutex) { (void)mutex; assert(!mutex_depth); mutex_depth++; }
static void mutex_unlock(int *mutex) { (void)mutex; assert(mutex_depth==1); mutex_depth--; }
static void complete_all(int *completion) { (void)completion; completions++; }
static void skb_queue_head_init(struct sk_buff_head *head) { memset(head,0,sizeof(*head)); }
static void skb_queue_splice_init(struct sk_buff_head *from, struct sk_buff_head *to)
{ assert(!to->first); to->first=from->first; from->first=NULL; }
static void __skb_queue_tail(struct sk_buff_head *head, struct sk_buff *skb)
{ assert(!head->first); head->first=skb; }
static struct sk_buff *__skb_dequeue(struct sk_buff_head *head)
{ struct sk_buff *skb=head->first; head->first=NULL; return skb; }
static void ieee80211_free_txskb(struct hw *hw, struct sk_buff *skb)
{ (void)hw; assert(skb); }
static void cancel_delayed_work_sync(int *work);
static void ieee80211_scan_completed(struct hw *hw, struct cfg80211_scan_info *info)
{ (void)hw; assert(info->aborted); scan_notifications++; }
#include "handoff-functions.h"
static void cancel_delayed_work_sync(int *work)
{
 (void)work; assert(!mutex_depth); cancels++;
 if(finish_during_cancel) {
  finish_during_cancel=false;
  mutex_lock(&close_mac->mutex);
  cancel_finish_status=0;
  assert(mt6797_mac_finish_scan(close_mac,&cancel_finish_status,false));
  mutex_unlock(&close_mac->mutex);
 }
}

static struct mt6797_mac ready(void)
{
 static struct hif hif; static struct wiphy wiphy; static u8 history[32];
 static struct hw hw = {.wiphy=&wiphy};
 hif.normal=(struct normal){.phase=MT6797_NORMAL_NVRAM_SUBMITTED,
  .tc4_limit=4,.tc4_free=4,.used_sequences=history};
 submissions=schedules=guards=cancels=completions=mutex_depth=scan_notifications=0;
 finish_during_cancel=false; close_mac=NULL; guard_error=send_error=0;
 return (struct mt6797_mac){.hif=&hif,.hw=&hw,.scan_active=true,
  .bss_active=true,.scan_count=1,.scan_channels=BIT(mt6797_channel_slot(40)),
  .tuning_submitted=4,.tuning_received=4};
}
int main(void)
{
 struct mt6797_mac mac=ready(); int status=0;
 assert(mt6797_mac_finish_scan(&mac,&status,false));
 assert(!status && !mac.scan_active);
#if CONFIG_MT6797_STATION_JOIN
 assert(mac.bss_active && mac.join_scan_ready && mac.join_running);
 assert(!submissions && schedules==1 && mac.join_deadline==11000000000ULL);
 assert(!mt6797_mac_finish_scan(&mac,&status,false));
 assert(schedules==1 && !submissions);
 assert(!mt6797_mac_join_retire_idle_bss(&mac));
 assert(guards==1 && submissions==1 && kinds[0]==MT6797_NORMAL_BSS_ACTIVE);
 assert(!mac.bss_active);
 assert(!mt6797_mac_join_retire_idle_bss(&mac) && submissions==1);
 for(unsigned bad=0;bad<12;bad++) {
  mac=ready(); status=0;
  if(bad==0) mac.scan_channels=1;
  if(bad==1) mac.scan_count=2;
  if(bad==2) mac.join_retired=true;
  if(bad==3) mac.hif->normal.tc4_free=3;
  if(bad==4) mac.hif->normal.tc4_limit=mac.hif->normal.tc4_free=0;
  if(bad==5) mac.tuning_pending=true;
  if(bad==6) mac.tuning_received=3;
  if(bad==7) mac.hif->normal.phase=0;
  if(bad==8) mac.hif->normal.tc4_limit=mac.hif->normal.tc4_free=0x10000;
  if(bad==9) mac.hif->normal.used_sequences=NULL;
  if(bad==10) mac.hif->normal.tc4_pending_cpu=1;
  if(bad==11) mac.hif->normal.tc4_pending_ffa=1;
  assert(mt6797_mac_finish_scan(&mac,&status,false));
  if(bad==2) {
   assert(status==-ECANCELED && mac.first_error==-ECANCELED);
   assert(!mac.bss_active && submissions==1 && !schedules);
   continue;
  }
  assert(status==-EPROTO && mac.first_error==-EPROTO);
  assert(!submissions && !schedules && !mac.join_scan_ready);
 }
 for(unsigned busy=0;busy<4;busy++) {
  mac=ready(); mac.scan_active=false; mac.join_scan_ready=true;
  if(busy==0) mac.join_peer_used=true;
  if(busy==1) mac.first_error=-EIO;
  if(busy==2) mac.join_channel_pending=true;
  if(busy==3) mac.join_inflight=&mac;
  assert(!mt6797_mac_join_retire_idle_bss(&mac));
  assert(!submissions && !guards && mac.bss_active);
 }
 mac=ready(); mac.scan_active=false; mac.join_scan_ready=true; guard_error=-EIO;
 assert(mt6797_mac_join_retire_idle_bss(&mac)==-EIO);
 assert(!submissions && mac.bss_active);
 mac=ready(); mac.scan_active=false; mac.join_scan_ready=true; send_error=-EIO;
 assert(mt6797_mac_join_retire_idle_bss(&mac)==-EIO);
 assert(submissions==1 && mac.first_error==-EIO && mac.bss_active);
#else
 assert(!mac.bss_active && submissions==1 && !schedules);
 assert(kinds[0]==MT6797_NORMAL_BSS_ACTIVE);
#endif
 mac=ready(); status=-ECANCELED;
 assert(mt6797_mac_finish_scan(&mac,&status,true));
 assert(status==-ECANCELED && submissions==2 && !schedules);
 assert(kinds[0]==MT6797_NORMAL_SCAN_CANCEL && kinds[1]==MT6797_NORMAL_BSS_ACTIVE);
 assert(!mac.join_scan_ready && !mac.bss_active);
 mac=ready(); status=-EIO; mac.first_error=-EIO;
 assert(mt6797_mac_finish_scan(&mac,&status,false));
 assert(!submissions && !schedules && mac.bss_active);
#if CONFIG_MT6797_STATION_JOIN
 /* Deterministic scan-finish interleaving at close's cancel-sync boundary. */
 mac=ready(); close_mac=&mac; finish_during_cancel=true;
 mt6797_mac_join_close(&mac);
 assert(cancels==1 && completions==2 && !mutex_depth);
 assert(!mac.join_running && mac.join_retired && !mac.join_scan_ready);
 assert(!schedules && cancel_finish_status==-ECANCELED);
 assert(!mac.bss_active && submissions==1);
 /* Completion before close must also retire the already queued pump. */
 mac=ready(); status=0;
 assert(mt6797_mac_finish_scan(&mac,&status,false));
 mt6797_mac_join_close(&mac);
 assert(cancels==1 && !mac.join_running && mac.join_retired);
 assert(!mac.bss_active && submissions==1);
#else
 mt6797_mac_join_close(&mac);
 assert(cancels==1 && !mac.join_running);
#endif
 /* Active cancellation completes once; late cancellation cannot retain join. */
 mac=ready(); mac.hw->priv=&mac;
 mt6797_mac_cancel_scan(mac.hw,NULL);
 assert(scan_notifications==1 && submissions==2 && !mac.scan_active);
 assert(!mac.join_running && !mac.join_scan_ready && !mac.bss_active);
#if CONFIG_MT6797_STATION_JOIN
 mac=ready(); status=0; mac.hw->priv=&mac;
 assert(mt6797_mac_finish_scan(&mac,&status,false));
 mt6797_mac_cancel_scan(mac.hw,NULL);
 assert(!scan_notifications && cancels==2 && mac.join_retired);
 assert(!mac.join_running && !mac.join_scan_ready && !mac.bss_active);
 assert(submissions==1);
#endif
 return 0;
}
