/* SPDX-License-Identifier: GPL-2.0-only */
/* Deterministic host interleavings, not a kernel concurrency or firmware model. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdarg.h>
#include <string.h>
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
#include <join-commands.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef uint64_t u64;
#define NSEC_PER_SEC 1000000000ULL
#define NSEC_PER_MSEC 1000000ULL
#define BIT(n) (1U << (n))
#define NL80211_BAND_5GHZ 1
#define IS_ENABLED(x) (x)
#define CONFIG_MT6797_STATION_JOIN 1
#define CONFIG_MT6797_PASSIVE_SCAN 1
#define IEEE80211_STYPE_AUTH 0xb0
#define IEEE80211_STYPE_ASSOC_REQ 0
#define IEEE80211_STYPE_DEAUTH 0xc0
#define WLAN_REASON_DEAUTH_LEAVING 3
#define MT6797_NORMAL_BSS_ACTIVE 0x11
enum ieee80211_sta_state { IEEE80211_STA_NOTEXIST, IEEE80211_STA_NONE,
 IEEE80211_STA_AUTH, IEEE80211_STA_ASSOC, IEEE80211_STA_AUTHORIZED };
struct wiphy { u8 perm_addr[6]; };
struct ieee80211_hw { void *priv; struct wiphy *wiphy; };
struct ieee80211_tx_info { unsigned band, flags; };
struct sk_buff { u8 data[26]; unsigned len; struct ieee80211_tx_info info; };
struct sk_buff_head { int lock; struct sk_buff *head; };
#define IEEE80211_SKB_CB(s) (&(s)->info)
#define wiphy_dev(w) (w)
/* Capture the refusal bitmask the production diagnostic reports. */
static unsigned last_reasons, refusal_logs, cleanup_logs, cleanup_stage, cleanup_free, overflow_logs;
static unsigned absence_logs, absence_bss, absence_flag, absence_quota;
static void record(const char *fmt, ...)
{ va_list ap; va_start(ap, fmt);
  if (strstr(fmt, "peer refused")) { last_reasons = va_arg(ap, unsigned); refusal_logs++; }
  else if (strstr(fmt, "cleanup refused")) { cleanup_stage = va_arg(ap, unsigned); (void)va_arg(ap, unsigned); cleanup_free = va_arg(ap, unsigned); cleanup_logs++; }
  else if (strstr(fmt, "credit overflow")) overflow_logs++;
  else if (strstr(fmt, "bss absence")) { absence_bss = va_arg(ap, unsigned); absence_flag = va_arg(ap, unsigned); absence_quota = va_arg(ap, unsigned); absence_logs++; }
  va_end(ap); }
#define dev_info(dev, ...) record(__VA_ARGS__)
static unsigned allocations, losses;
static bool allocation_failure;
static struct sk_buff *dev_alloc_skb(unsigned n)
{ assert(n==26);if(allocation_failure)return NULL;allocations++;return calloc(1,sizeof(struct sk_buff)); }
static void dev_kfree_skb(struct sk_buff *s) { if(s) { allocations--;free(s); } }
static u8 *skb_put_zero(struct sk_buff *s,unsigned n) { s->len=n;return s->data; }
static bool skb_queue_empty(struct sk_buff_head *q) { return !q->head; }
static void __skb_queue_tail(struct sk_buff_head *q,struct sk_buff *s)
{ assert(!q->head);q->head=s; }
static void put_unaligned_le16(unsigned n,u8 *p) { p[0]=n;p[1]=n>>8; }
static void mt6797_scan_bss(const u8 *a,bool active,u8 *p)
{ assert(a[0]==2 && !active);memset(p,0,12);memcpy(p+4,a,6); }
struct ieee80211_prep_tx_info { unsigned subtype, link_id; bool success; };
#define min(a,b) ((a)<(b)?(a):(b))
#define min_t(t,a,b) min((t)(a),(t)(b))
#define spin_lock_irqsave(lock,flags) do { (void)(lock); (flags)=0; } while (0)
#define spin_unlock_irqrestore(lock,flags) do { (void)(lock); (void)(flags); } while (0)
struct completion { unsigned count; };
struct ieee80211_vif { unsigned valid_links; struct { unsigned aid; } cfg; };
enum set_key_cmd { SET_KEY, DISABLE_KEY };
#define IEEE80211_KEY_FLAG_PAIRWISE BIT(3)
#define WLAN_CIPHER_SUITE_CCMP 0x000fac04
struct ieee80211_key_conf { unsigned cipher; int keyidx; unsigned keylen; unsigned flags; u8 key[32]; };
static void schedule_delayed_work(int *w, unsigned long d) { (void)w; (void)d; }
static unsigned long msecs_to_jiffies(unsigned ms) { return ms; }
struct ieee80211_sta { bool mlo; unsigned valid_links; u8 addr[6];
 struct { unsigned supp_rates[2]; } deflink; };
struct mt6797_hif { int unused; };
struct mt6797_hif_tx_status { int unused; };
struct mt6797_normal_release { unsigned released_pages; };
struct mt6797_mac {
 struct mt6797_hif *hif; struct ieee80211_vif *vif; struct ieee80211_hw *hw;
 int mutex, scan_work; struct sk_buff_head join_queue;
 bool scan_active, join_scan_ready, started, configured, bss_active;
 bool join_running, join_bss_valid, join_channel_valid, join_peer_used;
 bool join_retired, closing, join_open, join_peer_ready;
 bool join_authenticated, join_auth_received, join_auth_ok, join_assoc_received;
 bool join_last_acked, join_short_preamble, join_bss_configured;
 bool join_cleanup_requested, join_cleanup_done, join_deauth_done;
 unsigned join_cleanup_stage, join_queue_bytes; struct sk_buff *join_internal;
 unsigned join_last_sequence;
 u8 join_ssid[32], join_ssid_bytes;
 unsigned join_aid, join_assoc_status;
 void *join_inflight; u64 join_frame_deadline;
 unsigned join_seen, join_tx_allowed, join_rx_allowed;
 bool join_credit_pending, join_channel_pending, join_channel_granted;
 bool join_sta_pending, join_sta_active;
 bool join_peer_refusal_logged, join_channel_refusal_logged;
 unsigned join_absence_events;
 unsigned join_eapol_seen; u64 join_hold_until;
 bool join_rsn; unsigned join_key_pairwise, join_key_group; u8 join_group_key_id;
 unsigned int join_group_discarded; unsigned int join_action_discarded; bool join_key_pairwise_submitted, join_key_group_submitted, join_key_done, join_key_done_second;
 int join_work;
 unsigned join_page_debt, sequence, join_requested_ms, join_basic_rates;
 unsigned join_desired_rates, join_peer_basic_rates;
 u8 join_ap[6], join_bssid[6], join_channel_token, join_sta_sequence;
 u8 join_packet[24]; int first_error;
 u64 join_deadline, join_grant_deadline, join_credit_deadline;
 struct completion join_credit_done, join_channel_done, join_sta_done, join_frame_done;
};
static struct mt6797_mac *active;
static u64 now;
static unsigned locked, writes, waits, fail_write, fail_wait, released;
static unsigned order[16];
static int wait_mode;
static bool idle;
static void ieee80211_connection_loss(struct ieee80211_vif *v)
{ assert(v==active->vif && locked);losses++; }
static void mt6797_mac_join_close(struct mt6797_mac *m)
{ m->join_retired=true;m->join_running=false;m->join_open=false; }
static u64 ktime_get_ns(void) { return now; }
static unsigned long nsecs_to_jiffies(u64 ns) { return ns/NSEC_PER_MSEC; }
static void mutex_lock(int *m) { (void)m; assert(!locked); locked=1; }
static void mutex_unlock(int *m) { (void)m; assert(locked); locked=0; }
static void complete_all(struct completion *c) { c->count++; }
static void reinit_completion(struct completion *c) { c->count=0; }
static void cancel_delayed_work_sync(int *w) { (void)w; assert(!locked); }
static bool ether_addr_equal(const u8 *a,const u8 *b) { return !memcmp(a,b,6); }
static bool is_broadcast_ether_addr(const u8 *a) { return (a[0]&a[1]&a[2]&a[3]&a[4]&a[5])==0xff; }
static void ether_addr_copy(u8 *a,const u8 *b) { memcpy(a,b,6); }
static bool mt6797_hif_normal_idle(struct mt6797_hif *h) { assert(h); return idle; }
struct mt6797_hif_ledger { unsigned phase, tc4_free, tc4_limit, pending_cpu, pending_ffa; bool sequences, locked; };
static void mt6797_hif_normal_ledger(struct mt6797_hif *h, struct mt6797_hif_ledger *o)
{ assert(h && o); *o = (struct mt6797_hif_ledger){.phase = 5, .tc4_free = 25, .tc4_limit = 26, .pending_cpu = 1, .sequences = true}; }
static int mt6797_hif_read32(struct mt6797_hif *h,unsigned reg,u64 d,u32 *v)
{ assert(h && d>now); *v=reg ? BIT(8) : 0x0279|BIT(21); return 0; }
static int mt6797_hif_reconcile_runtime(struct mt6797_hif *h,u64 d,
 struct mt6797_hif_tx_status *s,struct mt6797_normal_release *a)
{ assert(h && d>now && s); a->released_pages=released;released=0;return 0; }
static int command(unsigned kind,unsigned sequence,u64 deadline)
{ assert(locked && deadline>now && sequence==5+writes && writes<16);
 order[writes++]=kind; return writes==fail_write ? -EIO : 0; }
static int mt6797_hif_join_filter(struct mt6797_hif *h,unsigned s,u64 d)
{ assert(h && active->join_page_debt==1); return command(0x0a,s,d); }
static int mt6797_hif_join_channel(struct mt6797_hif *h,unsigned s,u8 token,
 u8 channel,unsigned ms,bool abort,u64 d)
{ assert(h && token==1 && channel==40 && (abort ? ms==0 : ms==9000));
 assert(active->join_page_debt==1); return command(0x1c,s,d); }
static int mt6797_hif_join_station(struct mt6797_hif *h,unsigned s,const u8 *ap,
 unsigned state,unsigned aid,unsigned desired,unsigned basic,u64 d)
{ assert(h && ((state==1 && !aid) || (state==3 && aid==42)));
 assert(desired==0x3fc0 && basic==0x40);
 assert(active->join_page_debt==2 && ether_addr_equal(ap,active->join_bssid));
 return command(0x13,s,d); }
static bool expect_wpa2;
static int mt6797_hif_join_bss(struct mt6797_hif *h,unsigned s,const u8 *ap,
 const u8 *ssid,unsigned n,unsigned desired,unsigned basic,bool pre,bool wpa2,u64 d)
{ assert(h && ether_addr_equal(ap,active->join_ap) && n==3);
 assert(!memcmp(ssid,"lab",3) && desired==0x3fc0 && basic==0x40 && !pre && wpa2==expect_wpa2);
 assert(active->join_page_debt==1);return command(0x12,s,d); }
static unsigned key_adds, key_removals, key_pairwise, key_group;
static int mt6797_hif_join_key(struct mt6797_hif *h,unsigned s,bool add,bool pairwise,
 const u8 *peer,unsigned key_id,const u8 *material,u64 d)
{ assert(h && ether_addr_equal(peer,active->join_ap) && active->join_page_debt==1);
 assert(pairwise ? key_id==0 : key_id<=3);
 assert(add ? material!=NULL : material==NULL);
 if(add) key_adds++; else key_removals++;
 if(pairwise) key_pairwise++; else key_group++;
 return command(0x07,s,d); }
static int mt6797_hif_join_remove_station(struct mt6797_hif *h,unsigned s,u64 d)
{ assert(h && active->join_page_debt==1);return command(0x14,s,d); }
static int mt6797_hif_send_config(struct mt6797_hif *h,unsigned kind,unsigned s,
 const u8 *p,unsigned n,u64 d)
{ assert(h && kind==0x11 && n==12 && p[4]==2 && active->join_page_debt==1);
 return command(kind,s,d); }
static unsigned long wait_for_completion_timeout(struct completion *,unsigned long);
#include "peer-functions.h"
static unsigned long wait_for_completion_timeout(struct completion *c,unsigned long ticks)
{
 assert(!locked && ticks); waits++;
 if(waits==fail_wait) {
  if(wait_mode==1) active->first_error=-EIO;
  else if(wait_mode==2) active->join_retired=true;
  else if(wait_mode==3) now=active->join_credit_deadline;
  /* mode 0 is a spurious wake: it supplies neither credit nor event. */
  return 0;
 }
 if(c==&active->join_credit_done) {
  released=active->join_page_debt;
  assert(!mt6797_mac_join_guard(active,active->join_credit_deadline));
 } else if(c==&active->join_channel_done) {
  memset(active->join_packet,0,24);
  u8 *p=active->join_packet;
  p[0]=24;p[3]=0xe0;p[4]=0x10;p[9]=1;p[11]=40;p[13]=2;
  p[20]=9000&255;p[21]=9000>>8;
  assert(!mt6797_mac_join_control_event(active,24));
 } else if(c==&active->join_sta_done) {
  memset(active->join_packet,0,24);u8 *p=active->join_packet;
  p[0]=16;p[3]=0xe0;p[4]=0x0c;p[5]=active->join_sta_sequence;
  memcpy(p+8,active->join_ap,6);p[14]=1;
  assert(!mt6797_mac_join_control_event(active,16));
 } else {
  assert(c==&active->join_frame_done);
  active->join_inflight=NULL;active->join_last_acked=true;complete_all(c);
 }
 return 1;
}
static struct mt6797_mac ready(struct ieee80211_vif *vif,struct ieee80211_sta *sta)
{
 static struct mt6797_hif hif;
 static struct wiphy wiphy={.perm_addr={2,0,0,0,0,9}};
 static struct ieee80211_hw hw={.wiphy=&wiphy};
 now=NSEC_PER_SEC; writes=waits=locked=fail_write=fail_wait=released=0;
 key_adds=key_removals=key_pairwise=key_group=0; expect_wpa2=false;
 assert(!allocations);idle=true;wait_mode=0;losses=0;allocation_failure=false;
 memset(sta,0,sizeof(*sta)); sta->addr[0]=2;sta->addr[5]=7;
 sta->deflink.supp_rates[1]=255;
 struct mt6797_mac m={.hif=&hif,.vif=vif,.hw=&hw,.started=true,.configured=true,
  .join_scan_ready=true,.bss_active=true,.join_running=true,
  .join_bss_valid=true,.join_channel_valid=true,.join_basic_rates=1,
  .join_deadline=now+10*NSEC_PER_SEC,.sequence=5};
 memcpy(m.join_bssid,sta->addr,6); return m;
}
int main(void)
{
 struct ieee80211_vif vif={0};struct ieee80211_sta sta;
 struct mt6797_mac m=ready(&vif,&sta); active=&m;
 assert(!mt6797_mac_join_add_peer(&m,&vif,&sta));
 assert(writes==3 && waits==4 && !locked && !m.join_open);
 assert(order[0]==0x0a && order[1]==0x1c && order[2]==0x13);
 assert(m.join_peer_used && m.join_channel_granted && !m.join_page_debt);
 memset(sta.addr,0,6); assert(m.join_ap[5]==7);
 last_reasons=0;refusal_logs=0;
 assert(mt6797_mac_join_add_peer(&m,&vif,&sta)==-EOPNOTSUPP && writes==3);
 /* Second peer and foreign address are both named; logged once per lifetime. */
 assert(m.join_peer_refusal_logged && refusal_logs==1 && last_reasons==(BIT(10)|BIT(17)));
 assert(mt6797_mac_join_add_peer(&m,&vif,&sta)==-EOPNOTSUPP && refusal_logs==1);
 for(unsigned failure=1;failure<=3;failure++) {
  m=ready(&vif,&sta);fail_write=failure;
  assert(mt6797_mac_join_add_peer(&m,&vif,&sta)==-EIO);
  assert(writes==failure && m.join_peer_used && m.join_retired && !m.join_running);
 }
 for(unsigned mode=0;mode<=3;mode++) {
  m=ready(&vif,&sta);fail_wait=1;wait_mode=mode;
  int expected=mode==1 ? -EIO : mode==2 ? -ECANCELED : -ETIMEDOUT;
  assert(mt6797_mac_join_add_peer(&m,&vif,&sta)==expected);
  assert(writes==1 && m.join_retired && !locked);
 }
 /* A released page beyond the debt is refused as before and now logged. */
 m=ready(&vif,&sta);overflow_logs=0;m.join_page_debt=0;released=1;
 assert(mt6797_mac_join_guard(&m,now+NSEC_PER_MSEC)==-EPROTO && overflow_logs==1);released=0;
 m=ready(&vif,&sta);idle=false;last_reasons=0;refusal_logs=0;
 assert(mt6797_mac_join_add_peer(&m,&vif,&sta)==-EOPNOTSUPP && !writes);
 assert(refusal_logs==1 && last_reasons==BIT(16) && !m.join_peer_used && m.join_running);
 m=ready(&vif,&sta);m.sequence=254;
 assert(mt6797_mac_join_add_peer(&m,&vif,&sta)==-EOPNOTSUPP && !writes);
 m=ready(&vif,&sta);m.join_page_debt=2;m.join_credit_pending=true;
 m.join_credit_deadline=now+100*NSEC_PER_MSEC;released=1;
 assert(!mt6797_mac_join_guard(&m,m.join_credit_deadline));
 assert(m.join_page_debt==1 && !m.join_credit_done.count);
 released=1;
 assert(!mt6797_mac_join_guard(&m,m.join_credit_deadline));
 assert(!m.join_page_debt && m.join_credit_done.count==1);
 m.join_page_debt=1;released=2;
 assert(mt6797_mac_join_guard(&m,m.join_credit_deadline)==-EPROTO && m.join_page_debt==1);
 /* STA activation is not a TC4 release. */
 m=ready(&vif,&sta);m.join_sta_pending=true;m.join_sta_sequence=9;
 memcpy(m.join_ap,sta.addr,6);m.join_credit_pending=true;m.join_page_debt=2;
 u8 *p=m.join_packet;p[0]=16;p[3]=0xe0;p[4]=0x0c;p[5]=9;
 memcpy(p+8,sta.addr,6);p[14]=1;
 assert(!mt6797_mac_join_control_event(&m,16));
 assert(m.join_sta_active && m.join_credit_pending && m.join_page_debt==2);
 assert(m.join_sta_done.count==1 && !m.join_credit_done.count);
 /* The proven scan notifications stay bounded and retain CPU ownership. */
 memset(p,0,24);p[0]=12;p[3]=0xe0;p[4]=7;
 assert(!mt6797_mac_join_control_event(&m,12));
 p[8]=2;assert(mt6797_mac_join_control_event(&m,12)==-EPROTO);
 p[4]=0x27;assert(!mt6797_mac_join_control_event(&m,12));
 p[0]=11;assert(mt6797_mac_join_control_event(&m,12)==-EPROTO);
 p[0]=12;p[4]=0xff;assert(mt6797_mac_join_control_event(&m,12)==-EPROTO);
 /* Stack state may advance only after a received successful auth response. */
 m=ready(&vif,&sta);m.join_peer_ready=true;
 memcpy(m.join_ap,sta.addr,6);m.join_channel_granted=true;
 m.join_grant_deadline=now+9*NSEC_PER_SEC;
 struct ieee80211_hw hw={.priv=&m};
 struct ieee80211_prep_tx_info info={.subtype=IEEE80211_STYPE_AUTH};
 assert(mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_NONE,IEEE80211_STA_AUTH)==-EOPNOTSUPP);
 mt6797_mac_mgd_prepare_tx(&hw,&vif,&info);
 assert(m.join_open && m.join_tx_allowed==BIT(11) && (m.join_rx_allowed&BIT(11)));
 assert(!writes && !locked);
 m.join_seen=BIT(11);m.join_auth_received=true;m.join_auth_ok=true;m.join_last_acked=true;
 assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_NONE,IEEE80211_STA_AUTH));
 info.success=true;mt6797_mac_mgd_complete_tx(&hw,&vif,&info);
 assert(!m.join_open && !m.first_error && m.join_authenticated);
 info.subtype=IEEE80211_STYPE_ASSOC_REQ;mt6797_mac_mgd_prepare_tx(&hw,&vif,&info);
 assert(m.join_open && m.join_tx_allowed==BIT(0) && (m.join_rx_allowed&BIT(1)));
 m.join_seen|=BIT(0);mt6797_mac_mgd_prepare_tx(&hw,&vif,&info);
 assert(!m.join_open && m.first_error==-EOPNOTSUPP && !writes);
 assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_AUTH,IEEE80211_STA_NONE));
 assert(m.join_retired && !m.join_running);
 /* Successful association configures BSS/RLM before requesting STA activation. */
 m=ready(&vif,&sta);assert(!mt6797_mac_join_add_peer(&m,&vif,&sta));
 m.join_auth_received=m.join_auth_ok=m.join_last_acked=true;
 assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_NONE,IEEE80211_STA_AUTH));
 m.join_assoc_received=true;m.join_aid=vif.cfg.aid=42;
 m.join_ssid_bytes=3;memcpy(m.join_ssid,"lab",3);
 assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_AUTH,IEEE80211_STA_ASSOC));
 assert(writes==5 && order[3]==0x12 && order[4]==0x13);
 assert(m.join_bss_configured && m.join_sta_active && !m.join_sta_pending);
 assert(!m.join_page_debt && !m.join_credit_pending && !locked);
 assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_ASSOC,IEEE80211_STA_AUTHORIZED));
 /* Accepted association: owned deauth precedes the three cleanup commands. */
 info.subtype=IEEE80211_STYPE_ASSOC_REQ;info.success=true;
 m.join_last_sequence=4095;
 mt6797_mac_mgd_complete_tx(&hw,&vif,&info);
 assert(m.join_cleanup_requested && m.join_open && m.join_internal && allocations==1);
 assert(m.join_internal->data[0]==0xc0 && m.join_internal->data[24]==3);
 assert(!m.join_internal->data[22] && !m.join_internal->data[23]);
 assert(!memcmp(m.join_internal->data+4,m.join_ap,6));
 assert(!memcmp(m.join_internal->data+10,m.hw->wiphy->perm_addr,6));
 struct sk_buff *owned=m.join_internal;
 /* These callbacks used to close the queued deauth gate. */
 mt6797_mac_mgd_complete_tx(&hw,&vif,&info);
 assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_ASSOC,IEEE80211_STA_AUTH));
 assert(m.join_open && m.join_internal==owned && !m.join_retired);
 mutex_lock(&m.mutex);assert(!mt6797_mac_join_cleanup_step(&m));mutex_unlock(&m.mutex);
 assert(writes==5);
 m.join_queue.head=NULL;m.join_inflight=owned;m.join_page_debt=1;
 mutex_lock(&m.mutex);assert(!mt6797_mac_join_cleanup_step(&m));mutex_unlock(&m.mutex);
 assert(writes==5);
 m.join_inflight=NULL;m.join_internal=NULL;m.join_page_debt=0;
 dev_kfree_skb(owned);
 mutex_lock(&m.mutex);assert(!mt6797_mac_join_cleanup_step(&m));mutex_unlock(&m.mutex);
 assert(writes==5); /* Returned credit alone cannot prove deauth completion. */
 m.join_deauth_done=true;
 for(unsigned stage=0;stage<3;stage++) {
  mutex_lock(&m.mutex);assert(!mt6797_mac_join_cleanup_step(&m));mutex_unlock(&m.mutex);
  assert(writes==6+stage && m.join_cleanup_stage==stage+1 && m.join_credit_pending);
  released=1;
  assert(!mt6797_mac_join_guard(&m,m.join_credit_deadline));released=0;
 }
 assert(order[5]==0x14 && order[6]==0x1c && order[7]==0x11 && !losses);
 /* EVENT_ID_BSS_ABSENCE_PRESENCE after the BSS-off submission: 12 bytes, seq 0,
  * BSS 0, boolean flag; the body is synthetic and source-defined, logged as
  * metadata, never credit. Admitted at most twice; every deviation refused. */
 { struct mt6797_mac saved=m; u8 *e=m.join_packet; absence_logs=0;
   memset(e,0,24);e[0]=12;e[3]=0xe0;e[4]=0x11;e[5]=0;e[8]=0;e[9]=1;e[10]=7;e[11]=0;
   mutex_lock(&m.mutex);assert(!mt6797_mac_join_control_event(&m,12));mutex_unlock(&m.mutex);
   assert(absence_logs==1 && absence_bss==0 && absence_flag==1 && absence_quota==7);
   assert(m.join_page_debt==0 && !m.join_credit_pending && m.join_cleanup_stage==3 && !m.join_cleanup_done);
   e[9]=0; mutex_lock(&m.mutex);assert(!mt6797_mac_join_control_event(&m,12));mutex_unlock(&m.mutex);
   assert(absence_logs==2 && absence_flag==0 && m.join_absence_events==2);
   mutex_lock(&m.mutex);assert(mt6797_mac_join_control_event(&m,12)==-EPROTO);mutex_unlock(&m.mutex); /* budget */
   m=saved; e=m.join_packet; m.join_absence_events=0;
   e[5]=1; assert(mt6797_mac_join_control_event(&m,12)==-EPROTO); e[5]=0;          /* a solicited sequence */
   e[8]=1; assert(mt6797_mac_join_control_event(&m,12)==-EPROTO); e[8]=0;          /* foreign BSS slot */
   e[9]=2; assert(mt6797_mac_join_control_event(&m,12)==-EPROTO); e[9]=1;          /* non-boolean flag */
   e[0]=16; assert(mt6797_mac_join_control_event(&m,16)==-EPROTO); e[0]=12;        /* wrong length */
   m.join_cleanup_stage=2; assert(mt6797_mac_join_control_event(&m,12)==-EPROTO); m.join_cleanup_stage=3; /* before BSS off */
   m.join_page_debt=1; assert(mt6797_mac_join_control_event(&m,12)==-EPROTO); m.join_page_debt=0;     /* page owed */
   m.join_inflight=(void*)1; assert(mt6797_mac_join_control_event(&m,12)==-EPROTO); m.join_inflight=NULL;
   m.join_cleanup_done=true; assert(mt6797_mac_join_control_event(&m,12)==-EPROTO); m.join_cleanup_done=false;
   assert(m.join_absence_events==0 && absence_logs==2);
   m=saved; }
 /* Stage 3 with the HIF not idle: the refusal is unchanged (-EPROTO, nothing
  * completed or submitted) and now names the ledger terms exactly once. */
 { struct mt6797_mac saved=m; idle=false;cleanup_logs=0;
   mutex_lock(&m.mutex);assert(mt6797_mac_join_cleanup_step(&m)==-EPROTO);mutex_unlock(&m.mutex);
   assert(!m.join_cleanup_done && !m.join_retired && writes==8 && !losses);
   assert(cleanup_logs==1 && cleanup_stage==3 && cleanup_free==25);
   m=saved;idle=true; }
 mutex_lock(&m.mutex);assert(!mt6797_mac_join_cleanup_step(&m));mutex_unlock(&m.mutex);
 assert(m.join_cleanup_done && m.join_retired && !m.join_running && losses==1);
 mutex_lock(&m.mutex);assert(!mt6797_mac_join_cleanup_step(&m));mutex_unlock(&m.mutex);
 assert(writes==8 && losses==1);
 /* Refusal destroys the host STA before mgd_complete; polling must survive. */
 m=ready(&vif,&sta);assert(!mt6797_mac_join_add_peer(&m,&vif,&sta));
 assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_NONE,IEEE80211_STA_NOTEXIST));
 assert(m.join_cleanup_requested && m.join_running && !m.join_retired && !allocations);
 info.success=false;mt6797_mac_mgd_complete_tx(&hw,&vif,&info);
 mutex_lock(&m.mutex);assert(!mt6797_mac_join_cleanup_step(&m));mutex_unlock(&m.mutex);
 assert(writes==4 && order[3]==0x14);
 for(unsigned failure=4;failure<=6;failure++) {
  m=ready(&vif,&sta);assert(!mt6797_mac_join_add_peer(&m,&vif,&sta));
  mutex_lock(&m.mutex);assert(!mt6797_mac_join_request_cleanup(&m));mutex_unlock(&m.mutex);
  fail_write=failure;
  for(unsigned stage=0;stage<failure-3;stage++) {
   mutex_lock(&m.mutex);int ret=mt6797_mac_join_cleanup_step(&m);mutex_unlock(&m.mutex);
   if(stage==failure-4) {
    assert(ret==-EIO && writes==failure && !m.join_cleanup_done);
    m.first_error=ret;m.closing=true;
    mutex_lock(&m.mutex);assert(mt6797_mac_join_cleanup_step(&m)==-ECANCELED);mutex_unlock(&m.mutex);
    assert(writes==failure);
   } else {
    assert(!ret);released=1;assert(!mt6797_mac_join_guard(&m,m.join_credit_deadline));
   }
  }
 }
 m=ready(&vif,&sta);assert(!mt6797_mac_join_add_peer(&m,&vif,&sta));
 m.join_sta_active=m.join_assoc_received=true;allocation_failure=true;
 mutex_lock(&m.mutex);assert(mt6797_mac_join_request_cleanup(&m)==-ENOMEM);mutex_unlock(&m.mutex);
 assert(writes==3 && !m.join_cleanup_requested && !allocations);
 /* Poison and exhausted time admit no teardown command or RF frame. */
 for(unsigned mode=0;mode<2;mode++) {
  m=ready(&vif,&sta);assert(!mt6797_mac_join_add_peer(&m,&vif,&sta));
  if(mode) now=m.join_deadline-100*NSEC_PER_MSEC;else m.first_error=-EIO;
  mutex_lock(&m.mutex);assert(mt6797_mac_join_request_cleanup(&m)<0);mutex_unlock(&m.mutex);
  assert(writes==3 && !m.join_cleanup_requested && !allocations);
 }
 for(unsigned failure=4;failure<=5;failure++) {
  m=ready(&vif,&sta);assert(!mt6797_mac_join_add_peer(&m,&vif,&sta));
  m.join_authenticated=true;m.join_last_acked=true;m.join_assoc_received=true;
  m.join_aid=vif.cfg.aid=42;m.join_ssid_bytes=3;memcpy(m.join_ssid,"lab",3);
  fail_write=failure;
  assert(mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_AUTH,IEEE80211_STA_ASSOC)==-EIO);
  assert(writes==failure && m.closing && m.first_error==-EIO);
 }
 m=ready(&vif,&sta);m.join_last_acked=true;m.join_inflight=&m;
 m.join_frame_deadline=now+750*NSEC_PER_MSEC;
 mutex_lock(&m.mutex);assert(!mt6797_mac_join_wait_management(&m));mutex_unlock(&m.mutex);
 assert(!m.join_inflight && waits==1 && !writes);
 /* Phase C2 keys. The standard supplicant hands message 4 to the driver
  * before installing the pairwise key, so set_key serializes on the ledger:
  * in flight (TX done then credit), or queued (the command goes first and the
  * reply waits for its credit). Pairwise before group, one of each, CCMP only;
  * anything else ends the lifetime fail-stop. DISABLE_KEY submits nothing. */
 { struct ieee80211_key_conf ptk={.cipher=WLAN_CIPHER_SUITE_CCMP,.keyidx=0,.keylen=16,.flags=IEEE80211_KEY_FLAG_PAIRWISE};
   struct ieee80211_key_conf gtk={.cipher=WLAN_CIPHER_SUITE_CCMP,.keyidx=0,.keylen=16,.flags=0};
   struct ieee80211_key_conf tkip={.cipher=0x000fac02,.keyidx=0,.keylen=32,.flags=IEEE80211_KEY_FLAG_PAIRWISE};
   static struct sk_buff reply;
   memset(ptk.key,0x41,16);memset(gtk.key,0x42,16);
   m=ready(&vif,&sta);active=&m;expect_wpa2=true;m.join_rsn=true;
   assert(!mt6797_mac_join_add_peer(&m,&vif,&sta));
   m.join_auth_received=m.join_auth_ok=m.join_last_acked=true;
   assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_NONE,IEEE80211_STA_AUTH));
   m.join_assoc_received=true;m.join_aid=vif.cfg.aid=42;m.join_ssid_bytes=3;memcpy(m.join_ssid,"lab",3);
   assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_AUTH,IEEE80211_STA_ASSOC));
   assert(writes==5 && m.join_sta_active && m.join_bss_configured);
   /* Message 4 in flight with its pages owed: the key waits for TX done and credit. */
   m.join_inflight=&reply;m.join_frame_deadline=now+750*NSEC_PER_MSEC;m.join_last_acked=false;m.join_page_debt=2;
   m.join_hold_until=now+4000*NSEC_PER_MSEC;
   assert(!mt6797_mac_set_key(&hw,SET_KEY,&vif,&sta,&ptk));
   assert(!m.join_inflight && m.join_last_acked && !m.join_page_debt && !m.join_credit_pending);
   assert(writes==6 && order[5]==0x07 && key_adds==1 && key_pairwise==1 && m.join_key_pairwise==1 && !m.join_key_group);
   assert(!locked && m.join_hold_until==now+4000*NSEC_PER_MSEC);
   /* A queued reply does not block the group key; the command goes first. */
   m.join_queue.head=&reply;
   assert(!mt6797_mac_set_key(&hw,SET_KEY,&vif,NULL,&gtk));m.join_queue.head=NULL;
   assert(writes==7 && order[6]==0x07 && key_adds==2 && key_group==1 && m.join_key_group==1 && m.join_group_key_id==0);
   assert(m.join_hold_until==now+1000*NSEC_PER_MSEC && !m.join_page_debt);
   /* Disable submits nothing; a second pairwise key is refused fail-stop. */
   assert(!mt6797_mac_set_key(&hw,DISABLE_KEY,&vif,&sta,&ptk) && writes==7);
   { struct mt6797_mac saved=m;
     assert(mt6797_mac_set_key(&hw,SET_KEY,&vif,&sta,&ptk)==-EOPNOTSUPP && m.first_error==-EOPNOTSUPP && m.join_retired && !m.join_running);
     m=saved; active=&m; }
   /* Healthy teardown: the deauthentication completes, then the two removals (exact
    * wlanoidSetRemoveKey shapes), then station removal, channel abort and BSS off. */
   info.subtype=IEEE80211_STYPE_ASSOC_REQ;info.success=true;m.join_last_sequence=4095;
   mt6797_mac_mgd_complete_tx(&hw,&vif,&info);
   assert(m.join_cleanup_requested && m.join_internal && allocations==1);
   { struct sk_buff *owned=m.join_internal; m.join_queue.head=NULL;m.join_inflight=NULL;m.join_internal=NULL;dev_kfree_skb(owned); }
   m.join_deauth_done=true;
   for(unsigned step=0;step<5;step++) {
    mutex_lock(&m.mutex);assert(!mt6797_mac_join_cleanup_step(&m));mutex_unlock(&m.mutex);
    assert(writes==8+step && m.join_credit_pending);
    released=1; assert(!mt6797_mac_join_guard(&m,m.join_credit_deadline)); released=0;
   }
   assert(order[7]==0x07 && order[8]==0x07 && order[9]==0x14 && order[10]==0x1c && order[11]==0x11);
   assert(key_removals==2 && key_pairwise==2 && key_group==2 && m.join_key_pairwise==2 && m.join_key_group==2);
   assert(m.join_cleanup_stage==3 && !m.join_cleanup_done && !losses);
   /* Refusals on fresh lifetimes: wrong cipher; group before pairwise. */
   m=ready(&vif,&sta);active=&m;expect_wpa2=true;m.join_rsn=true;
   assert(!mt6797_mac_join_add_peer(&m,&vif,&sta));m.join_auth_received=m.join_auth_ok=m.join_last_acked=true;
   assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_NONE,IEEE80211_STA_AUTH));
   m.join_assoc_received=true;m.join_aid=vif.cfg.aid=42;m.join_ssid_bytes=3;memcpy(m.join_ssid,"lab",3);
   assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_AUTH,IEEE80211_STA_ASSOC));
   { struct mt6797_mac saved=m;
     assert(mt6797_mac_set_key(&hw,SET_KEY,&vif,&sta,&tkip)==-EOPNOTSUPP && m.join_retired && writes==5);
     m=saved; active=&m;
     assert(mt6797_mac_set_key(&hw,SET_KEY,&vif,NULL,&gtk)==-EOPNOTSUPP && m.join_retired && writes==5);
     m=saved; active=&m; }
   /* Group key ids 1 to 3 are admitted as well (the AP's id is not measured). */
   m=ready(&vif,&sta);active=&m;expect_wpa2=true;m.join_rsn=true;
   assert(!mt6797_mac_join_add_peer(&m,&vif,&sta));m.join_auth_received=m.join_auth_ok=m.join_last_acked=true;
   assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_NONE,IEEE80211_STA_AUTH));
   m.join_assoc_received=true;m.join_aid=vif.cfg.aid=42;m.join_ssid_bytes=3;memcpy(m.join_ssid,"lab",3);
   assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_AUTH,IEEE80211_STA_ASSOC));
   m.join_hold_until=now+4000*NSEC_PER_MSEC;
   assert(!mt6797_mac_set_key(&hw,SET_KEY,&vif,&sta,&ptk));
   { struct ieee80211_key_conf gtk3=gtk; gtk3.keyidx=3; assert(!mt6797_mac_set_key(&hw,SET_KEY,&vif,NULL,&gtk3)); }
   assert(m.join_group_key_id==3 && writes==7);
   { struct ieee80211_key_conf gtk4=gtk; gtk4.keyidx=4; struct mt6797_mac saved=m;
     assert(mt6797_mac_set_key(&hw,SET_KEY,&vif,NULL,&gtk4)==-EOPNOTSUPP); m=saved; active=&m; }
   /* An open join declares no WPA2 and admits no key. */
   m=ready(&vif,&sta);active=&m;expect_wpa2=false;
   assert(!mt6797_mac_join_add_peer(&m,&vif,&sta));m.join_auth_received=m.join_auth_ok=m.join_last_acked=true;
   assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_NONE,IEEE80211_STA_AUTH));
   m.join_assoc_received=true;m.join_aid=vif.cfg.aid=42;m.join_ssid_bytes=3;memcpy(m.join_ssid,"lab",3);
   assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_AUTH,IEEE80211_STA_ASSOC));
   assert(mt6797_mac_set_key(&hw,SET_KEY,&vif,&sta,&ptk)==-EOPNOTSUPP && m.join_retired);
 }
}
