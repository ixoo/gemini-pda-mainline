/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "hif_init_transaction.h"

/* Narrow exports for the independent Python differential fixture. */
int check_result(const unsigned char *p, size_t n, unsigned int seq)
{
	unsigned int status;
	int e = mt6797_init_validate_result(p, n, seq, &status);
	return e == 0 ? 0 : e == -EIO ? 1 : 2;
}
int check_config(const unsigned char *p, size_t n, unsigned int seq)
{
	return mt6797_init_validate_config(p, n, seq) ? 2 : 0;
}

int main(void)
{
	unsigned char command[20] = {20,0,0,0x80,1,0xa0,0,19,0x40,0x30,0x20,0x10,
		0xd0,0x16,0,0,0x0d,0,0,0x80};
	unsigned char reply[32] = {28,0,0,0xe0,1,19};
	struct mt6797_init_transaction t = {.free_pages = 104};
	struct mt6797_hif_command span;
	unsigned int status, i;
	assert(!mt6797_init_begin(&t, command, 20, 19));
	assert(t.phase == MT6797_INIT_DISPATCH && t.free_pages == 103);
	assert(!mt6797_init_submitted(&t, 0) && t.phase == MT6797_INIT_REPLY);
	assert(mt6797_init_prepare_reply(&t, 0, 32, &span) == -EAGAIN);
	assert(!span.word && t.phase == MT6797_INIT_REPLY);
	assert(!mt6797_init_prepare_reply(&t, 28, 32, &span));
	assert(span.transfer_bytes == 32 && span.word == 0x1000a020);
	assert(!mt6797_init_accept_reply(&t, reply, 28, &status));
	assert(t.phase == MT6797_INIT_IDLE && t.free_pages == 103 && status == 0);
	assert(mt6797_init_begin(&t, command, 20, 19) < 0 && t.phase == MT6797_INIT_POISONED);
	assert(t.free_pages == 103);
	/* Each bad reply poisons a newly admitted pending transaction. */
	for (i = 0; i < 5; i++) {
		t = (struct mt6797_init_transaction){.free_pages=104}; reply[5]=19; reply[8]=0;
		assert(!mt6797_init_begin(&t, command, 20, 19));
		assert(!mt6797_init_submitted(&t, 0));
		if (i == 0) reply[5] = 20;
		if (i == 1) reply[8] = 255;
		assert(mt6797_init_accept_reply(&t, i == 2 ? NULL : reply,
			i == 3 ? 27 : i == 4 ? 32 : 28, &status) < 0);
		assert(t.phase == MT6797_INIT_POISONED && t.free_pages == 103);
		assert(mt6797_init_submitted(&t, 0) < 0);
	}
	reply[5]=19; reply[8]=0;
	for (i = 0; i < 5; i++) {
		t = (struct mt6797_init_transaction){.free_pages=104};
		assert(!mt6797_init_begin(&t, command, 20, 19));
		if (i == 0) assert(mt6797_init_submitted(&t, -EIO) < 0);
		if (i == 1) assert(mt6797_init_accept_reply(&t, reply, 28, &status) < 0);
		if (i == 2) assert(mt6797_init_abort(&t) < 0); /* deadline/ownership loss */
		if (i >= 3) {
			assert(!mt6797_init_submitted(&t, 0));
			if (i == 3) assert(mt6797_init_prepare_reply(&t, 29, 32, &span) < 0);
			else assert(mt6797_init_prepare_reply(&t, 28, 31, &span) < 0);
		}
		assert(t.phase == MT6797_INIT_POISONED && t.free_pages == 103);
	}
	t = (struct mt6797_init_transaction){.free_pages=104};
	for (i = 0; i < 104; i++) {
		command[7]=(unsigned char)i; reply[5]=(unsigned char)i;
		assert(!mt6797_init_begin(&t,command,20,i));
		assert(!mt6797_init_submitted(&t,0));
		assert(!mt6797_init_accept_reply(&t,reply,28,&status));
	}
	command[7]=104;
	assert(mt6797_init_begin(&t,command,20,104)==-ENOSPC && !t.free_pages);
	t = (struct mt6797_init_transaction){.free_pages=105};
	assert(mt6797_init_begin(&t,command,20,104)<0 && t.phase==MT6797_INIT_POISONED);
	assert(mt6797_init_validate_result(reply,28,256,&status)==-EINVAL);
	assert(mt6797_init_validate_result(reply,28,103,NULL)==-EINVAL);
	assert(mt6797_init_begin(NULL,command,20,104)==-EINVAL);
	puts("config_transaction_submission_reply_poison_no_refund=pass");
	return 0;
}
