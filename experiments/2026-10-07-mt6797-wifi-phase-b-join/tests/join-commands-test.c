/* SPDX-License-Identifier: GPL-2.0-only */
#include <stdbool.h>
#include <stddef.h>
#include <assert.h>
#include <string.h>
#include "join-commands.h"
int main(void)
{
 unsigned char ap[6]={2,0,0,0,0,1}, p[124], before[124], ch[16], rm[4];
 assert(mt6797_join_station_payload(ap,1,0,0x3fc0,0x540,p));
 assert(p[0]==1 && p[1]==0x41 && !memcmp(p+2,ap,6));
 assert(p[13]==8 && p[20]==1 && !p[51] && p[54]==1 && !p[55]);
 assert(p[68]==3 && p[74]==0x4b && p[76]==1 && p[77]==1);
 for(unsigned i=78;i<124;i++) assert(!p[i]);
 assert(mt6797_join_station_payload(ap,3,2007,0x3fc0,0x540,p));
 assert(p[8]==0xd7 && p[9]==7 && p[20]==3 && p[51]==1);
 memcpy(before,p,124);
 assert(!mt6797_join_station_payload(ap,3,0,0x3fc0,0x540,p));
 assert(!mt6797_join_station_payload(ap,3,2008,0x3fc0,0x540,p));
 assert(!mt6797_join_station_payload(ap,1,1,0x3fc0,0x540,p));
 assert(!mt6797_join_station_payload(ap,2,0,0x3fc0,0x540,p));
 assert(!mt6797_join_station_payload(ap,1,0,0x3fc1,0x540,p));
 assert(!mt6797_join_station_payload(ap,1,0,0x40,0x540,p));
 ap[0]=3; assert(!mt6797_join_station_payload(ap,1,0,0x3fc0,0x540,p));
 assert(!memcmp(before,p,124));
 assert(mt6797_join_channel_payload(7,40,10000,false,ch));
 assert(!ch[0] && ch[1]==7 && !ch[2] && ch[3]==40 && ch[5]==2);
 assert(ch[12]==0x10 && ch[13]==0x27 && !ch[14] && !ch[15]);
 assert(!mt6797_join_channel_payload(7,36,10000,false,ch));
 assert(!mt6797_join_channel_payload(7,40,0,false,ch));
 assert(!mt6797_join_channel_payload(0,40,10000,false,ch));
 assert(mt6797_join_channel_payload(7,0,0,true,ch));
 assert(ch[1]==7 && ch[2]==1);
 for(unsigned i=3;i<16;i++) assert(!ch[i]);
 assert(mt6797_join_remove_station(rm));
 assert(!rm[0] && rm[1]==1 && !rm[2] && !rm[3]);
 return 0;
}
