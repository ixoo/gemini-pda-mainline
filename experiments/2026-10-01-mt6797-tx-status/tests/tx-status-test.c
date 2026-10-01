/* SPDX-License-Identifier: GPL-2.0-only */
#define MT6797_HIF_HOST_TEST
#include <stdio.h>
#include <string.h>
#include "hif.c"

static struct {
 unsigned int calls, fail_at, reads, fatal;
 unsigned char *mapping;
} fake;
u64 ktime_get_ns(void) { return 1000; }
void usleep_range(unsigned long low, unsigned long high) { assert(low == 50 && high == 100); }
static unsigned int reg(unsigned int n) { return n == 0 ? 0x0c : n == 1 ? 0x10 : 0x130 + (n-2)*4; }
int mt6797_test_write(unsigned int value, void *address)
{
 unsigned int n=fake.calls++;
 assert(!(n%2) && n<40);
 assert((unsigned char *)address-fake.mapping == 0);
 assert(value == (0x10000004U | (reg((n%20)/2)<<9)));
 return fake.calls == fake.fail_at ? -EIO : 0;
}
int mt6797_test_read(void *address, unsigned int *value)
{
 unsigned int n=fake.calls++;
 assert(n%2 && n<40);
 assert((unsigned char *)address-fake.mapping == 0x1000);
 if(fake.calls == fake.fail_at) return -EIO;
 *value=0x76540000U+n/2;
 if(n%20==3) *value |= fake.fatal;
 fake.reads++;
 return 0;
}
static void exercise(unsigned int fail_at, bool post_record)
{
 struct mt6797_init_transaction transaction={.phase=MT6797_INIT_IDLE};
 struct mt6797_hif_tx_status status[2];
 unsigned int count=post_record ? 2 : 1;
 struct mt6797_hif *hif;
 unsigned int calls, valid;
 memset(&fake,0,sizeof(fake)); fake.mapping=calloc(1,0x1004); assert(fake.mapping);
 hif=mt6797_hif_alloc(fake.mapping,0x1004,&transaction); assert(!IS_ERR(hif));
 hif->firmware_ready=true;
 if(post_record) {
  hif->tx_status_boot_attempted=true; hif->capability_attempted=true; hif->capability_complete=true;
  assert(!mt6797_normal_admit(&hif->normal,26,14,transaction.used_sequences));
  hif->normal.phase=MT6797_NORMAL_NVRAM_SUBMITTED;
 }
 fake.fail_at=fail_at;
 int ret=mt6797_hif_observe_tx_status(hif,1000001000ULL,count,status);
 calls=fail_at ? fail_at : 20*count;
 assert(fake.calls==calls);
 for(unsigned int n=0;n<count;n++) {
  unsigned int read_calls=fail_at ? fail_at-1 : 20*count;
  if(read_calls>20*(n+1)) read_calls=20*(n+1);
  read_calls=read_calls>20*n ? read_calls-20*n : 0;
  valid=(1U<<(read_calls/2))-1;
  assert(status[n].valid_words==valid);
  if(valid&1) assert(status[n].whcr==0x76540000+10*n);
  if(valid&2) assert(status[n].whisr==0x76540001+10*n);
  for(unsigned int i=0;i<8;i++) if(valid&(1U<<(i+2))) assert(status[n].wtqcr[i]==0x76540002+10*n+i);
 }
 if(post_record) assert(hif->normal.tc4_free==14 && hif->normal.tc4_limit==26);
 if(fail_at) {
  assert(ret==-EIO && transaction.phase==MT6797_INIT_POISONED);
  if(post_record) assert(hif->normal.phase==MT6797_NORMAL_FAILED);
  assert(mt6797_hif_observe_tx_status(hif,1000001000ULL,count,status)==-EIO);
  assert(fake.calls==calls && !status[0].valid_words);
 } else {
  assert(!ret && transaction.phase==MT6797_INIT_IDLE);
  unsigned int prior=fake.calls;
  assert(mt6797_hif_observe_tx_status(hif,1000001000ULL,count,status)==-EIO);
  assert(fake.calls==prior && !status[0].valid_words);
 }
 mt6797_hif_free(hif); free(fake.mapping);
}
static void fatal_status(unsigned int flag)
{
 struct mt6797_init_transaction transaction={.phase=MT6797_INIT_IDLE};
 struct mt6797_hif_tx_status status;
 memset(&fake,0,sizeof(fake)); fake.mapping=calloc(1,0x1004); assert(fake.mapping);
 struct mt6797_hif *hif=mt6797_hif_alloc(fake.mapping,0x1004,&transaction); assert(!IS_ERR(hif));
 hif->firmware_ready=true; fake.fatal=flag;
 assert(mt6797_hif_observe_tx_status(hif,1000001000ULL,1,&status)==-EIO);
 assert(status.valid_words==3 && fake.calls==4 && transaction.phase==MT6797_INIT_POISONED);
 assert(status.whisr & flag);
 mt6797_hif_free(hif); free(fake.mapping);
}
static void deadline_refusal(u64 deadline)
{
 struct mt6797_init_transaction transaction={.phase=MT6797_INIT_IDLE};
 struct mt6797_hif_tx_status status[2]={{.valid_words=123}};
 memset(&fake,0,sizeof(fake)); fake.mapping=calloc(1,0x1004); assert(fake.mapping);
 struct mt6797_hif *hif=mt6797_hif_alloc(fake.mapping,0x1004,&transaction); assert(!IS_ERR(hif));
 hif->firmware_ready=true;
 int expected=deadline<=1000 ? -ETIMEDOUT : -EINVAL;
 assert(mt6797_hif_observe_tx_status(hif,deadline,1,status)==expected);
 assert(!status[0].valid_words && !fake.calls && transaction.phase==MT6797_INIT_POISONED);
 mt6797_hif_free(hif); free(fake.mapping);
}
static void refusal(void)
{
 struct mt6797_init_transaction transaction={.phase=MT6797_INIT_IDLE};
 struct mt6797_hif_tx_status status[2]={{.valid_words=123}};
 memset(&fake,0,sizeof(fake)); fake.mapping=calloc(1,0x1004); assert(fake.mapping);
 struct mt6797_hif *hif=mt6797_hif_alloc(fake.mapping,0x1004,&transaction); assert(!IS_ERR(hif));
 assert(mt6797_hif_observe_tx_status(hif,1000001000ULL,1,status)==-EIO && !status[0].valid_words && !fake.calls);
 hif->firmware_ready=true; hif->normal.phase=MT6797_NORMAL_NVRAM_SUBMITTED;
 assert(mt6797_hif_observe_tx_status(hif,1000001000ULL,1,status)==-EIO && !fake.calls);
 hif->normal.phase=MT6797_NORMAL_COLD; hif->capability_attempted=true;
 assert(mt6797_hif_observe_tx_status(hif,1000001000ULL,1,status)==-EIO && !fake.calls);
 hif->capability_attempted=false;
 assert(mt6797_hif_observe_tx_status(hif,1000001000ULL,2,status)==-EIO && !fake.calls);
 assert(mt6797_hif_observe_tx_status(hif,1000001000ULL,0,status)==-EINVAL && !fake.calls);
 assert(mt6797_hif_observe_tx_status(hif,1000001000ULL,3,status)==-EINVAL && !fake.calls);
 hif->mutex.held=true;
 assert(mt6797_hif_observe_tx_status(hif,1000001000ULL,1,status)==-EBUSY && !fake.calls);
 hif->mutex.held=false;
 assert(mt6797_hif_observe_tx_status(NULL,1000001000ULL,1,status)==-EINVAL && !status[0].valid_words);
 assert(mt6797_hif_observe_tx_status(hif,1000001000ULL,1,NULL)==-EINVAL && !fake.calls);
 mt6797_hif_free(hif); free(fake.mapping);
}
int main(void)
{
 fatal_status(1U<<6); fatal_status(1U<<31);
 refusal(); deadline_refusal(1000); deadline_refusal(1000001001ULL); exercise(0,false); exercise(0,true);
 for(unsigned int i=1;i<=20;i++) exercise(i,false);
 for(unsigned int i=1;i<=40;i++) exercise(i,true);
 puts("TX status: pass; 60 injected read/setup failures; no credit refund"); return 0;
}
