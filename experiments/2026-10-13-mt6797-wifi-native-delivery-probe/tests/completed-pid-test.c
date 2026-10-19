/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
#define dev_info(...) ((void)0)
#include "actual-pid-pool.inc"
#include "join-events.h"
struct mt6797_mac {
 bool first_error, closing, join_retired, join_credit_pending, join_data_ended;
 bool ccmp_reserved_pid_used;
 unsigned int join_page_debt, join_data_page_debt, ccmp_unowned_tx_done;
 unsigned char join_pid, join_next_pid, join_packet[24];
 void *join_inflight;
 struct mt6797_join_pid_pool ccmp_pid_pool;
};
static bool ccmp_stable_epoch = true;
#include "actual-assign.inc"
/* The exact outer shape check is retained; worker-local rx size becomes bytes. */
#define rx actual_rx
static struct { size_t logical_bytes; } actual_rx;
#include "actual-complete.inc"
#undef rx
static struct mt6797_mac ready(void)
{
 struct mt6797_mac m = { .join_next_pid = 1 };
 m.ccmp_pid_pool.next = 1;
 return m;
}
static void event(struct mt6797_mac *m, unsigned char pid, unsigned char wlan, unsigned char status)
{
 memset(m->join_packet, 0, sizeof(m->join_packet));
 m->join_packet[0]=24; m->join_packet[3]=0xe0; m->join_packet[4]=0x0f;
 m->join_packet[8]=pid; m->join_packet[9]=status; m->join_packet[12]=wlan;
 actual_rx.logical_bytes=24;
}
int main(void)
{
 struct mt6797_join_pid_pool p = { .next = 1 }, before;
 struct mt6797_mac m, old;
 unsigned int i, n;
 unsigned char pid;
 for (i=0;i<8192;i++) {
  pid=mt6797_join_pid_take(&p); assert(pid==i%126+1 && pid!=127);
  before=p; assert(!mt6797_join_pid_take(&p) && !memcmp(&p,&before,sizeof(p)));
  for (n=0;n<128;n++) if (n!=pid) {
   before=p; assert(!mt6797_join_pid_complete(&p,n) && !memcmp(&p,&before,sizeof(p)));
  }
  assert(mt6797_join_pid_complete(&p,pid));
  before=p; assert(!mt6797_join_pid_complete(&p,pid) && !memcmp(&p,&before,sizeof(p)));
 }
 assert(p.allocations==8192 && p.completions==8192 && p.wraps==8192/126);
 assert(!mt6797_join_pid_take(NULL) && !mt6797_join_pid_complete(NULL,1));
 p=(struct mt6797_join_pid_pool){.next=1,.allocations=~0U,.completions=~0U};
 before=p; assert(!mt6797_join_pid_take(&p) && !memcmp(&p,&before,sizeof(p)));
 p=(struct mt6797_join_pid_pool){.next=1,.used={[1]=true}};
 before=p; assert(!mt6797_join_pid_take(&p) && !memcmp(&p,&before,sizeof(p)));
 for (i=0;i<8;i++) {
  m=ready();
  if(i==0)m.first_error=true;
  if(i==1)m.closing=true;
  if(i==2)m.join_retired=true;
  if(i==3)m.join_credit_pending=true;
  if(i==4)m.join_page_debt=1;
  if(i==5)m.join_data_page_debt=1;
  if(i==6)m.join_data_ended=true;
  if(i==7)m.ccmp_reserved_pid_used=true;
  old=m; assert(mt6797_ccmp_assign_pid(&m,false)<0 && !memcmp(&m,&old,sizeof(m)));
 }
 m=ready(); assert(!mt6797_ccmp_assign_pid(&m,false) && m.join_pid==1);
 m.join_inflight=&m; event(&m,1,1,0);
 assert(!actual_complete(&m,24));
 assert(!m.ccmp_pid_pool.pending && m.ccmp_pid_pool.completions==1);
 assert(!mt6797_ccmp_assign_pid(&m,true) && m.join_pid==127 && m.join_next_pid==2);
 old=m; assert(mt6797_ccmp_assign_pid(&m,true)<0 && !memcmp(&m,&old,sizeof(m)));
 m=ready(); assert(!mt6797_ccmp_assign_pid(&m,false));
 old=m; assert(mt6797_ccmp_assign_pid(&m,true)<0 && !memcmp(&m,&old,sizeof(m)));
 /* Integrated MAC ownership wraps without tripping the old cursor ceiling. */
 m=ready();
 for(i=0;i<8192;i++) {
  assert(!mt6797_ccmp_assign_pid(&m,false));
  assert(m.join_pid==i%126+1 && m.join_next_pid>=1 && m.join_next_pid<=126);
  m.join_inflight=&m; event(&m,m.join_pid,1,0);
  assert(!actual_complete(&m,24));
  m.join_inflight=NULL;
 }
 assert(m.ccmp_pid_pool.allocations==8192 && m.ccmp_pid_pool.completions==8192);
 m.join_data_page_debt=1; old=m;
 assert(mt6797_ccmp_assign_pid(&m,false)==-EBUSY && !memcmp(&m,&old,sizeof(m)));
 m.join_data_page_debt=0; assert(!mt6797_ccmp_assign_pid(&m,false));
 m=ready(); assert(!mt6797_ccmp_assign_pid(&m,false));
 /* No completion -> no recycle, including after credit return and time passage. */
 for(i=0;i<256;i++)assert(mt6797_ccmp_assign_pid(&m,false)<0);
 assert(m.ccmp_pid_pool.pending==1 && m.ccmp_pid_pool.allocations==1);
 /* Valid unowned events never retire the currently awaited owner. */
 m.join_inflight=&m;
 for(i=0;i<256;i++) if(i!=1) {
  event(&m,i,1,0); assert(actual_complete(&m,24)==1 && m.ccmp_pid_pool.pending==1);
 }
 event(&m,1,2,0); assert(actual_complete(&m,24)==1 && m.ccmp_pid_pool.pending==1);
 event(&m,1,1,255); assert(actual_complete(&m,24)==-EPROTO && m.ccmp_pid_pool.pending==1);
 event(&m,1,1,0); assert(actual_complete(&m,23)==-EPROTO && m.ccmp_pid_pool.pending==1);
 m.join_packet[4]=0x10; assert(actual_complete(&m,24)==-EPROTO);
 for(i=0;i<=34;i++) {
  m=ready(); assert(!mt6797_ccmp_assign_pid(&m,false)); m.join_inflight=&m;
  event(&m,1,1,i);
  if(i<=7 || i>=32) assert(!actual_complete(&m,24) && m.ccmp_pid_pool.completions==1);
  else assert(actual_complete(&m,24)==-EPROTO && m.ccmp_pid_pool.pending==1);
 }
 ccmp_stable_epoch=false; m=ready();
 assert(!mt6797_ccmp_assign_pid(&m,false) && m.join_pid==1 && m.join_next_pid==2);
 assert(!m.ccmp_pid_pool.allocations);
 puts("completed PID actual-source 8192 allocations/wrap, pending/credit/poison/reserved, unknown and malformed cases PASS");
 return 0;
}
