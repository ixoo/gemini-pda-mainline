/* SPDX-License-Identifier: GPL-2.0-only */
#define MT6797_HIF_HOST_TEST
#include <stdio.h>
#include <string.h>
#include "hif.c"

static struct {
 unsigned int calls, fail_at, values[2][10], final_clock;
 bool expire_after_pair;
 unsigned char *mapping;
} fake;
u64 ktime_get_ns(void)
{
 if(fake.expire_after_pair && fake.calls==40 && ++fake.final_clock>=2) return 1000001000ULL;
 return 1000;
}
void usleep_range(unsigned long low, unsigned long high) { assert(low==50 && high==100); }
static unsigned int reg(unsigned int n) { return n==0 ? 0x0c : n==1 ? 0x10 : 0x130+(n-2)*4; }
int mt6797_test_write(unsigned int value, void *address)
{
 unsigned int n=fake.calls++;
 assert(!(n%2) && n<40);
 assert((unsigned char *)address-fake.mapping==0);
 assert(value==(0x10000004U|(reg((n%20)/2)<<9)));
 return fake.calls==fake.fail_at ? -EIO : 0;
}
int mt6797_test_read(void *address, unsigned int *value)
{
 unsigned int n=fake.calls++;
 assert(n%2 && n<40);
 assert((unsigned char *)address-fake.mapping==0x1000);
 if(fake.calls==fake.fail_at) return -EIO;
 *value=fake.values[n/20][(n%20)/2];
 return 0;
}
static struct mt6797_hif *allocate(struct mt6797_init_transaction *transaction)
{
 memset(&fake,0,sizeof(fake)); fake.mapping=calloc(1,0x1004); assert(fake.mapping);
 struct mt6797_hif *hif=mt6797_hif_alloc(fake.mapping,0x1004,transaction); assert(!IS_ERR(hif));
 hif->firmware_ready=true; return hif;
}
static void release(struct mt6797_hif *hif) { mt6797_hif_free(hif); free(fake.mapping); }
static void normal_owner(struct mt6797_hif *hif)
{
 assert(!mt6797_normal_admit(&hif->normal,26,9,hif->transaction->used_sequences));
 hif->normal.phase=MT6797_NORMAL_NVRAM_SUBMITTED;
 hif->capability_attempted=true; hif->capability_complete=true;
 hif->transaction->used_sequences[0]=0x1f;
}
static void baseline(unsigned int fail_at, int dirty_word)
{
 struct mt6797_init_transaction transaction={.phase=MT6797_INIT_IDLE};
 struct mt6797_hif_tx_status status;
 struct mt6797_normal_release account;
 struct mt6797_hif *hif=allocate(&transaction);
 fake.fail_at=fail_at;
 if(dirty_word>=0) fake.values[0][2+dirty_word]=1;
 int ret=mt6797_hif_account_tx_status(hif,1000001000ULL,1,&status,&account);
 assert(fake.calls==(fail_at ? fail_at : 20));
 assert(!account.released_pages && !account.tc4_free && !account.pending_cpu && !account.pending_ffa);
 if(fail_at || dirty_word>=0) {
  assert(ret==-EIO && !hif->tx_status_accounting_baseline && transaction.phase==MT6797_INIT_POISONED);
 } else {
  assert(!ret && hif->tx_status_accounting_baseline && status.valid_words==0x3ff);
 }
 unsigned int prior=fake.calls;
 assert(mt6797_hif_account_tx_status(hif,1000001000ULL,1,&status,&account)==-EIO);
 assert(fake.calls==prior);
 release(hif);
}
static void pair(unsigned int fail_at, int bad_snapshot, int bad_word)
{
 struct mt6797_init_transaction transaction={.phase=MT6797_INIT_IDLE};
 struct mt6797_hif_tx_status status[2];
 struct mt6797_normal_release account[2];
 struct mt6797_hif *hif=allocate(&transaction);
 assert(!mt6797_hif_account_tx_status(hif,1000001000ULL,1,status,account));
 normal_owner(hif); fake.calls=0; fake.fail_at=fail_at;
 fake.values[0][9]=(4U<<16)|16U;
 fake.values[1][9]=12U<<16;
 if(bad_snapshot>=0) fake.values[bad_snapshot][2+bad_word]=bad_word==7 ? 0x00120012U : 1;
 unsigned char history[32]; memcpy(history,transaction.used_sequences,sizeof(history));
 int ret=mt6797_hif_account_tx_status(hif,1000001000ULL,2,status,account);
 assert(fake.calls==(fail_at ? fail_at : bad_snapshot==0 ? 20 : 40));
 assert(!memcmp(history,transaction.used_sequences,sizeof(history)));
 if(fail_at || bad_snapshot>=0) {
  assert(ret==-EIO && hif->normal.tc4_free==9 && hif->normal.phase==MT6797_NORMAL_FAILED);
  assert(!hif->normal.tc4_pending_cpu && !hif->normal.tc4_pending_ffa);
  assert(!account[0].released_pages && !account[1].released_pages);
 } else {
  assert(!ret && hif->normal.tc4_free==25 && hif->normal.phase==MT6797_NORMAL_NVRAM_SUBMITTED);
  assert(account[0].released_pages==4 && account[0].tc4_free==13 && account[0].pending_ffa==12 && !account[0].pending_cpu);
  assert(account[1].released_pages==12 && account[1].tc4_free==25 && !account[1].pending_cpu && !account[1].pending_ffa);
 }
 unsigned int prior=fake.calls;
 assert(mt6797_hif_account_tx_status(hif,1000001000ULL,2,status,account)==-EIO);
 assert(fake.calls==prior && !account[0].released_pages && !account[1].released_pages);
 release(hif);
}
static void missing_accounting_baseline(void)
{
 struct mt6797_init_transaction transaction={.phase=MT6797_INIT_IDLE};
 struct mt6797_hif_tx_status status[2]; struct mt6797_normal_release account[2];
 struct mt6797_hif *hif=allocate(&transaction);
 assert(!mt6797_hif_observe_tx_status(hif,1000001000ULL,1,status));
 normal_owner(hif); fake.calls=0;
 assert(mt6797_hif_account_tx_status(hif,1000001000ULL,2,status,account)==-EIO);
 assert(!fake.calls && hif->normal.tc4_free==9 && transaction.phase==MT6797_INIT_POISONED);
 release(hif);
}
static void late_deadline(void)
{
 struct mt6797_init_transaction transaction={.phase=MT6797_INIT_IDLE};
 struct mt6797_hif_tx_status status[2]; struct mt6797_normal_release account[2];
 struct mt6797_hif *hif=allocate(&transaction);
 assert(!mt6797_hif_account_tx_status(hif,1000001000ULL,1,status,account));
 normal_owner(hif); fake.calls=0; fake.expire_after_pair=true;
 fake.values[0][9]=0x00040004U;
 assert(mt6797_hif_account_tx_status(hif,1000001000ULL,2,status,account)==-ETIMEDOUT);
 assert(fake.calls==40 && hif->normal.tc4_free==9 && !account[0].released_pages && !account[1].released_pages);
 assert(transaction.phase==MT6797_INIT_POISONED && hif->normal.phase==MT6797_NORMAL_FAILED);
 release(hif);
}
static void ledger(void)
{
 unsigned char history[32]={0x5a}; unsigned int words[8]={0};
 struct mt6797_normal_release account;
 for(unsigned int free_pages=0;free_pages<=26;free_pages++) {
  for(unsigned int cpu=0;cpu<=28;cpu++) for(unsigned int ffa=0;ffa<=28;ffa++) {
   struct mt6797_normal_transaction t={0};
   assert(!mt6797_normal_admit(&t,26,free_pages,history)); t.phase=MT6797_NORMAL_NVRAM_SUBMITTED;
   words[7]=(cpu<<16)|ffa;
   int ret=mt6797_normal_reconcile(&t,words,&account);
   unsigned int debt=26-free_pages, refund=cpu<ffa ? cpu : ffa;
   if(cpu>debt || ffa>debt) assert(ret==-EIO && t.tc4_free==free_pages && t.phase==MT6797_NORMAL_FAILED && !account.released_pages);
   else {
    assert(!ret && t.tc4_free==free_pages+refund && t.tc4_pending_cpu==cpu-refund && t.tc4_pending_ffa==ffa-refund);
    words[7]=0; assert(!mt6797_normal_reconcile(&t,words,&account) && !account.released_pages);
    words[7]=((debt-cpu)<<16)|(debt-ffa);
    assert(!mt6797_normal_reconcile(&t,words,&account) && t.tc4_free==26 && !t.tc4_pending_cpu && !t.tc4_pending_ffa);
    words[7]=1; assert(mt6797_normal_reconcile(&t,words,&account)==-EIO && t.tc4_free==26);
   }
   assert(history[0]==0x5a);
  }
 }
 for(unsigned int phase=MT6797_NORMAL_COLD;phase<=MT6797_NORMAL_FAILED;phase++) {
  struct mt6797_normal_transaction t={.phase=phase,.tc4_limit=26,.tc4_free=12,.used_sequences=history}; words[7]=0;
  int ret=mt6797_normal_reconcile(&t,words,&account);
  assert((ret==0)==(phase==MT6797_NORMAL_CAP_RECEIVED || phase==MT6797_NORMAL_NVRAM_SUBMITTED));
 }
 for(unsigned int side=0;side<2;side++) {
  struct mt6797_normal_transaction t={.phase=MT6797_NORMAL_CAP_RECEIVED,.tc4_limit=26,.tc4_free=12,.used_sequences=history};
  if(side) t.tc4_pending_cpu=15; else t.tc4_pending_ffa=15;
  assert(mt6797_normal_reconcile(&t,words,&account)==-EIO && t.tc4_free==12);
 }
 struct mt6797_normal_transaction wide={.phase=MT6797_NORMAL_CAP_RECEIVED,.tc4_limit=65535,.used_sequences=history};
 words[7]=0xffffffffU; assert(!mt6797_normal_reconcile(&wide,words,&account) && wide.tc4_free==65535);
 assert(mt6797_normal_reconcile(NULL,words,&account)==-EINVAL);
 assert(mt6797_normal_reconcile(&wide,NULL,&account)==-EINVAL);
 assert(mt6797_normal_reconcile(&wide,words,NULL)==-EINVAL);
}
int main(void)
{
 ledger(); late_deadline(); missing_accounting_baseline(); baseline(0,-1); pair(0,-1,-1);
 for(unsigned int i=1;i<=20;i++) baseline(i,-1);
 for(unsigned int i=1;i<=40;i++) pair(i,-1,-1);
 for(int i=0;i<8;i++) { baseline(0,i); pair(0,0,i); pair(0,1,i); }
 puts("TC4 reconciliation: pass; separated returns, bounded debit, atomic pair, 60 transfer faults");
 return 0;
}
