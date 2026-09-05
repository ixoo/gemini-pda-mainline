/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include "hif_config_phase.h"

struct fake {
	unsigned int calls, fail, rx, status, sequence;
};
static int write_io(void *p, unsigned int offset, unsigned int value)
{
	struct fake *f=p;
	static const unsigned int tx[]={0x90006814,0x80000014,0x1300a001,
		0x10203040,0x16d0,0x8000000d};
	assert(f->calls<7);
	assert(offset==(f->calls==0 || f->calls==6 ? 0U : 0x1000U));
	assert(value==(f->calls<6 ? tx[f->calls] : 0x1000a020U));
	return ++f->calls==f->fail ? -EIO : 0;
}
static int read_io(void *p, unsigned int offset, unsigned int *word)
{
	struct fake *f=p;
	assert(offset==0x1000 && f->calls>=7 && f->rx<8);
	/* Uninterpreted diagnostics and extra-read tail intentionally nonzero. */
	*word=f->rx==0 ? 0xe000001c : f->rx==1 ? (f->sequence<<8)|1 :
		f->rx==2 ? 0xffffff00U|f->status : 0xa5a5a5a5;
	f->rx++;
	return ++f->calls==f->fail ? -EIO : 0;
}
int main(void)
{
	const unsigned char command[]={20,0,0,0x80,1,0xa0,0,19,0x40,0x30,0x20,0x10,
		0xd0,0x16,0,0,0x0d,0,0,0x80};
	struct fake f={.sequence=19};
	struct mt6797_hif_pio_io io={&f,write_io,read_io};
	struct mt6797_init_transaction t={.free_pages=104};
	unsigned int status,i;
	assert(!mt6797_config_send(&t,&io,command,20,19));
	assert(f.calls==6 && t.phase==MT6797_INIT_REPLY && t.free_pages==103);
	assert(mt6797_config_receive(&t,&io,0,&status)==-EAGAIN && f.calls==6);
	assert(!mt6797_config_receive(&t,&io,28,&status));
	assert(f.calls==15 && f.rx==8 && t.phase==MT6797_INIT_IDLE && status==0);
	assert(t.free_pages==103);
	assert(mt6797_config_receive(&t,&io,28,&status)<0 && f.calls==15);
	/* Every individual setup/data error terminates without another access. */
	for(i=1;i<=15;i++) {
		f=(struct fake){.sequence=19,.fail=i};
		t=(struct mt6797_init_transaction){.free_pages=104};
		if(i<=6) assert(mt6797_config_send(&t,&io,command,20,19)<0);
		else {
			assert(!mt6797_config_send(&t,&io,command,20,19));
			assert(mt6797_config_receive(&t,&io,28,&status)<0);
		}
		assert(f.calls==i && t.phase==MT6797_INIT_POISONED && t.free_pages==103);
	}
	for(i=0;i<4;i++) {
		f=(struct fake){.sequence=i==0 ? 20 : 19,.status=i==1 ? 7 : 0};
		t=(struct mt6797_init_transaction){.free_pages=104};
		assert(!mt6797_config_send(&t,&io,command,20,19));
		if(i==3) {
			assert(mt6797_init_abort(&t)<0); /* external deadline/owner failure */
			assert(mt6797_config_receive(&t,&io,28,&status)<0 && f.calls==6);
		} else assert(mt6797_config_receive(&t,&io,i==2 ? 29 : 28,&status)<0);
		assert(t.phase==MT6797_INIT_POISONED && t.free_pages==103);
		if(i==2) assert(f.calls==6);
	}
	f=(struct fake){.sequence=19}; t=(struct mt6797_init_transaction){.free_pages=104};
	assert(mt6797_config_send(&t,&io,command,19,19)<0 && !f.calls && t.free_pages==104);
	assert(mt6797_config_send(&t,&io,command,20,20)<0 && !f.calls);
	t.free_pages=0;
	assert(mt6797_config_send(&t,&io,command,20,19)==-ENOSPC && !f.calls);
	puts("config_phase_exact_pio_ack_flow_all_access_failures=pass");
	return 0;
}
