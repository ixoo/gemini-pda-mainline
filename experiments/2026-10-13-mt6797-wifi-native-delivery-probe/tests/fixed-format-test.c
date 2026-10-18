/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual HIF, normal ledger and extracted MAC functions. No firmware model. */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint16_t u16;
#define MT6797_HIF_HOST_TEST
#include "hif.c"
#define RX_FLAG_DECRYPTED 1U
#define RX_FLAG_IV_STRIPPED 2U
#define RX_FLAG_PN_VALIDATED 4U
#define RX_FLAG_MMIC_STRIPPED 8U
#define RX_FLAG_MIC_STRIPPED 16U
#define RX_FLAG_ALLOW_SAME_PN 32U
#define RX_FLAG_NO_SIGNAL_VAL 64U
#include "native-diag.h"
#define NSEC_PER_MSEC 1000000ULL
#define min_t(type,a,b) ((type)(a) < (type)(b) ? (type)(a) : (type)(b))
#define wiphy_dev(x) NULL
static void dev_info(void *dev, const char *format, ...) __attribute__((format(printf, 2, 3)));
static unsigned int log_calls;
static void dev_info(void *dev, const char *format, ...) { (void)dev; (void)format; log_calls++; }
#define ASSERT_RTNL() assert(rtnl_held)
struct operation { bool write; unsigned int offset, value; };
static struct operation operations[256];
static unsigned int count, used, fail_at, expire_at, sleeps, cases;
static u64 clock_ns;
static u8 mapping[0x1004];
static bool rtnl_held = true, native_delivery_diag, ccmp_stable_epoch = true;
struct ieee80211_hw { void *priv; };
struct mt6797_mac {
 struct mt6797_hif *hif;
 struct mutex mutex;
 void *vif;
 u64 native_diag_started, join_data_deadline, join_credit_deadline, join_deadline;
 unsigned int native_diag_total, native_diag_native, native_diag_bytes, ccmp_queued;
 unsigned int sequence, join_page_debt, join_key_pairwise, join_key_group, join_next_pid;
 unsigned char native_diag_state;
 bool join_data_phase, join_data_ended, join_credit_pending, join_inflight;
 bool closing, native_diag_sample_done, native_diag_engaged;
 bool rx_format_ready, rx_format_attempted, scan_ready, started, scan_used, configured;
 int first_error, join_credit_done;
};
static void reinit_completion(int *c) { *c = 0; }
static void mutex_lock(struct mutex *m) { assert(mutex_trylock(m)); }
static void mt6797_mac_join_end_data(struct mt6797_mac *m, const char *reason)
{ (void)reason; m->join_data_ended = true; }
#include "fixed-mac.inc"
u64 ktime_get_ns(void) { return clock_ns; }
void usleep_range(unsigned long low, unsigned long high)
{ assert(low == 20000 && high == 21000); clock_ns += low * 1000; sleeps++; }
static void add(bool write, unsigned int offset, unsigned int value)
{ assert(count < 256); operations[count++] = (struct operation){write, offset, value}; }
static void read_register(unsigned int reg, unsigned int value)
{ add(true, 0, (1U << 28) | (reg << 9) | 4U); add(false, 0x1000, value); }
static void script(const unsigned int *credits, unsigned int polls)
{
 count = used = sleeps = fail_at = expire_at = 0; clock_ns = 1000000000ULL;
 add(true, 0, 0x90006810); add(true, 0x1000, 0x80000010);
 add(true, 0x1000, 0x1301a0c0); add(true, 0x1000, 0x800c0068);
 add(true, 0x1000, 7);
 for (unsigned int n = 0; n < polls; n++) {
  read_register(0x0c, 0); read_register(0x10, 0);
  for (unsigned int i = 0; i < 8; i++) read_register(0x130 + 4 * i, i == 7 ? credits[n] : 0);
 }
}
static int access(bool write, void *address, unsigned int *value)
{
 assert(used < count);
 struct operation *op = &operations[used++];
 assert(write == op->write && address == mapping + op->offset);
 if (write) assert(*value == op->value); else *value = op->value;
 if (used == expire_at) clock_ns = 1100000000ULL;
 return used == fail_at ? -EIO : 0;
}
int mt6797_test_read(void *address, unsigned int *value) { return access(false, address, value); }
int mt6797_test_write(unsigned int value, void *address) { return access(true, address, &value); }
static void setup(struct mt6797_hif *h, struct mt6797_init_transaction *t, u8 *history)
{
 memset(h, 0, sizeof(*h)); memset(t, 0, sizeof(*t)); memset(history, 0, 32);
 t->phase = MT6797_INIT_IDLE; t->free_pages = t->start_free_pages = 104;
 h->transaction = t; h->base = mapping; h->firmware_ready = h->capability_complete = true;
 h->tx_status_accounting_baseline = h->tx_status_normal_attempted = true;
 h->io = (struct mt6797_hif_pio_io){.context=h, .write=mt6797_hif_write, .read=mt6797_hif_read};
 mutex_init(&h->mutex); assert(!mt6797_normal_admit(&h->normal, 4, 4, history));
 h->normal.phase = MT6797_NORMAL_NVRAM_SUBMITTED;
}
static enum mt6797_rx_format_phase phase;
static int configure(struct mt6797_hif *h, unsigned int seq, u64 deadline)
{ return mt6797_hif_configure_rx_format(h,seq,deadline,&phase); }
static void wire_trial(const unsigned int *credits, unsigned int polls, unsigned int fault, unsigned int expiry, int expected)
{
 struct mt6797_hif h; struct mt6797_init_transaction t; u8 history[32];
 setup(&h, &t, history); script(credits, polls); fail_at=fault; expire_at=expiry;
 assert(configure(&h, 19, 1100000000ULL) == expected);
 if (fault) assert(used == fault);
 if (expiry) assert(used == expiry);
 assert(h.rx_format_attempted && (history[2] & 8));
 assert(phase==(expected?(fault<=5 && fault?MT6797_RX_FORMAT_SUBMIT:expiry<=5 && expiry?MT6797_RX_FORMAT_SUBMIT:MT6797_RX_FORMAT_CREDIT):MT6797_RX_FORMAT_DONE));
 if (!expected) {
  assert(used == count && h.normal.tc4_free == 4 && mt6797_hif_normal_idle(&h));
  assert(t.phase == MT6797_INIT_IDLE && !h.first_error);
 } else {
  assert(t.phase == MT6797_INIT_POISONED && h.normal.phase == MT6797_NORMAL_FAILED);
  assert(h.normal.tc4_free == 3); /* ambiguous/error never refunds the debit */
  assert(h.first_error == expected);
 }
 unsigned int before = used;
 assert(configure(&h, 20, clock_ns + 100000000ULL) == (expected ? -EIO : -EALREADY));
 assert(used == before && !(history[2] & 16)); cases++;
}
static void prior_debt(void)
{
 for(unsigned int mode=0;mode<5;mode++) {
  struct mt6797_hif h; struct mt6797_init_transaction t; u8 history[32];
  setup(&h,&t,history); h.normal.tc4_free=3; h.normal.tc4_pending_ffa=1; history[2]=4;
  if(mode==3) { h.normal.tc4_limit=26; h.normal.tc4_free=14; h.normal.tc4_pending_ffa=12; }
  count=used=sleeps=fail_at=expire_at=0; clock_ns=1000000000ULL;
  unsigned int polls=(mode==1 || mode==4)?5:1;
  for(unsigned int n=0;n<polls;n++) {
   read_register(0x0c,0); read_register(0x10,0);
   for(unsigned int i=0;i<8;i++) read_register(0x130+4*i,i==7?(mode==0?0x10000:mode==2?0x20000:mode==3?0xc0000:mode==4&&n==4?0x10000:0):0);
  }
  if(mode==0 || mode==3 || mode==4) {
   add(true,0,0x90006810); add(true,0x1000,0x80000010); add(true,0x1000,0x1301a0c0);
   add(true,0x1000,0x800c0068); add(true,0x1000,7);
   read_register(0x0c,0); read_register(0x10,0);
   for(unsigned int i=0;i<8;i++) read_register(0x130+4*i,i==7&&mode!=4?0x10001:0);
  }
  int rc=configure(&h,19,1100000000ULL);
  assert(rc==(mode==0 || mode==3?0:mode==1 || mode==4?-ETIMEDOUT:-EIO));
  assert(used==count && (history[2]&4));
  assert(phase==(mode==0 || mode==3?MT6797_RX_FORMAT_DONE:mode==4?MT6797_RX_FORMAT_CREDIT:MT6797_RX_FORMAT_PRIOR_CREDIT));
  assert((history[2]&8)==(mode==0 || mode==3 || mode==4?8:0)); /* no mask encoded before prior debt retired */
  assert(h.normal.tc4_free==(mode==3?26U:mode==0?4U:3U));
  assert(h.deadline_ns==1100000000ULL);
  if(mode==1 || mode==2 || mode==4) assert(t.phase==MT6797_INIT_POISONED);
  if(mode==1 || mode==2) assert(h.normal.tc4_pending_ffa==1);
  if(mode==4) assert(h.normal.tc4_pending_ffa==0 && sleeps==5);
  cases++;
 }
}
static void prior_snapshot_faults(void)
{
 for(unsigned int kind=0;kind<2;kind++) for(unsigned int fault=1;fault<=20;fault++) {
  struct mt6797_hif h; struct mt6797_init_transaction t; u8 history[32];
  setup(&h,&t,history); h.normal.tc4_free=3; h.normal.tc4_pending_ffa=1;
  count=used=sleeps=fail_at=expire_at=0; clock_ns=1000000000ULL;
  read_register(0x0c,0); read_register(0x10,0);
  for(unsigned int i=0;i<8;i++) read_register(0x130+4*i,i==7?0x10000:0);
  if(kind) expire_at=fault; else fail_at=fault;
  assert(configure(&h,19,1100000000ULL)==(kind?-ETIMEDOUT:-EIO));
  assert(used==fault && !(history[2]&8) && h.normal.tc4_free==3 && h.normal.tc4_pending_ffa==1);
  assert(phase==MT6797_RX_FORMAT_PRIOR_CREDIT);
  assert(t.phase==MT6797_INIT_POISONED); cases++;
 }
}
static void admission(void)
{
 for (unsigned int n=0; n<7; n++) {
  struct mt6797_hif h; struct mt6797_init_transaction t; u8 history[32];
  setup(&h,&t,history); script((unsigned int[]){0x10001},1);
  if (n==0) h.tx_status_accounting_baseline=false;
  if (n==1) h.tx_status_normal_attempted=false;
  if (n==2) h.mutex.held=true;
  if (n==3) h.normal.phase=MT6797_NORMAL_FAILED;
  if (n==4) h.normal.phase=MT6797_NORMAL_CAP_RECEIVED;
  int rc=configure(&h,19,n==5?1000000000ULL:n==6?1100000001ULL:1100000000ULL);
  assert(rc && !used && !(history[2]&8)); cases++;
 }
}
static void payload_cases(void)
{
 u8 payload[8], out[32], history[32]; struct mt6797_hif_command command;
 for (unsigned int n=0;n<74;n++) {
  struct mt6797_hif h; struct mt6797_init_transaction t;
  setup(&h,&t,history); mt6797_diag_mask_payload(true,payload); memset(out,0xa5,sizeof(out));
  size_t bytes=8;
  if(n<64) payload[n/8]^=1U<<(n%8); else bytes=n-64;
  int rc=mt6797_normal_prepare_config(&h.normal,MT6797_NORMAL_RX_FORMAT,19,payload,bytes,out,sizeof(out),&command);
  if(bytes==8 && n==72) { assert(!rc && h.normal.tc4_free==3); }
  else {
   assert(rc && h.normal.tc4_free==4 && !(history[2]&8));
   for(unsigned int i=0;i<sizeof(out);i++) assert(out[i]==0xa5);
  }
  cases++;
 }
}
static void runtime_mode_refused(void)
{
 for(unsigned int enable=0;enable<2;enable++) {
  struct mt6797_hif h; struct mt6797_init_transaction t; u8 history[32];
  setup(&h,&t,history); script((unsigned int[]){0x10001},1);
  assert(mt6797_hif_diag_mask(&h,19,enable,1100000000ULL)==-EINVAL);
  assert(!used && h.normal.tc4_free==4 && !(history[2]&8)); cases++;
 }
 struct mt6797_hif h; struct mt6797_init_transaction t; u8 history[32], payload[8], out[32];
 struct mt6797_hif_command command;
 setup(&h,&t,history); mt6797_diag_mask_payload(false,payload); memset(out,0xa5,sizeof(out));
 assert(mt6797_normal_prepare_config(&h.normal,MT6797_NORMAL_RX_FORMAT,19,payload,8,out,sizeof(out),&command)==-EINVAL);
 assert(h.normal.tc4_free==4 && !(history[2]&8));
 for(unsigned int i=0;i<sizeof(out);i++) assert(out[i]==0xa5);
 cases++;
}
static void mac_cases(void)
{
 for(unsigned int failure=0;failure<3;failure++) {
  struct mt6797_hif h; struct mt6797_init_transaction t; u8 history[32];
  setup(&h,&t,history); script((unsigned int[]){0x10001},1); if(failure==1) fail_at=3;
  struct mt6797_mac m={.hif=&h,.sequence=19,.configured=true}; struct ieee80211_hw hw={.priv=&m};
  if(failure==2) m.started=true;
  assert((mt6797_mac_prepare_rx_format(&hw)==0)==!failure);
  mt6797_mac_scan_ready(&hw);
  assert(m.scan_ready==!failure && m.rx_format_ready==!failure);
  assert(m.closing==!!failure && !m.mutex.held);
  unsigned int before=used; assert(mt6797_mac_prepare_rx_format(&hw));
  assert(used==before && m.closing && !m.scan_ready && !m.rx_format_ready); cases++;
 }
 for(unsigned int state=0;state<5;state++) for(unsigned int flags=0;flags<256;flags++) {
  struct mt6797_mac m={.sequence=19,.native_diag_state=state,.rx_format_ready=!(flags&1),
   .join_data_phase=!(flags&2),.join_key_pairwise=!(flags&4),.join_key_group=!(flags&8),
   .join_credit_pending=!!(flags&16),.join_page_debt=!!(flags&16),.join_inflight=!!(flags&32),
   .native_diag_sample_done=!!(flags&64),.native_diag_engaged=state!=0,.closing=!!(flags&128)};
  m.join_data_deadline=m.join_deadline=clock_ns+7000000000ULL;
  unsigned int debt=m.join_page_debt; bool pending=m.join_credit_pending;
  count=used=0; mt6797_native_diag_step(&m);
  assert(!used && m.sequence==19 && m.join_page_debt==debt && m.join_credit_pending==pending);
  if(!flags && state==0) assert(m.native_diag_state==MT6797_ND_ACTIVE && m.native_diag_engaged && m.native_diag_started==clock_ns);
  if(state==0 && m.rx_format_ready && !m.closing && (flags & (2|4|8)))
   assert(m.native_diag_state==MT6797_ND_IDLE && !m.native_diag_engaged);
  if(state==4) assert(m.native_diag_state==MT6797_ND_CLOSED);
  if(!m.rx_format_ready || state==1 || state==3) assert(m.first_error && m.closing);
  cases++;
 }
 for(unsigned int owed=0;owed<4;owed++) {
  struct mt6797_mac m={.sequence=19,.native_diag_state=MT6797_ND_ACTIVE,.rx_format_ready=true,
   .native_diag_engaged=true,.join_data_ended=true,.join_inflight=!!(owed&1),.join_page_debt=!!(owed&2)};
  count=used=0; mt6797_native_diag_step(&m);
  assert(!used && !m.first_error);
  assert((m.native_diag_state==MT6797_ND_CLOSED)==!owed);
  assert(mt6797_native_diag_tx_fenced(&m)==!!owed);
  assert(mt6797_native_diag_cleanup_allowed(m.native_diag_state)==!owed); cases++;
 }
 clock_ns=20000000000ULL;
 for(unsigned int kind=0;kind<4;kind++) for(unsigned int at=0;at<2;at++) {
  struct mt6797_mac m={.sequence=19,.native_diag_state=MT6797_ND_ACTIVE,.rx_format_ready=true,
   .native_diag_engaged=true,.join_data_phase=true,.join_key_pairwise=1,.join_key_group=1};
  m.join_data_deadline=clock_ns+7000000000ULL;
  if(kind==0) m.native_diag_started=clock_ns-(9999+at)*NSEC_PER_MSEC;
  if(kind==1) m.native_diag_total=511+at;
  if(kind==2) m.ccmp_queued=63+at;
  if(kind==3) m.native_diag_bytes=1024*1024-1+at;
  count=used=0; mt6797_native_diag_step(&m);
  assert(!used && !m.first_error && (m.native_diag_state==MT6797_ND_CLOSED)==!!at); cases++;
 }
}
static void scan_log_cases(void)
{
 struct mt6797_hif_rx_result rx={.protocol_refusal=MT6797_HIF_RX_REFUSAL_HEADER,
  .pre_valid=true,.pre_wrplr=94,.selected_length=94,.header_valid=true,.header_length=142,
  .rx_setup=true,.rx_complete=true,.staging_bytes=100,.refused_type_valid=true,.refused_type_word=0x5faf};
 log_calls=0; scan_refusal(-EPROTO,0,rx); assert(log_calls==2);
 log_calls=0; scan_refusal(0,0,rx); scan_refusal(-EIO,0,rx); assert(!log_calls);
 rx.protocol_refusal=MT6797_HIF_RX_REFUSAL_NONE; scan_refusal(-EPROTO,0,rx); assert(!log_calls);
 cases+=3;
}
int main(void)
{
 wire_trial((unsigned int[]){0x10001},1,0,0,0);
 wire_trial((unsigned int[]){0x10000,1},2,0,0,0);
 wire_trial((unsigned int[]){1,0x10000},2,0,0,0);
 for(unsigned int i=1;i<=25;i++) {
  wire_trial((unsigned int[]){0x10001},1,i,0,-EIO);
  wire_trial((unsigned int[]){0x10001},1,0,i,-ETIMEDOUT);
 }
 wire_trial((unsigned int[]){0,0,0,0,0},5,0,0,-ETIMEDOUT);
 wire_trial((unsigned int[]){0x20002},1,0,0,-EIO);
 prior_debt(); prior_snapshot_faults(); admission(); payload_cases(); runtime_mode_refused(); mac_cases(); scan_log_cases();
 printf("fixed format: %u cases; actual normal/HIF credit, bounds, poison, local MAC/no runtime I/O PASS\n",cases);
 return 0;
}
