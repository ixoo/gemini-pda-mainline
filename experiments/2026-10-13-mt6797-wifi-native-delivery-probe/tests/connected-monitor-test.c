/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
typedef uint64_t u64;
#define IS_ENABLED(x) x
#define NSEC_PER_MSEC 1000000ULL
#define MT6797_JOIN_TEARDOWN_MARGIN_MS 5000U
#define MT6797_ND_ACTIVE 2U
#define IEEE80211_VIF_BEACON_FILTER 1U
#define NL80211_IFTYPE_STATION 2U
#define min(a,b) ((a)<(b)?(a):(b))
#define rcu_access_pointer(p) (p)
#define wiphy_dev(p) (p)
struct wiphy { unsigned char perm_addr[6]; };
struct ieee80211_hw { void *priv; struct wiphy *wiphy; };
struct ieee80211_vif { unsigned int type, driver_flags; unsigned char addr[6]; };
struct mt6797_mac {
 bool ccmp_closed, ccmp_decap, closing, join_retired, join_data_phase, join_data_ended;
 bool join_running, join_sta_active, join_bss_valid, join_bss_configured, ccmp_pm_connected;
 bool ccmp_loss_reported, started, scan_ready, scan_used;
 int first_error, mutex;
 struct { bool active, authorized; } ccmp_rx;
 void *ccmp_sta, *ccmp_ptk;
 struct ieee80211_hw *hw;
 struct ieee80211_vif *vif;
 unsigned int native_diag_state, join_key_pairwise, join_key_group;
 unsigned int ccmp_queued, ccmp_timeout_observed, join_beacons_delivered, join_beacon_interval;
 unsigned int join_data_rx_unicast, join_data_rx_group, join_data_rx_dropped;
 unsigned int join_data_tx_queued, join_data_tx_done, join_data_tx_failed, join_data_credits;
 unsigned int join_data_g1_uni_present, join_data_g1_uni_absent, join_data_g1_grp_present;
 unsigned int join_data_g1_grp_absent, join_data_uni_masks, join_data_grp_masks;
 u64 ccmp_pm_credit_ns, ccmp_last_checked_rx, ccmp_last_beacon_rx;
 u64 join_deadline, join_hold_until, join_data_started;
 const char *join_data_end_reason;
 unsigned char join_packet[24];
};
static bool ccmp_stable_epoch = true;
static u64 test_now = 100000000000ULL;
static unsigned int reports, beacon_ends, closes;
static u64 ktime_get_ns(void) { return test_now; }
static void dev_info(void *dev, const char *fmt, ...) { (void)dev; (void)fmt; }
static void mutex_lock(int *p) { (void)p; }
static void mutex_unlock(int *p) { (void)p; }
static bool ether_addr_equal(const void *a, const void *b) { return !memcmp(a,b,6); }
static void ieee80211_connection_loss(struct ieee80211_vif *vif) { assert(vif); reports++; }
static void mt6797_ccmp_data_end_beacons(struct mt6797_mac *m)
{
 assert(m->join_data_ended && m->join_deadline==test_now+5000000000ULL);
 assert(m->ccmp_timeout_observed==1); beacon_ends++;
}
static void mt6797_mac_join_close(struct mt6797_mac *m) { (void)m; closes++; }
static void mt6797_mac_cancel_scan(struct ieee80211_hw *hw, struct ieee80211_vif *vif) { (void)hw; (void)vif; }
#include "join-events.h"
#include "actual-ready.inc"
#include "actual-observe.inc"
#include "actual-end.inc"
#include "actual-lost.inc"
#include "actual-owned.inc"
#include "actual-add.inc"
#include "actual-remove.inc"
static struct wiphy wiphy;
static struct ieee80211_hw hw={.wiphy=&wiphy};
static struct ieee80211_vif vif;
static struct mt6797_mac ready(void)
{
 struct mt6797_mac m = { .ccmp_decap=true, .join_data_phase=true, .join_running=true,
  .join_sta_active=true, .join_bss_valid=true, .join_bss_configured=true,
  .ccmp_pm_connected=true, .started=true, .native_diag_state=2,
  .join_key_pairwise=1, .join_key_group=1, .ccmp_pm_credit_ns=1,
  .join_deadline=UINT64_MAX, .ccmp_queued=1, .join_beacons_delivered=1,
  .join_beacon_interval=100, .hw=&hw, .vif=&vif, .ccmp_sta=&vif, .ccmp_ptk=&vif };
 m.ccmp_rx.active=m.ccmp_rx.authorized=true;
 m.join_packet[0]=12; m.join_packet[3]=0xe0; m.join_packet[4]=0x13;
 return m;
}
int main(void)
{
 struct mt6797_mac m, old;
 unsigned int i, n;
 for(i=0;i<256;i++) {
  m=ready(); m.join_packet[9]=i; m.join_packet[10]=0xa5; m.join_packet[11]=0x5a;
  reports=beacon_ends=0;
  assert(mt6797_ccmp_owned_loss(&m,12));
  assert(reports==1 && beacon_ends==1 && m.ccmp_timeout_observed==1);
  assert(m.join_deadline==test_now+5000000000ULL && m.join_hold_until==test_now);
  assert(m.join_data_ended && !strcmp(m.join_data_end_reason,"connection-loss"));
  assert(!m.first_error && !m.closing);
  assert(!mt6797_ccmp_owned_loss(&m,12) && reports==1);
  mt6797_ccmp_connection_lost(&m,"cleanup"); assert(reports==1);
 }
 for(i=0;i<25;i++) if(i!=12) {
  m=ready();old=m;assert(!mt6797_ccmp_owned_loss(&m,i) && !memcmp(&m,&old,sizeof(m)));
 }
 for(i=0;i<256;i++) if(i) {
  m=ready();m.join_packet[8]=i;old=m;assert(!mt6797_ccmp_owned_loss(&m,12) && !memcmp(&m,&old,sizeof(m)));
  m=ready();m.join_packet[5]=i;old=m;assert(!mt6797_ccmp_owned_loss(&m,12) && !memcmp(&m,&old,sizeof(m)));
 }
 for(i=0;i<23;i++) {
  m=ready();
  switch(i) {
  case 0:m.ccmp_closed=true;break;
  case 1:m.ccmp_decap=false;break;
  case 2:m.closing=true;break;
  case 3:m.first_error=-EIO;break;
  case 4:m.join_retired=true;break;
  case 5:m.join_data_phase=false;break;
  case 6:m.join_data_ended=true;break;
  case 7:m.ccmp_rx.active=false;break;
  case 8:m.ccmp_rx.authorized=false;break;
  case 9:m.ccmp_sta=NULL;break;
  case 10:m.ccmp_ptk=NULL;break;
  case 11:m.native_diag_state=1;break;
  case 12:m.join_running=false;break;
  case 13:m.join_sta_active=false;break;
  case 14:m.join_bss_valid=false;break;
  case 15:m.join_bss_configured=false;break;
  case 16:m.ccmp_pm_connected=false;break;
  case 17:m.ccmp_pm_credit_ns=0;break;
  case 18:m.join_key_group=2;break;
  case 19:m.ccmp_loss_reported=true;break;
  case 20:m.started=false;break;
  case 21:m.vif=NULL;break;
  case 22:m.join_key_pairwise=2;break;
  }
  old=m; assert(!mt6797_ccmp_owned_loss(&m,12) && !memcmp(&m,&old,sizeof(m)));
 }
 ccmp_stable_epoch=false;m=ready();old=m;assert(!mt6797_ccmp_owned_loss(&m,12) && !memcmp(&m,&old,sizeof(m)));
 ccmp_stable_epoch=true;
 for(i=0;i<4;i++) {
  m=ready();m.vif=NULL;m.scan_ready=true;hw.priv=&m;memset(&vif,0,sizeof(vif));
  vif.type=NL80211_IFTYPE_STATION;vif.driver_flags=0x100;
  if(i==1)vif.type=1;
  if(i==2)vif.addr[0]=1;
  if(i==3)m.scan_ready=false;
  n=mt6797_mac_add_interface(&hw,&vif);
  if(i) { assert((int)n==-EOPNOTSUPP && vif.driver_flags==0x100 && !m.vif); }
  else {
   assert(!n && vif.driver_flags==(0x100|IEEE80211_VIF_BEACON_FILTER) && m.vif==&vif);
   mt6797_mac_remove_interface(&hw,&vif);
   assert(vif.driver_flags==0x100 && !m.vif && m.closing && closes==1);
  }
 }
 puts("connected monitor actual-source owned body/reasons, predata/stale/poison refusal, once-only loss and VIF flag PASS");
 return 0;
}
