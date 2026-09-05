/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include "hif_init_transaction.h"

int main(void)
{
	unsigned char start[16]={16,0,0,0x80,2,0xa0,0,19};
	unsigned char config[20]={20,0,0,0x80,1,0xa0,0,18,0,0,0,0,1,0,0,0,0,0,0,0x80};
	unsigned char reply[28]={28,0,0,0xe0,1,18};
	struct mt6797_init_transaction t={.free_pages=104,.start_free_pages=104};
	unsigned int status, i;
	/* CONFIG then START uses independent pools and shared sequence history. */
	assert(!mt6797_init_begin(&t,config,20,18));
	assert(!mt6797_init_submitted(&t,0));
	assert(!mt6797_init_accept_reply(&t,reply,28,&status));
	assert(!mt6797_start_begin(&t,start,16,19));
	assert(t.phase==MT6797_START_DISPATCH && t.free_pages==103 && t.start_free_pages==103);
	assert(!mt6797_start_submitted(&t,0) && t.phase==MT6797_START_READY);
	assert(mt6797_start_observe_ready(&t,0xffdfffffU)==-EAGAIN);
	assert(t.phase==MT6797_START_READY);
	assert(!mt6797_start_observe_ready(&t,0x200000));
	assert(t.phase==MT6797_INIT_IDLE && t.free_pages==103 && t.start_free_pages==103);
	assert(mt6797_start_begin(&t,start,16,19)<0 && t.phase==MT6797_INIT_POISONED);
	for (i=0;i<6;i++) {
		t=(struct mt6797_init_transaction){.free_pages=104,.start_free_pages=104};
		assert(!mt6797_start_begin(&t,start,16,19));
		if (i==0) assert(mt6797_start_submitted(&t,-EIO)<0);
		if (i==1) assert(mt6797_start_observe_ready(&t,0x200000)<0);
		if (i>=2) {
			assert(!mt6797_start_submitted(&t,0));
			if (i==2) assert(mt6797_init_accept_reply(&t,reply,28,&status)<0);
			if (i==3) assert(mt6797_start_submitted(&t,0)<0);
			if (i==4) assert(mt6797_init_abort(&t)<0); /* timeout */
			if (i==5) assert(mt6797_init_abort(&t)<0); /* owner/read failure */
		}
		assert(t.phase==MT6797_INIT_POISONED && t.free_pages==104 && t.start_free_pages==103);
		assert(mt6797_start_observe_ready(&t,0x200000)<0);
	}
	/* Invalid commands do not consume credits; sequence cannot be reused by CONFIG. */
	t=(struct mt6797_init_transaction){.free_pages=104,.start_free_pages=104};
	start[8]=2;
	assert(mt6797_start_begin(&t,start,16,19)==-EPROTO && t.free_pages==104);
	start[8]=0;
	assert(!mt6797_start_begin(&t,start,16,19));
	assert(!mt6797_start_submitted(&t,0));
	assert(!mt6797_start_observe_ready(&t,0x200000));
	config[7]=19;
	assert(mt6797_init_begin(&t,config,20,19)<0 && t.phase==MT6797_INIT_POISONED);
	t=(struct mt6797_init_transaction){0};
	assert(mt6797_start_begin(&t,start,16,19)==-ENOSPC && t.phase==MT6797_INIT_IDLE);
	t=(struct mt6797_init_transaction){.free_pages=105,.start_free_pages=105};
	assert(mt6797_start_begin(&t,start,16,19)<0 && t.phase==MT6797_INIT_POISONED);
	assert(mt6797_start_begin(NULL,start,16,19)==-EINVAL);
	/* Independent depletion: all CONFIG credits consumed leaves START intact. */
	t=(struct mt6797_init_transaction){.free_pages=104,.start_free_pages=104};
	for(i=0;i<104;i++) {
		config[7]=(unsigned char)i; reply[5]=(unsigned char)i;
		assert(!mt6797_init_begin(&t,config,20,i));
		assert(!mt6797_init_submitted(&t,0));
		assert(!mt6797_init_accept_reply(&t,reply,28,&status));
	}
	assert(!t.free_pages && t.start_free_pages==104);
	config[7]=104;
	assert(mt6797_init_begin(&t,config,20,104)==-ENOSPC);
	for(i=104;i<208;i++) {
		start[7]=(unsigned char)i;
		assert(!mt6797_start_begin(&t,start,16,i));
		assert(!mt6797_start_submitted(&t,0));
		assert(!mt6797_start_observe_ready(&t,0x200000));
	}
	assert(!t.free_pages && !t.start_free_pages);
	start[7]=208;
	assert(mt6797_start_begin(&t,start,16,208)==-ENOSPC);
	/* Exhausted START must not block or debit an available CONFIG pool. */
	t=(struct mt6797_init_transaction){.free_pages=104};
	assert(mt6797_start_begin(&t,start,16,208)==-ENOSPC && t.free_pages==104);
	config[7]=209;
	assert(!mt6797_init_begin(&t,config,20,209) && t.free_pages==103 && !t.start_free_pages);
	/* Independent source oracle: CONFIG spends TC4 only, then the same
	 * sequence must be refused by START despite its untouched TC0 balance.
	 */
	t=(struct mt6797_init_transaction){.free_pages=104,.start_free_pages=104};
	config[7]=23; reply[5]=23; start[7]=23;
	assert(!mt6797_init_begin(&t,config,20,23));
	assert(t.free_pages==103 && t.start_free_pages==104);
	assert(!mt6797_init_submitted(&t,0));
	assert(!mt6797_init_accept_reply(&t,reply,28,&status));
	assert(mt6797_start_begin(&t,start,16,23)<0);
	assert(t.phase==MT6797_INIT_POISONED);
	assert(t.free_pages==103 && t.start_free_pages==104);
	puts("config_tc4_start_tc0_independent_pool_exhaustion=pass");
	puts("start_submission_readiness_timeout_sequence_no_ack_no_refund=pass");
	return 0;
}
