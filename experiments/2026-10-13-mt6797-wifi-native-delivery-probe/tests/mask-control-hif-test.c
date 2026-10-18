// SPDX-License-Identifier: GPL-2.0-only
/* Actual HIF plus extracted MAC step; finite PIO mock from native-hif-test.c. */
#include <stdint.h>
#include <stdio.h>
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
#define dev_info(...) ((void)0)
static bool native_delivery_diag, ccmp_stable_epoch = true;
static u64 clock_ns;
static unsigned int calls, fail_at, expire_at;
static u8 mapping[0x1004], emitted[24];
static bool ended;
#ifdef CONFIG_MT6797_CCMP_MASK_CONTROL
#define TX_CALLS 5U
#else
#define TX_CALLS 7U
#endif
struct mt6797_mac {
	struct mt6797_hif *hif;
	u64 native_diag_started, join_data_deadline, join_credit_deadline, join_deadline;
	unsigned int native_diag_total, native_diag_native, native_diag_bytes, ccmp_queued;
	unsigned int sequence, join_page_debt, join_key_pairwise, join_key_group;
	unsigned char native_diag_state;
	bool join_data_phase, join_data_ended, join_credit_pending, join_inflight;
	bool closing, native_diag_sample_done, native_diag_engaged;
	int first_error, join_credit_done;
};
static void reinit_completion(int *c) { *c = 0; }
static void mt6797_mac_join_end_data(struct mt6797_mac *m, const char *r)
{ (void)m; (void)r; ended = true; }
#include "native-step.inc"
u64 ktime_get_ns(void) { return clock_ns; }
void usleep_range(unsigned long a, unsigned long b) { (void)a; (void)b; assert(false); }
int mt6797_test_read(void *a, unsigned int *v) { (void)a; (void)v; assert(false); return -EIO; }
int mt6797_test_write(unsigned int value, void *address)
{
	assert(calls < TX_CALLS && address == mapping + (calls ? 0x1000 : 0));
	if (calls) for (unsigned int i = 0; i < 4; i++) emitted[(calls-1)*4+i] = value >> (8*i);
	calls++; if (calls == expire_at) clock_ns += 100 * NSEC_PER_MSEC;
	return calls == fail_at ? -EIO : 0;
}
static void exercise(bool enable, u64 remaining, unsigned int fault, unsigned int expiry)
{
	struct mt6797_init_transaction trans = {.phase = MT6797_INIT_IDLE};
	u8 history[32] = {0};
	struct mt6797_hif h = {.transaction=&trans, .firmware_ready=true, .capability_complete=true, .base=mapping};
	struct mt6797_mac m = {.hif=&h, .sequence=19, .native_diag_state=enable?MT6797_ND_IDLE:MT6797_ND_ACTIVE,
		.join_data_phase=enable, .join_key_pairwise=1, .join_key_group=1, .native_diag_engaged=!enable};
	int error = fault ? -EIO : expiry || !remaining ? -ETIMEDOUT : 0;
	clock_ns=1000000000ULL; m.join_deadline=clock_ns+remaining; m.join_data_deadline=m.join_deadline;
	calls=0; fail_at=fault; expire_at=expiry; ended=false; memset(emitted,0,sizeof(emitted));
	mutex_init(&h.mutex); h.io=(struct mt6797_hif_pio_io){.context=&h,.write=mt6797_hif_write,.read=mt6797_hif_read};
	assert(!mt6797_normal_admit(&h.normal,4,4,history)); h.normal.phase=MT6797_NORMAL_NVRAM_SUBMITTED;
	mt6797_native_diag_step(&m);
	assert(m.sequence==20 && m.first_error==error && m.closing==(error!=0));
	assert(m.join_page_debt==(error?0U:1U) && m.join_credit_pending==(error==0));
	assert(m.native_diag_engaged==(!enable || !error));
	assert(m.native_diag_state==(error?MT6797_ND_CLOSED:(enable?MT6797_ND_ENABLE_PENDING:MT6797_ND_DISABLE_PENDING)));
	assert(h.deadline_ns==1000000000ULL+(remaining<100*NSEC_PER_MSEC?remaining:100*NSEC_PER_MSEC));
	assert(h.normal.tc4_free==3 && !h.mutex.held && history[2]==8);
	assert(calls==(!remaining?0:fault?fault:expiry?expiry:TX_CALLS));
	if (error) {
		assert(h.normal.phase==MT6797_NORMAL_FAILED && trans.phase!=MT6797_INIT_IDLE);
		unsigned int before=calls;
#ifdef CONFIG_MT6797_CCMP_MASK_CONTROL
		assert(mt6797_hif_diag_mask(&h,20,false,clock_ns+NSEC_PER_MSEC)==-EIO);
#else
		assert(mt6797_hif_native_monitor(&h,20,false,40,clock_ns+NSEC_PER_MSEC)==-EIO);
#endif
		assert(calls==before && !(history[2]&16));
	} else {
		assert(h.normal.phase==MT6797_NORMAL_NVRAM_SUBMITTED && trans.phase==MT6797_INIT_IDLE);
#ifdef CONFIG_MT6797_CCMP_MASK_CONTROL
		const u8 expected[16]={16,0,0,0x80,0xc0,0xa0,1,19,0x68,0,0x0c,0x80,enable?7:0,0,0,0};
		assert(!memcmp(emitted,expected,sizeof(expected)));
#else
		assert(emitted[0]==24 && emitted[4]==0xfc && emitted[7]==19 && emitted[8]==enable && emitted[10]==40);
#endif
	}
}
int main(void)
{
	for (unsigned int enable=0;enable<2;enable++) {
		exercise(enable,11*1000*NSEC_PER_MSEC,0,0);
		exercise(enable,10*NSEC_PER_MSEC,0,0);
		for (unsigned int i=1;i<=TX_CALLS;i++) { exercise(enable,11*1000*NSEC_PER_MSEC,i,0); exercise(enable,11*1000*NSEC_PER_MSEC,0,i); }
	}
	exercise(false,0,0,0);
	puts("actual HIF/MAC control, boundaries, poison/no-second-I/O PASS"); return 0;
}
