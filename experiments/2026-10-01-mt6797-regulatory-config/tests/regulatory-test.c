/* SPDX-License-Identifier: GPL-2.0-only */
#include <assert.h>
#include <stdio.h>
#include "regulatory-encode.h"
#include "normal_command.h"
static void encode(void)
{
 struct mt6797_channel_limit c[13] = {0};
 struct mt6797_regulatory_payloads p;
 unsigned int i;
 for (i=0;i<13;i++) c[i]=(struct mt6797_channel_limit){true,i>=11,20};
 assert(!mt6797_regulatory_encode(c,"00",&p));
 assert(p.domain[0]=='0' && p.domain[1]=='0');
 assert(p.domain[7]==1 && p.domain[8]==13);
 assert(p.passive[7]==12 && p.passive[8]==2 && p.passive[2]==1);
 assert(p.domain[52]==1 && p.domain[53]==1 && p.power[8]==1);
 for(i=0;i<13;i++) assert(p.power[12+i]==40);
 for(i=25;i<30;i++) assert(p.power[i]==0xc0);
 c[3].enabled=false; c[7].max_power_dbm=-1;
 assert(!mt6797_regulatory_encode(c,"US",&p));
 assert(p.domain[0]=='S' && p.domain[1]=='U');
 assert(p.domain[7]==1 && p.domain[8]==3 && p.domain[15]==5 && p.domain[16]==9);
 assert(p.power[15]==0xc0 && p.power[19]==254);
 c[7].max_power_dbm=32;
 assert(mt6797_regulatory_encode(c,"US",&p)==-ERANGE);
 for(i=0;i<sizeof(p);i++) assert(!((unsigned char *)&p)[i]);
 for(i=0;i<13;i++) c[i]=(struct mt6797_channel_limit){i%2==0,false,20};
 assert(mt6797_regulatory_encode(c,"00",&p)==-E2BIG);
 for(i=0;i<sizeof(p);i++) assert(!((unsigned char *)&p)[i]);
 assert(mt6797_regulatory_encode(c,"ZZ",NULL)==-EINVAL);
 assert(mt6797_regulatory_encode(c,"us",&p)==-EINVAL);
 memset(c,0,sizeof(c));
 assert(!mt6797_regulatory_encode(c,"00",&p));
 for(i=4;i<52;i++) assert(!p.domain[i] && !p.passive[i]);
}
static void transaction(void)
{
 struct mt6797_normal_transaction t={0};
 struct mt6797_hif_command cmd;
 unsigned char history[32]={0x1e}, payload[512]={0},frame[1024];
 assert(!mt6797_normal_admit(&t,26,25,history));
 t.phase=MT6797_NORMAL_CAP_RECEIVED;
 assert(!mt6797_normal_prepare_config(&t,MT6797_NORMAL_NVRAM_SETTINGS,5,payload,512,frame,sizeof(frame),&cmd));
 assert(t.phase==MT6797_NORMAL_NVRAM_TX && t.tc4_free==20);
 assert(!mt6797_normal_submitted(&t,0));
 assert(t.phase==MT6797_NORMAL_NVRAM_SUBMITTED);
 assert(!mt6797_normal_prepare_config(&t,MT6797_NORMAL_DOMAIN,6,payload,56,frame,sizeof(frame),&cmd));
 assert(t.tc4_free==19);
 assert(!mt6797_normal_submitted(&t,0));
 assert(t.phase==MT6797_NORMAL_NVRAM_SUBMITTED);
 assert(mt6797_normal_prepare_config(&t,MT6797_NORMAL_TX_CTRL,7,payload,31,frame,sizeof(frame),&cmd)==-EINVAL);
 assert(t.phase==MT6797_NORMAL_NVRAM_SUBMITTED && t.tc4_free==19);
 assert(!mt6797_normal_prepare_config(&t,MT6797_NORMAL_TX_CTRL,7,payload,32,frame,sizeof(frame),&cmd));
 assert(t.tc4_free==18 && frame[4]==0x38 && frame[6]==1 && frame[7]==7);
 assert(mt6797_normal_submitted(&t,-EIO)==-EIO);
 assert(t.phase==MT6797_NORMAL_FAILED && t.tc4_free==18 && history[0]==0xfe);
 assert(mt6797_normal_prepare_config(&t,MT6797_NORMAL_DOMAIN,8,payload,56,frame,sizeof(frame),&cmd)==-EIO);
 t=(struct mt6797_normal_transaction){0}; memset(history,0,sizeof(history));
 assert(!mt6797_normal_admit(&t,26,25,history)); t.phase=MT6797_NORMAL_NVRAM_SUBMITTED;
 assert(mt6797_normal_prepare_config(&t,MT6797_NORMAL_NVRAM_SETTINGS,5,payload,512,frame,sizeof(frame),&cmd)==-EIO);
 assert(t.phase==MT6797_NORMAL_FAILED && t.tc4_free==25 && !history[0]);
}
int main(void){encode();transaction();puts("regulatory encoder and retained transaction: pass");return 0;}
