/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "hif_ordinary_section.h"
struct fake { unsigned int calls, fail; };
static int write_io(void *p,unsigned int offset,unsigned int value)
{
	struct fake *f=p;
	unsigned int n=f->calls, expected, expected_offset=0x1000;
	static const unsigned int config[]={0x90006814,0x80000014,0x1300a001,
		0x10203040,0x801,0x8000000d};
	if(n<6) { expected=config[n]; if(!n) expected_offset=0; }
	else if(n==6) {expected=0x1000a020;expected_offset=0;}
	else if(n==15) {expected=0x98006805;expected_offset=0;}
	else if(n==16) expected=0xc0000808;
	else if(n==17) expected=0xa000;
	else if(n<530) expected=0x5a5a5a5a;
	else if(n<656) expected=0;
	else if(n==656) {expected=0x9000680c;expected_offset=0;}
	else if(n==657) expected=0xc0000009;
	else if(n==658) expected=0xa000;
	else {assert(n==659);expected=0x5a;}
	assert(offset==expected_offset && value==expected);
	return ++f->calls==f->fail ? -EIO : 0;
}
static int read_io(void *p,unsigned int offset,unsigned int *word)
{
	struct fake *f=p;
	assert(offset==0x1000 && f->calls>=7 && f->calls<15);
	*word=f->calls==7 ? 0xe000001c : f->calls==8 ? 0x1301 : 0;
	return ++f->calls==f->fail ? -EIO : 0;
}
int main(void)
{
	unsigned char config[]={20,0,0,0x80,1,0xa0,0,19,0x40,0x30,0x20,0x10,
		1,8,0,0,0x0d,0,0,0x80};
	unsigned char data[2049], scratch[2560];
	unsigned int fail,status;
	struct fake f;
	struct mt6797_hif_pio_io io={&f,write_io,read_io};
	struct mt6797_init_transaction t;
	struct mt6797_ordinary_section s;
	int e;
	memset(data,0x5a,sizeof(data));
	for(fail=0;fail<=660;fail++) {
		f=(struct fake){.fail=fail};
		t=(struct mt6797_init_transaction){.free_pages=104,.start_free_pages=104};
		s=(struct mt6797_ordinary_section){0};
		e=mt6797_section_begin(&s,&t,&io,MT6797_SECTION_ORDINARY,config,20,19,data,sizeof(data));
		if(!e) e=mt6797_section_ack(&s,&io,28,&status);
		if(!e) e=mt6797_section_next(&s,&io,scratch,sizeof(scratch));
		if(!e) e=mt6797_section_next(&s,&io,scratch,sizeof(scratch));
		assert(t.free_pages==103 && t.start_free_pages==104);
		if(!fail) {
			assert(!e && f.calls==660 && s.submitted==2049 && s.phase==MT6797_SECTION_SUBMITTED);
			assert(mt6797_section_next(&s,&io,scratch,sizeof(scratch))<0 && f.calls==660);
		} else {
			assert(e && f.calls==fail && s.phase==MT6797_SECTION_FAILED && t.phase==MT6797_INIT_POISONED);
		}
	}
	f=(struct fake){0};t=(struct mt6797_init_transaction){.free_pages=104};
	s=(struct mt6797_ordinary_section){0};
	assert(mt6797_section_begin(&s,&t,&io,MT6797_SECTION_EMI,config,20,19,data,sizeof(data))<0 && !f.calls);
	assert(mt6797_section_begin(&s,&t,&io,MT6797_SECTION_ORDINARY,config,20,19,data,2048)<0 && !f.calls);
	assert(!mt6797_section_begin(&s,&t,&io,MT6797_SECTION_ORDINARY,config,20,19,data,2049));
	assert(mt6797_section_next(&s,&io,scratch,sizeof(scratch))<0 && f.calls==6);
	f=(struct fake){0};t=(struct mt6797_init_transaction){.free_pages=104};s=(struct mt6797_ordinary_section){0};
	assert(!mt6797_section_begin(&s,&t,&io,MT6797_SECTION_ORDINARY,config,20,19,data,2049));
	assert(!mt6797_section_ack(&s,&io,28,&status));
	assert(mt6797_section_next(&s,&io,scratch,2056)<0 && f.calls==15);
	/* START cannot interleave with an unfinished ordinary payload. */
	f=(struct fake){0};t=(struct mt6797_init_transaction){.free_pages=104,.start_free_pages=104};
	s=(struct mt6797_ordinary_section){0};
	assert(!mt6797_section_begin(&s,&t,&io,MT6797_SECTION_ORDINARY,config,20,19,data,2049));
	assert(!mt6797_section_ack(&s,&io,28,&status));
	{
		unsigned char start[]={16,0,0,0x80,2,0xa0,0,20,0,0,0,0,0,0,0,0};
		assert(mt6797_start_begin(&t,start,16,20)<0 && t.start_free_pages==104);
		assert(mt6797_section_next(&s,&io,scratch,sizeof(scratch))<0 && f.calls==15);
	}
	puts("ordinary_section_two_chunk_flow_660_failure_points_credit_isolation=pass");
	return 0;
}
