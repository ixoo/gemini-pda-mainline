/* SPDX-License-Identifier: GPL-2.0-only */
#define MT6797_HIF_HOST_TEST
#include <string.h>
#include "hif.c"
static unsigned calls, fail_at;
static u8 *mapping;
static u8 expected[256];
static unsigned command_word, transfer_bytes;
u64 ktime_get_ns(void) { return 1000; }
void usleep_range(unsigned long minimum, unsigned long maximum)
{ (void)minimum; (void)maximum; assert(false); }
int mt6797_test_read(void *address, unsigned int *value)
{ (void)address; (void)value; assert(false); return -EIO; }
int mt6797_test_write(unsigned int value, void *address)
{
 unsigned offset = calls ? 0x1000 : 0;
 assert(address == mapping + offset);
 if (!calls) assert(value == command_word);
 else {
  unsigned n=(calls-1)*4;
  assert(n<transfer_bytes);
  assert(value == ((unsigned)expected[n] | (unsigned)expected[n+1]<<8 |
                   (unsigned)expected[n+2]<<16 | (unsigned)expected[n+3]<<24));
 }
 calls++;
 return calls == fail_at ? -EIO : 0;
}
static void exercise(unsigned fault, bool expired)
{
 struct mt6797_init_transaction transaction={.phase=MT6797_INIT_IDLE};
 unsigned char history[32]={0}, frame[30]={0xb0};
 struct mt6797_hif hif={.transaction=&transaction,.firmware_ready=true,
                       .capability_complete=true};
 struct mt6797_hif_command cmd;
 unsigned pages;
 int ret;
 mapping=calloc(1,0x1004); assert(mapping); hif.base=mapping;
 mutex_init(&hif.mutex);
 hif.io=(struct mt6797_hif_pio_io){.context=&hif,.write=mt6797_hif_write,.read=mt6797_hif_read};
 assert(!mt6797_normal_admit(&hif.normal,4,4,history));
 hif.normal.phase=MT6797_NORMAL_NVRAM_SUBMITTED;
 memset(expected,0,sizeof(expected));
 assert(mt6797_join_tx_descriptor(frame,30,1,7,500,3,expected,&pages));
 memcpy(expected+28,frame,30);
 assert(!mt6797_hif_encode_command(0x34,MT6797_HIF_WRITE,MT6797_HIF_PIO_ONLY,58,sizeof(expected),&cmd));
 command_word=cmd.word; transfer_bytes=cmd.transfer_bytes;
 calls=0; fail_at=fault;
 ret=mt6797_hif_send_management(&hif,frame,30,1,7,500,3,expired?1000:1000000);
 assert(hif.normal.tc4_free==3); /* Failed/ambiguous submission never refunded. */
 for(unsigned i=0;i<32;i++) assert(!history[i]);
 assert(!hif.mutex.held);
 if(expired || fault) {
  assert(ret<0 && hif.normal.phase==MT6797_NORMAL_FAILED);
  assert(transaction.phase!=MT6797_INIT_IDLE);
  assert(calls==(expired?0:fault));
 } else {
  assert(!ret && hif.normal.phase==MT6797_NORMAL_NVRAM_SUBMITTED);
  assert(calls==1+transfer_bytes/4);
  calls=0;
  assert(mt6797_hif_send_management(&hif,frame,30,1,8,500,3,1000000)==-EBUSY);
  assert(!calls && hif.normal.tc4_free==3);
 }
 free(mapping);
}
static void exercise_command(unsigned kind, unsigned fault, bool expired)
{
 struct mt6797_init_transaction transaction={.phase=MT6797_INIT_IDLE};
 unsigned char history[32]={0}, ap[6]={2,0,0,0,0,1};
 struct mt6797_hif hif={.transaction=&transaction,.firmware_ready=true,
                       .capability_complete=true};
 struct mt6797_hif_command cmd;
 unsigned cid=kind==0?0x13:kind==1?0x1c:kind==2?0x14:kind==3?0x0a:0x12;
 unsigned bytes=kind==0?124:kind==1?16:kind==4?88:4;
 unsigned pages=(8+bytes+127)/128;
 int ret;
 mapping=calloc(1,0x1004); assert(mapping); hif.base=mapping;
 mutex_init(&hif.mutex);
 hif.io=(struct mt6797_hif_pio_io){.context=&hif,.write=mt6797_hif_write,.read=mt6797_hif_read};
 assert(!mt6797_normal_admit(&hif.normal,4,4,history));
 hif.normal.phase=MT6797_NORMAL_NVRAM_SUBMITTED;
 memset(expected,0,sizeof(expected));
 expected[0]=8+bytes; expected[3]=0x80; expected[4]=cid;
 expected[5]=0xa0; expected[6]=1; expected[7]=19;
 if(kind==0) assert(mt6797_join_station_payload(ap,3,1,0x3fc0,0x540,expected+8));
 else if(kind==1) assert(mt6797_join_channel_payload(7,40,10000,false,expected+8));
 else if(kind==2) assert(mt6797_join_remove_station(expected+8));
 else if(kind==3) assert(mt6797_join_filter_payload(expected+8));
 else assert(mt6797_join_bss_payload(ap,(const u8 *)"lab",3,0x3fc0,0x540,false,false,expected+8));
 assert(!mt6797_hif_encode_command(0x34,MT6797_HIF_WRITE,MT6797_HIF_PIO_ONLY,8+bytes,sizeof(expected),&cmd));
 command_word=cmd.word; transfer_bytes=cmd.transfer_bytes; calls=0; fail_at=fault;
 u64 deadline=expired?1000:1000000;
 if(kind==0) ret=mt6797_hif_join_station(&hif,19,ap,3,1,0x3fc0,0x540,deadline);
 else if(kind==1) ret=mt6797_hif_join_channel(&hif,19,7,40,10000,false,deadline);
 else if(kind==2) ret=mt6797_hif_join_remove_station(&hif,19,deadline);
 else if(kind==3) ret=mt6797_hif_join_filter(&hif,19,deadline);
 else ret=mt6797_hif_join_bss(&hif,19,ap,(const u8 *)"lab",3,0x3fc0,0x540,false,false,deadline);
 assert(hif.normal.tc4_free==4-pages && !hif.mutex.held);
 assert(history[19/8]==(1U<<(19%8)));
 for(unsigned i=0;i<32;i++) if(i!=19/8) assert(!history[i]);
 if(expired || fault) {
  assert(ret<0 && hif.normal.phase==MT6797_NORMAL_FAILED);
  assert(transaction.phase!=MT6797_INIT_IDLE);
  assert(calls==(expired?0:fault));
 } else {
  assert(!ret && calls==1+transfer_bytes/4);
  assert(hif.normal.phase==MT6797_NORMAL_NVRAM_SUBMITTED);
  unsigned int words[8]={0}; struct mt6797_normal_release release;
  words[7]=(pages<<16)|pages;
  assert(!mt6797_normal_reconcile(&hif.normal,words,&release));
  calls=0;
  assert(mt6797_hif_join_remove_station(&hif,19,1000000)<0);
  assert(!calls && hif.normal.phase==MT6797_NORMAL_FAILED);
 }
 free(mapping);
}
static void corrupt_command_ledger(unsigned kind)
{
 struct mt6797_init_transaction transaction={.phase=MT6797_INIT_IDLE};
 unsigned char history[32]={0};
 struct mt6797_hif hif={.transaction=&transaction,.firmware_ready=true,
                       .capability_complete=true};
 mutex_init(&hif.mutex);
 assert(!mt6797_normal_admit(&hif.normal,4,4,history));
 hif.normal.phase=MT6797_NORMAL_NVRAM_SUBMITTED;
 if(kind==0) hif.normal.tc4_free=5;
 else if(kind==1) hif.normal.tc4_limit=0;
 else if(kind==2) hif.normal.tc4_limit=0x10000;
 else hif.normal.used_sequences=NULL;
 calls=0;
 assert(mt6797_hif_join_remove_station(&hif,19,1000000)<0);
 assert(!calls && !hif.mutex.held);
 assert(hif.normal.phase==MT6797_NORMAL_FAILED);
 for(unsigned i=0;i<32;i++) assert(!history[i]);
}
static void reject_other_filter_modes(void)
{
 unsigned char history[32]={0}, payload[4], out[64], before[64];
 const unsigned words[]={0,1,8,0x20,0xff,0x10000009};
 struct mt6797_normal_transaction t={0};
 struct mt6797_hif_command command;
 for(unsigned i=0;i<sizeof(words)/sizeof(words[0]);i++) {
  assert(!mt6797_normal_admit(&t,4,4,history));
  t.phase=MT6797_NORMAL_NVRAM_SUBMITTED;
  for(unsigned b=0;b<4;b++) payload[b]=words[i]>>(8*b);
  memset(out,0xa5,sizeof(out)); memcpy(before,out,sizeof(out));
  assert(mt6797_join_prepare_command(&t,0x0a,19,payload,4,out,sizeof(out),&command)==-EINVAL);
  assert(!memcmp(out,before,sizeof(out)) && t.tc4_free==4);
  assert(t.phase==MT6797_NORMAL_NVRAM_SUBMITTED);
  for(unsigned b=0;b<32;b++) assert(!history[b]);
  t=(struct mt6797_normal_transaction){0};
 }
}
int main(void)
{
 reject_other_filter_modes();
 for(unsigned kind=0;kind<4;kind++) corrupt_command_ledger(kind);
 exercise(0,false);
 unsigned accesses=1+transfer_bytes/4;
 for(unsigned fault=1;fault<=accesses;fault++) exercise(fault,false);
 exercise(0,true);
 for(unsigned kind=0;kind<5;kind++) {
  exercise_command(kind,0,false);
  unsigned n=1+transfer_bytes/4;
  for(unsigned fault=1;fault<=n;fault++) exercise_command(kind,fault,false);
  exercise_command(kind,0,true);
 }
 return 0;
}
