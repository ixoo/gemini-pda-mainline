/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdbool.h>
#include <stddef.h>
#include <errno.h>
#include <assert.h>
#include <string.h>
#include "join-submit.h"
static void ready(struct mt6797_normal_transaction *t, unsigned char *history, unsigned pages)
{
 *t=(struct mt6797_normal_transaction){0};
 assert(!mt6797_normal_admit(t,pages,pages,history));
 t->phase=MT6797_NORMAL_NVRAM_SUBMITTED;
}
int main(void)
{
 struct mt6797_normal_transaction t={0}; struct mt6797_hif_command command;
 unsigned char history[32]={0}, out[256], before[256], frame[101]={0xb0};
 ready(&t,history,4); memset(out,0xa5,sizeof(out));
 assert(!mt6797_join_prepare_management(&t,frame,101,1,7,500,3,out,sizeof(out),&command));
 assert(t.tc4_free==2 && t.phase==MT6797_NORMAL_CONFIG_TX);
 assert(out[0]==129 && out[28]==0xb0 && !memcmp(out+28,frame,101));
 for(unsigned i=129;i<command.transfer_bytes;i++) assert(!out[i]);
 for(unsigned i=0;i<32;i++) assert(!history[i]);
 assert(!mt6797_normal_submitted(&t,0));
 assert(t.tc4_free==2 && t.phase==MT6797_NORMAL_NVRAM_SUBMITTED);
 memcpy(before,out,sizeof(out));
 assert(mt6797_join_prepare_management(&t,frame,101,1,8,500,3,out,sizeof(out),&command)==-EBUSY);
 assert(!memcmp(out,before,sizeof(out)) && t.tc4_free==2);
 /* Credit reconciliation is separate from successful PIO/TXdone. */
 struct mt6797_normal_release release;
 unsigned int words[8]={0}; words[7]=(2U<<16)|2U;
 assert(!mt6797_normal_reconcile(&t,words,&release));
 assert(t.tc4_free==4);
 assert(!mt6797_join_prepare_management(&t,frame,101,1,8,500,3,out,sizeof(out),&command));
 assert(mt6797_normal_submitted(&t,-EIO)<0 && t.phase==MT6797_NORMAL_FAILED && t.tc4_free==2);
 ready(&t,history,1); memcpy(before,out,sizeof(out));
 assert(mt6797_join_prepare_management(&t,frame,101,1,9,500,3,out,sizeof(out),&command)==-ENOSPC);
 assert(t.tc4_free==1 && !memcmp(out,before,sizeof(out)));
 ready(&t,history,4);
 assert(mt6797_join_prepare_management(&t,frame,101,1,9,500,3,out,128,&command)<0);
 assert(t.tc4_free==4 && !memcmp(out,before,sizeof(out)));
 frame[0]=8;
 assert(mt6797_join_prepare_management(&t,frame,101,1,9,500,3,out,sizeof(out),&command)==-EINVAL);
 assert(t.tc4_free==4 && !memcmp(out,before,sizeof(out)));
 return 0;
}
