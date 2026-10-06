/* SPDX-License-Identifier: GPL-2.0-only */
/* Deterministic host interleavings, not a kernel concurrency or firmware model. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
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
enum ieee80211_sta_state { IEEE80211_STA_NOTEXIST, IEEE80211_STA_NONE,
 IEEE80211_STA_AUTH, IEEE80211_STA_ASSOC, IEEE80211_STA_AUTHORIZED };
struct ieee80211_hw { void *priv; };
struct ieee80211_prep_tx_info { unsigned subtype, link_id; bool success; };
#define min(a,b) ((a)<(b)?(a):(b))
#define min_t(t,a,b) min((t)(a),(t)(b))
#define spin_lock_irqsave(lock,flags) do { (void)(lock); (flags)=0; } while (0)
#define spin_unlock_irqrestore(lock,flags) do { (void)(lock); (void)(flags); } while (0)
struct completion { unsigned count; };
struct ieee80211_vif { unsigned valid_links; };
struct ieee80211_sta { bool mlo; unsigned valid_links; u8 addr[6];
 struct { unsigned supp_rates[2]; } deflink; };
struct mt6797_hif { int unused; };
struct mt6797_hif_tx_status { int unused; };
struct mt6797_normal_release { unsigned released_pages; };
struct mt6797_mac {
 struct mt6797_hif *hif; struct ieee80211_vif *vif;
 int mutex, scan_work; struct { int lock; } join_queue;
 bool scan_active, join_scan_ready, started, configured, bss_active;
 bool join_running, join_bss_valid, join_channel_valid, join_peer_used;
 bool join_retired, closing, join_open, join_peer_ready;
 bool join_authenticated, join_auth_received, join_auth_ok, join_assoc_received;
 unsigned join_seen, join_tx_allowed, join_rx_allowed;
 bool join_credit_pending, join_channel_pending, join_channel_granted;
 bool join_sta_pending, join_sta_active;
 unsigned join_page_debt, sequence, join_requested_ms, join_basic_rates;
 unsigned join_desired_rates, join_peer_basic_rates;
 u8 join_ap[6], join_bssid[6], join_channel_token, join_sta_sequence;
 u8 join_packet[24]; int first_error;
 u64 join_deadline, join_grant_deadline, join_credit_deadline;
 struct completion join_credit_done, join_channel_done, join_sta_done;
};
static struct mt6797_mac *active;
static u64 now;
static unsigned locked, writes, waits, fail_write, fail_wait, released;
static unsigned order[3];
static int wait_mode;
static bool idle;
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
static void ether_addr_copy(u8 *a,const u8 *b) { memcpy(a,b,6); }
static bool mt6797_hif_normal_idle(struct mt6797_hif *h) { assert(h); return idle; }
static int mt6797_hif_read32(struct mt6797_hif *h,unsigned reg,u64 d,u32 *v)
{ assert(h && d>now); *v=reg ? BIT(8) : 0x0279|BIT(21); return 0; }
static int mt6797_hif_reconcile_runtime(struct mt6797_hif *h,u64 d,
 struct mt6797_hif_tx_status *s,struct mt6797_normal_release *a)
{ assert(h && d>now && s); a->released_pages=released; return 0; }
static int command(unsigned kind,unsigned sequence,u64 deadline)
{ assert(locked && deadline>now && sequence==5+writes && writes<3);
 order[writes++]=kind; return writes==fail_write ? -EIO : 0; }
static int mt6797_hif_join_filter(struct mt6797_hif *h,unsigned s,u64 d)
{ assert(h && active->join_page_debt==1); return command(0x0a,s,d); }
static int mt6797_hif_join_channel(struct mt6797_hif *h,unsigned s,u8 token,
 u8 channel,unsigned ms,bool abort,u64 d)
{ assert(h && token==1 && channel==40 && ms==9000 && !abort);
 assert(active->join_page_debt==1); return command(0x1c,s,d); }
static int mt6797_hif_join_station(struct mt6797_hif *h,unsigned s,const u8 *ap,
 unsigned state,unsigned aid,unsigned desired,unsigned basic,u64 d)
{ assert(h && state==1 && !aid && desired==0x3fc0 && basic==0x40);
 assert(active->join_page_debt==2 && ether_addr_equal(ap,active->join_bssid));
 return command(0x13,s,d); }
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
 } else {
  assert(c==&active->join_channel_done);
  memset(active->join_packet,0,24);
  u8 *p=active->join_packet;
  p[0]=24;p[3]=0xe0;p[4]=0x10;p[9]=1;p[11]=40;p[13]=2;
  p[20]=9000&255;p[21]=9000>>8;
  assert(!mt6797_mac_join_control_event(active,24));
 }
 return 1;
}
static struct mt6797_mac ready(struct ieee80211_vif *vif,struct ieee80211_sta *sta)
{
 static struct mt6797_hif hif;
 now=NSEC_PER_SEC; writes=waits=locked=fail_write=fail_wait=released=0;
 idle=true; wait_mode=0;
 memset(sta,0,sizeof(*sta)); sta->addr[0]=2;sta->addr[5]=7;
 sta->deflink.supp_rates[1]=255;
 struct mt6797_mac m={.hif=&hif,.vif=vif,.started=true,.configured=true,
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
 assert(mt6797_mac_join_add_peer(&m,&vif,&sta)==-EOPNOTSUPP && writes==3);
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
 m=ready(&vif,&sta);idle=false;
 assert(mt6797_mac_join_add_peer(&m,&vif,&sta)==-EOPNOTSUPP && !writes);
 m=ready(&vif,&sta);m.sequence=254;
 assert(mt6797_mac_join_add_peer(&m,&vif,&sta)==-EOPNOTSUPP && !writes);
 m=ready(&vif,&sta);m.join_page_debt=2;m.join_credit_pending=true;
 m.join_credit_deadline=now+100*NSEC_PER_MSEC;released=1;
 assert(!mt6797_mac_join_guard(&m,m.join_credit_deadline));
 assert(m.join_page_debt==1 && !m.join_credit_done.count);
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
 m.join_seen=BIT(11);m.join_auth_received=true;m.join_auth_ok=true;
 assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_NONE,IEEE80211_STA_AUTH));
 info.success=true;mt6797_mac_mgd_complete_tx(&hw,&vif,&info);
 assert(!m.join_open && !m.first_error && m.join_authenticated);
 info.subtype=IEEE80211_STYPE_ASSOC_REQ;mt6797_mac_mgd_prepare_tx(&hw,&vif,&info);
 assert(m.join_open && m.join_tx_allowed==BIT(0) && (m.join_rx_allowed&BIT(1)));
 m.join_seen|=BIT(0);mt6797_mac_mgd_prepare_tx(&hw,&vif,&info);
 assert(!m.join_open && m.first_error==-EOPNOTSUPP && !writes);
 assert(!mt6797_mac_sta_state(&hw,&vif,&sta,IEEE80211_STA_AUTH,IEEE80211_STA_NONE));
 assert(m.join_retired && !m.join_running);
}
