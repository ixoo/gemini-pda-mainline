/* SPDX-License-Identifier: GPL-2.0-only */
#define MT6797_HIF_HOST_TEST
#include <stdio.h>
#include <string.h>
#include "hif.c"

static struct {
 unsigned int calls, fail_at, setup, transfer;
 unsigned char frame[1024], *mapping;
} fake;
u64 ktime_get_ns(void) { return 1000; }
void usleep_range(unsigned long low, unsigned long high) { assert(low == 50 && high == 100); }
int mt6797_test_read(void *address, unsigned int *value)
{
 (void)value; (void)address; assert(false); return -EIO;
}
int mt6797_test_write(unsigned int value, void *address)
{
 unsigned int i=fake.calls++, expected=fake.setup;
 assert(i <= fake.transfer/4);
 assert((unsigned char *)address-fake.mapping == (i ? 0x1000 : 0));
 if(i) {
  unsigned int b=4*(i-1);
  expected=(unsigned int)fake.frame[b] | ((unsigned int)fake.frame[b+1]<<8) |
   ((unsigned int)fake.frame[b+2]<<16) | ((unsigned int)fake.frame[b+3]<<24);
 }
 assert(value==expected);
 return fake.calls==fake.fail_at ? -EIO : 0;
}
static int submit(struct mt6797_hif *hif, enum mt6797_normal_config_kind kind,
 unsigned int sequence, unsigned int length, unsigned int fail_at)
{
 unsigned char payload[512];
 unsigned int bytes=length+8;
 for(unsigned int i=0;i<length;i++) payload[i]=i^0x5a;
 memset(fake.frame,0,sizeof(fake.frame));
 fake.frame[0]=bytes; fake.frame[1]=bytes>>8; fake.frame[3]=0x80;
 fake.frame[4]=kind; fake.frame[5]=0xa0; fake.frame[6]=1; fake.frame[7]=sequence;
 memcpy(fake.frame+8,payload,length);
 fake.calls=0; fake.fail_at=fail_at;
 fake.transfer=length==512 ? 1024 : bytes;
 fake.setup=length==512 ? 0x98006802 : length==56 ? 0x90006840 : 0x90006828;
 return mt6797_hif_send_config(hif,kind,sequence,payload,length,1000001000ULL);
}
static void exercise(bool control_failure, unsigned int fail_at)
{
 struct mt6797_init_transaction transaction={.phase=MT6797_INIT_IDLE};
 struct mt6797_hif *hif;
 int ret;
 unsigned int expected_calls;
 memset(&fake,0,sizeof(fake)); fake.mapping=calloc(1,0x1004); assert(fake.mapping);
 hif=mt6797_hif_alloc(fake.mapping,0x1004,&transaction); assert(!IS_ERR(hif));
 hif->firmware_ready=true; hif->capability_complete=true;
 transaction.used_sequences[0]=0x1e;
 assert(!mt6797_normal_admit(&hif->normal,26,25,transaction.used_sequences));
 hif->normal.phase=MT6797_NORMAL_CAP_RECEIVED;
 ret=submit(hif,MT6797_NORMAL_NVRAM_SETTINGS,5,512,control_failure ? 0 : fail_at);
 expected_calls=fail_at ? fail_at : 257;
 if(control_failure || !fail_at) {
  assert(!ret && fake.calls==257 && hif->normal.tc4_free==20);
  assert(hif->normal.phase==MT6797_NORMAL_NVRAM_SUBMITTED);
  assert(!submit(hif,MT6797_NORMAL_DOMAIN,6,56,0));
  assert(fake.calls==17 && hif->normal.tc4_free==19);
  assert(hif->normal.phase==MT6797_NORMAL_NVRAM_SUBMITTED);
  ret=submit(hif,MT6797_NORMAL_TX_CTRL,7,32,control_failure ? fail_at : 0);
  expected_calls=fail_at ? fail_at : 11;
  assert(hif->normal.tc4_free==18 && transaction.used_sequences[0]==0xfe);
 } else {
  assert(hif->normal.tc4_free==20 && transaction.used_sequences[0]==0x3e);
 }
 assert(fake.calls==expected_calls);
 if(fail_at) {
  unsigned char power[32]={0};
  assert(ret==-EIO && hif->normal.phase==MT6797_NORMAL_FAILED);
  assert(transaction.phase==MT6797_INIT_POISONED);
  assert(mt6797_hif_send_config(hif,MT6797_NORMAL_TX_CTRL,8,power,32,1000001000ULL)==-EIO);
  assert(fake.calls==expected_calls);
 } else {
  assert(!ret && transaction.phase==MT6797_INIT_IDLE);
  assert(hif->normal.phase==MT6797_NORMAL_NVRAM_SUBMITTED);
 }
 mt6797_hif_free(hif); free(fake.mapping);
}
int main(void)
{
 exercise(false,0);
 for(unsigned int i=1;i<=257;i++) exercise(false,i);
 for(unsigned int i=1;i<=11;i++) exercise(true,i);
 puts("retained record/regulatory HIF: pass, 268 injected write failures"); return 0;
}
